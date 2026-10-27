"""Administrator-only integration readiness. Counts only; no evidence text or paid calls."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session
from .db import get_db
from .auth import current_user
from .models import User
from .access import profile, has

router=APIRouter(prefix="/api/integration",tags=["integration"])

def require_admin(db,user):
    grant=profile(db,user)
    if grant.get("role")!="National Administrator" or grant.get("geographic_scope")!="Nationwide" or not has(grant,"administration"):
        raise HTTPException(status_code=403,detail="National administrator required")

METRICS={
 "social_posts": """SELECT COUNT(*) AS total,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(canonical_url),'') IS NULL) AS missing_url,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(platform),'') IS NULL) AS missing_platform,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(published_at),'') IS NULL) AS missing_publication,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(text_content),'') IS NULL) AS missing_content,
  COUNT(*) FILTER(WHERE COALESCE(NULLIF(TRIM(observed_handle),''),NULLIF(TRIM(author_name),'')) IS NULL) AS missing_account,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(provider_result_id),'') IS NULL) AS missing_provider_id
  FROM social_listening_results""",
 "promotion_lineage": """SELECT COUNT(*) AS linked,
  COUNT(*) FILTER(WHERE i.id IS NULL) AS broken_fk,
  COUNT(*) FILTER(WHERE i.id IS NOT NULL AND NULLIF(TRIM(i.source_id),'') IS NULL) AS eligible_backfill,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(i.source_id),'') IS NOT NULL AND i.source_id<>('social:'||CAST(s.id AS TEXT))) AS conflicts
  FROM social_listening_results s
  LEFT JOIN intelligence_items i ON i.id=s.promoted_intelligence_id
  WHERE s.promoted_intelligence_id IS NOT NULL""",
 "intelligence_provenance": """SELECT COUNT(*) AS total,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(source_url),'') IS NULL) AS missing_url,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(platform),'') IS NULL) AS missing_platform,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(original_content),'') IS NULL) AS missing_content,
  COUNT(*) FILTER(WHERE NULLIF(TRIM(source_id),'') IS NULL) AS missing_canonical_source_id
  FROM intelligence_items""",
 "candidates": """SELECT COUNT(*) AS total,
  COUNT(*) FILTER(WHERE status='Active') AS active
  FROM watchlist_items WHERE LOWER(type)='candidate'"""
}

@router.get("/readiness")
def readiness(user:User=Depends(current_user),db:Session=Depends(get_db)):
    require_admin(db,user)
    result={}
    for key,statement in METRICS.items():
        try:
            row=db.execute(text(statement)).mappings().one()
            result[key]={name:int(value or 0) for name,value in row.items()}
        except Exception:
            db.rollback()
            raise HTTPException(503,"Integration readiness query unavailable")
    # Untrusted source fields are never returned. The provider distribution
    # is a fixed aggregate over platform names with a strict result cap.
    platform_rows=db.execute(text("""SELECT platform,COUNT(*) AS total,
        COUNT(*) FILTER(WHERE NULLIF(TRIM(published_at),'') IS NULL) AS missing_publication,
        COUNT(*) FILTER(WHERE NULLIF(TRIM(provider_result_id),'') IS NULL) AS missing_provider_id,
        COUNT(*) FILTER(WHERE NULLIF(TRIM(text_content),'') IS NULL) AS missing_content
      FROM social_listening_results
      GROUP BY platform ORDER BY COUNT(*) DESC LIMIT 25""")).mappings().all()
    result["platform_quality"]=[{key:(int(value or 0) if key!="platform" else str(value or "Unknown")[:64])
                                for key,value in row.items()} for row in platform_rows]
    source=result["social_posts"]
    lineage=result["promotion_lineage"]
    result["release_gates"]={
      "social_source_provenance_complete":all(
        source[field]==0 for field in ("missing_url","missing_platform","missing_publication","missing_content","missing_account")
      ),
      "promoted_source_id_integrity":lineage["broken_fk"]==0 and lineage["eligible_backfill"]==0 and lineage["conflicts"]==0,
      "source_id_backfill_needed":lineage["eligible_backfill"]>0,
      "manual_validation_required":True,
      "external_pilot_status":"Requires separate Supabase audit"
    }
    result["canonical_contract"]="social:<row id> | radar:<pilot post id> | candidate:<registry id>"
    result["scope"]="Current app database only; Smart Radar pilot lives in separate Supabase project"
    result["external_pilot_verification"]="Not queried by this endpoint"
    result["paid_requests"]=0
    return result

class BackfillRequest(BaseModel):
    confirm: bool = False
    expected_missing: int = Field(default=0, ge=0, le=1000)

@router.get("/source-id-backfill/preview")
def preview_backfill(user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Read-only plan; never changes stored source evidence."""
    require_admin(db,user)
    from scripts.backfill_source_ids import run
    return run(db,apply=False)

@router.post("/source-id-backfill/apply")
def apply_backfill(body:BackfillRequest,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Apply explicitly confirmed and preflight-matched source-ID repair only."""
    require_admin(db,user)
    if not body.confirm:
        raise HTTPException(409,"Explicit confirmation required")
    from scripts.backfill_source_ids import run
    try:
        result=run(db,apply=True,expected_missing=body.expected_missing)
        return {**result,"mode":"already_complete" if result["updated"]==0 else "apply"}
    except RuntimeError as exc:
        db.rollback()
        raise HTTPException(409,str(exc)) from exc

@router.get("/provenance-review-queue")
def provenance_review_queue(limit:int=100,offset:int=0,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Bounded, administrator-only provenance review queue (metadata only)."""
    require_admin(db,user)
    if limit<1 or limit>200 or offset<0 or offset>100000:
        raise HTTPException(422,"Invalid review queue page")
    rows=db.execute(text("""
      SELECT id,platform,canonical_url,published_at,provider_result_id,
             text_content,observed_handle,author_name
      FROM social_listening_results
      WHERE NULLIF(TRIM(canonical_url),'') IS NULL
         OR NULLIF(TRIM(platform),'') IS NULL
         OR NULLIF(TRIM(published_at),'') IS NULL
         OR NULLIF(TRIM(text_content),'') IS NULL
         OR COALESCE(NULLIF(TRIM(observed_handle),''),NULLIF(TRIM(author_name),'')) IS NULL
         OR NULLIF(TRIM(provider_result_id),'') IS NULL
      ORDER BY id LIMIT :limit OFFSET :offset
    """),{"limit":limit,"offset":offset}).mappings().all()
    from .source_ids import canonical_source_id
    output=[]
    for row in rows:
        missing=[]
        for field,column in (("source_url","canonical_url"),("platform","platform"),
                             ("publication_time","published_at"),("content","text_content"),
                             ("provider_record_id","provider_result_id")):
            if not str(row[column] or "").strip(): missing.append(field)
        if not str(row["observed_handle"] or row["author_name"] or "").strip():
            missing.append("account")
        output.append({"source_id":canonical_source_id("social",row["id"]),
                       "platform":str(row["platform"] or "Unknown")[:64],
                       "missing_fields":missing,
                       "source_url_available":bool(str(row["canonical_url"] or "").strip())})
    return {"results":output,"limit":limit,"offset":offset,
            "has_more":len(rows)==limit,
            "policy":"Source content and original URLs are withheld; verify against original evidence before edits.",
            "paid_requests":0}
