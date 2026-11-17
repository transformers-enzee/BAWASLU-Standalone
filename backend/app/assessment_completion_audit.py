"""Read-only, authorization-scoped assessment job completion verification.

An AI usage row can belong to an older assessment version; manual review and
sentiment-only updates may append later versions. An absent usage-backed
classification is an audit discrepancy, not permission to retry provider calls.
"""
from sqlalchemy import and_, case, func, exists
from .models import AIAssessmentJob, EvidenceAssessment, AssessmentAIUsage, CampaignEvidence

_VALID_LABELS=('RELEVANT','IRRELEVANT','UNCERTAIN')

def campaign_completion_audit(db,campaign_id):
    cid=int(campaign_id)
    # Correlated per job, so each completed job contributes at most one count
    # irrespective of the number of assessment versions or usage rows.
    any_assessment=exists().where(and_(
        EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
        EvidenceAssessment.result_id==AIAssessmentJob.result_id))
    valid_assessment=exists().where(and_(
        EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
        EvidenceAssessment.result_id==AIAssessmentJob.result_id,
        func.upper(func.coalesce(EvidenceAssessment.relevance_label,'' )).in_(_VALID_LABELS)))
    usage_link=exists().where(and_(
        EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
        EvidenceAssessment.result_id==AIAssessmentJob.result_id,
        AssessmentAIUsage.assessment_id==EvidenceAssessment.id,
        AssessmentAIUsage.campaign_id==AIAssessmentJob.campaign_id))
    # A usage row only verifies completion when its own assessment has an
    # actual relevance label, rather than a sentiment-only UNASSESSED row.
    verified=exists().where(and_(
        EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
        EvidenceAssessment.result_id==AIAssessmentJob.result_id,
        func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).in_(_VALID_LABELS),
        AssessmentAIUsage.assessment_id==EvidenceAssessment.id,
        AssessmentAIUsage.campaign_id==AIAssessmentJob.campaign_id))
    def amount(clause):
        return func.coalesce(func.sum(case((clause,1),else_=0)),0)
    completed=AIAssessmentJob.state=='COMPLETED'
    # Existing queue uniqueness ensures one row per (campaign,result).
    counts=(db.query(
        func.count(AIAssessmentJob.id),
        amount(completed),
        amount(and_(completed,verified)),
        amount(and_(completed,~any_assessment)),
        amount(and_(completed,any_assessment,~valid_assessment)),
        amount(and_(completed,valid_assessment,~usage_link)),
        amount(and_(completed,usage_link,~verified)),
        amount(and_(completed,AIAssessmentJob.attempts==0)),
        amount(AIAssessmentJob.state=='PENDING'),
        amount(AIAssessmentJob.state=='PROCESSING'),
        amount(AIAssessmentJob.state=='FAILED'))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT').one())
    (jobs,complete,good,missing_assessment,invalid_label,missing_usage,
     usage_without_valid_label,zero_attempts,pending,processing,failed)=map(int,counts)
    discrepancies=complete-good
    return {
        'scope':'AUTHORIZED_CAMPAIGN_ORDINARY_ASSESSMENT_JOBS',
        'campaign_id':str(cid),'ordinary_jobs':jobs,
        'completed_jobs':complete,'verified_usage_backed_completed_jobs':good,
        'completed_missing_any_assessment':missing_assessment,
        'completed_without_valid_relevance':invalid_label,
        'completed_valid_relevance_missing_linked_usage':missing_usage,
        'completed_usage_without_valid_relevance':usage_without_valid_label,
        'completed_zero_attempts':zero_attempts,
        'completed_requiring_manual_history_review':discrepancies,
        'pending_jobs':pending,'processing_jobs':processing,'failed_jobs':failed,
        'completion_reconciled':complete==good,
        'counts_reconciled':jobs==complete+pending+processing+failed,
        'missing_usage_requires_manual_history_review':True,
        'automatically_retry_missing_usage':False,
        'relevance_is_not_legal_determination':True,
        'source_text_or_ids_returned':False,
        'paid_provider_called':False,'database_writes':0,
    }
