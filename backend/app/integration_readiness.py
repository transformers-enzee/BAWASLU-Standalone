"""Administrator-only integration readiness. Counts only; no evidence text or paid calls."""
from fastapi import APIRouter, Depends, HTTPException
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
    result["canonical_contract"]="social:<row id> | radar:<pilot post id> | candidate:<registry id>"
    result["scope"]="Current app database only; Smart Radar pilot lives in separate Supabase project"
    result["external_pilot_verification"]="Not queried by this endpoint"
    result["paid_requests"]=0
    return result
