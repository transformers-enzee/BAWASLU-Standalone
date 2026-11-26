"""Optional, permission-scoped legacy view adapters for the governance ledger.

Never mutate raw source / AI assessment rows; no paid AI. Disabled unless an
administrator explicitly enables governance integration after database QA.
"""
import os
import json
from collections import defaultdict
from sqlalchemy import tuple_
from .models import GovernanceFieldCorrection, GovernanceInsight
from .governance_projection import effective_assessment
from .human_governance_gates import insight_publication_gate

def active():
    return os.getenv("BAWASLU_GOVERNANCE_INTEGRATION_ENABLED","").strip().lower() in {"1","true","yes"}

def inbox_governance_annotations(db,records):
    """Return review overlays keyed by (campaign,source), scoped to caller's visible page."""
    if not active() or not records:
        return {}
    pairs={(int(r["campaign_id"]),int(r["id"])) for r in records}
    if len(pairs)>300:
        raise ValueError("Governance annotations require a bounded Inbox page")
    rows=(db.query(GovernanceFieldCorrection).filter(
        tuple_(GovernanceFieldCorrection.campaign_id,GovernanceFieldCorrection.result_id).in_(pairs)
    ).order_by(GovernanceFieldCorrection.id.asc()).limit(5001).all())
    if len(rows)>5000:
        raise ValueError("Governance correction ledger exceeds safe page limit")
    grouped=defaultdict(list)
    for correction in rows:
        grouped[(correction.campaign_id,correction.result_id)].append(correction)
    return {key:effective_assessment(None,grouped.get(key,[]))
            for key in pairs if grouped.get(key)}

def approved_command_annotations(db,p,campaigns,limit=15):
    """Only independently approved, current-source insight summaries; not legacy alerts."""
    if not active() or not campaigns:
        return []
    from .governance_persistence import _snapshot,_approved_row_gate
    from .access import allowed
    authorized=[int(c.id) for c in campaigns if allowed(p,c)]
    if not authorized:return []
    rows=(db.query(GovernanceInsight).filter(
        GovernanceInsight.campaign_id.in_(authorized),
        GovernanceInsight.state=="approved"
    ).order_by(GovernanceInsight.id.desc()).limit(min(max(limit,1),30)*3).all())
    approved=[]
    for row in rows:
        try:
            ids=json.loads(row.evidence_ids_json)
            if not isinstance(ids,list) or not ids:
                continue
            current=_snapshot(db,p,row.campaign_id,ids)==row.source_digest
            decision=_approved_row_gate(row,ids,current)
            if not decision["publish_allowed"]:continue
            approved.append({
                "insight_id":str(row.id),"campaign_id":str(row.campaign_id),
                "title":row.title,"analysis_scope":row.analysis_scope,
                "claim_status":row.claim_status,"evidence_result_ids":[str(i) for i in ids],
                "review_state":"OFFICER_APPROVED","approver_id":str(row.approver_id),
                "read_only":True,"legal_violation_confirmed":False,
            })
            if len(approved)>=limit:break
        except (ValueError,TypeError):
            continue
        except Exception as error:
            # Invalid source or scope is not a publishable item. Other failures
            # must not silently become a default empty feed.
            from fastapi import HTTPException
            if isinstance(error,HTTPException) and error.status_code in (403,404,409,422):
                continue
            raise
    return approved
