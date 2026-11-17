"""One read-only aggregate for campaign assessment readiness.

Keep WATCHLIST_ACCOUNT links out of ordinary AI screening. An assessment row
labelled UNASSESSED is still pending; mere row existence is not completion.
Only execute after existing campaign authorization checks. No provider calls.
"""
from sqlalchemy import case, func, and_, or_
from .models import CampaignEvidence, EvidenceAssessment, AIAssessmentJob

def campaign_link_assessment_coverage(db,campaign_id):
    """Counts by source *link*, not post population, for one authorized campaign."""
    cid=int(campaign_id)
    latest_id=(db.query(EvidenceAssessment.id).filter(
        EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
        EvidenceAssessment.result_id==CampaignEvidence.result_id
    ).order_by(EvidenceAssessment.assessment_version.desc(),
               EvidenceAssessment.id.desc()).limit(1).correlate(CampaignEvidence).scalar_subquery())
    is_monitoring=CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'
    is_watchlist=CampaignEvidence.match_method=='WATCHLIST_ACCOUNT'
    latest_label=func.upper(func.coalesce(EvidenceAssessment.relevance_label,''))
    is_pending=or_(EvidenceAssessment.id.is_(None),latest_label.in_(['UNASSESSED','']))
    has_job=AIAssessmentJob.id.is_not(None)
    missing_job=AIAssessmentJob.id.is_(None)
    def amount(clause):
        return func.coalesce(func.sum(case((clause,1),else_=0)),0)
    result=(db.query(
       func.count(CampaignEvidence.id),
       amount(is_watchlist),
       amount(is_monitoring),
       amount(and_(is_monitoring,~is_pending)),
       amount(and_(is_monitoring,is_pending)),
       amount(and_(is_monitoring,is_pending,missing_job)),
       amount(and_(is_monitoring,is_pending,has_job)),
       amount(and_(is_monitoring,is_pending,AIAssessmentJob.state=='FAILED'))
    ).outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
      .outerjoin(AIAssessmentJob,and_(
          AIAssessmentJob.campaign_id==CampaignEvidence.campaign_id,
          AIAssessmentJob.result_id==CampaignEvidence.result_id))
      .filter(CampaignEvidence.campaign_id==cid).one())
    (all_links,watchlist,monitoring,completed,pending,without_job,
     with_job,failed)=map(int,result)
    return {
      'scope':'ONE_AUTHORIZED_CAMPAIGN_LINK_INVENTORY',
      'total_campaign_links':all_links,
      'watchlist_account_links_excluded_from_ai':watchlist,
      'monitoring_evidence_links':monitoring,
      'assessed_monitoring_links':completed,
      'pending_monitoring_links':pending,
      'pending_monitoring_without_job':without_job,
      'pending_monitoring_with_job':with_job,
      'pending_monitoring_failed_jobs':failed,
      'link_count_reconciled':all_links==watchlist+monitoring and monitoring==completed+pending and pending==without_job+with_job,
      'ready_for_no_cost_job_reconciliation':without_job>0,
      'next_action':(
         'Use campaignAssessmentJobReconcile only after review; job creation is no-cost but provider processing is separately budget gated.'
         if without_job else 'No unqueued assessment gap detected in this authorized campaign.'
      ),
      'watchlist_links_are_not_missing_assessments':True,
      'assessment_rows_labelled_unassessed_remain_pending':True,
      'source_text_or_ids_returned':False,
      'paid_provider_called':False,
      'database_writes':0,
    }
