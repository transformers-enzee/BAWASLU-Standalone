"""Permission-scoped resolution of BAWASLU canonical source references.

No provider calls, no implicit cross-database joins, no inferred identities.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from .db import get_db
from .models import User, SocialListeningResult, IntelligenceItem
from .auth import current_user
from .access import profile, has, allowed
from .source_ids import parse_canonical_source_id
from .socialcrawl import _result_in_scope

router=APIRouter(prefix="/api/source-lineage",tags=["source-lineage"])

@router.get("/saved-assessments/{reference:path}")
def resolve_saved_assessments(reference:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    """Shared Inbox/Watchlist/Smart Radar lookup for existing *social* source IDs.

    Radar pilot IDs are NOT assumed to refer to the same post.
    """
    p=profile(db,user)
    if not has(p,'view_intelligence'):
        raise HTTPException(403,'Intelligence access required')
    try:
        namespace,raw_id=parse_canonical_source_id(reference)
    except ValueError:
        raise HTTPException(422,'Invalid canonical source reference')
    if namespace!='social':
        raise HTTPException(409,'No verified mapping from Radar pilot IDs to Social Listening source IDs')
    post=db.get(SocialListeningResult,int(raw_id))
    if not post or not _result_in_scope(db,p,post):
        raise HTTPException(404,'Source unavailable')
    from .saved_assessment_views import saved_classifications_for_posts
    assessments=saved_classifications_for_posts(db,p,[post]).get(post.id,[])
    # This contract is shared by Inbox/Watchlist and any Smart Radar view
    # explicitly carrying a canonical social:* identifier. Pilot-only Radar IDs
    # must never be silently treated as Social Listening record IDs.
    return {'canonical_source_id':reference,'saved_assessments':assessments,
        'assessment_count':len(assessments),'shared_review_provenance':'SAVED_CAMPAIGN_ASSESSMENTS',
        'reusable_by':['Intelligence Inbox','Watchlist','Smart Radar canonical-social-source view'],
        'identity_scope':'SOCIAL_SOURCE_ONLY',
        'radar_pilot_identity_crosswalk_verified':False,
        'paid_provider_called':False}


@router.get("/{reference:path}")
def resolve_source(reference:str,user:User=Depends(current_user),db:Session=Depends(get_db)):
    p=profile(db,user)
    if not has(p,"view_intelligence"):
        raise HTTPException(403,"Intelligence access required")
    try:
        namespace,source_id=parse_canonical_source_id(reference)
    except ValueError:
        raise HTTPException(422,"Invalid canonical source reference")
    if namespace!="social":
        # Radar source evidence lives in a distinct Supabase pilot schema and
        # must be accessed using its existing scope-protected Smart Radar API.
        raise HTTPException(409,"Radar sources require Smart Radar's pilot evidence API")
    row=db.get(SocialListeningResult,int(source_id))
    if not row or not _result_in_scope(db,p,row):
        raise HTTPException(404,"Source unavailable")
    intel=None
    if row.promoted_intelligence_id is not None:
        candidate=db.get(IntelligenceItem,row.promoted_intelligence_id)
        if candidate and allowed(p,candidate) and candidate.source_id in ("",None,reference):
            intel={"id":str(candidate.id),"intelligence_code":candidate.intelligence_id}
    return {
        "canonical_source_id":reference,
        "provider_result_id":row.provider_result_id or None,
        "source_url":row.canonical_url or None,
        "platform":row.platform or None,
        "published_at":row.published_at or None,
        "collected_at":row.collected_at.isoformat() if row.collected_at else None,
        "has_original_content":bool((row.text_content or "").strip()),
        "observed_account":row.observed_handle or row.author_name or None,
        "review_state":row.review_state,
        "intelligence":intel,
        "publication_time_verified":bool((row.published_at or "").strip()),
        "source_evidence_verified":False,
    }
