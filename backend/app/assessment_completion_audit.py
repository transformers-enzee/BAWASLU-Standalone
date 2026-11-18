"""Read-only, authorization-scoped assessment job completion verification.

An AI usage row can belong to an older assessment version; manual review and
sentiment-only updates may append later versions. An absent usage-backed
classification is an audit discrepancy, not permission to retry provider calls.
"""
from datetime import datetime, timedelta
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
        AssessmentAIUsage.campaign_id==AIAssessmentJob.campaign_id,
        AssessmentAIUsage.request_kind=='RELEVANCE_AND_CLASSIFICATION'))
    # A usage row only verifies completion when its own assessment has an
    # actual relevance label, rather than a sentiment-only UNASSESSED row.
    verified=exists().where(and_(
        EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
        EvidenceAssessment.result_id==AIAssessmentJob.result_id,
        func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).in_(_VALID_LABELS),
        AssessmentAIUsage.assessment_id==EvidenceAssessment.id,
        AssessmentAIUsage.campaign_id==AIAssessmentJob.campaign_id,
        AssessmentAIUsage.request_kind=='RELEVANCE_AND_CLASSIFICATION'))
    sentiment_usage=exists().where(and_(
        EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
        EvidenceAssessment.result_id==AIAssessmentJob.result_id,
        AssessmentAIUsage.assessment_id==EvidenceAssessment.id,
        AssessmentAIUsage.campaign_id==AIAssessmentJob.campaign_id,
        AssessmentAIUsage.request_kind=='STANDALONE_SENTIMENT'))
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
        amount(and_(completed,valid_assessment,~usage_link,sentiment_usage)),
        amount(AIAssessmentJob.state=='PENDING'),
        amount(AIAssessmentJob.state=='PROCESSING'),
        amount(AIAssessmentJob.state=='FAILED'),
        amount(AIAssessmentJob.state=='SUPERSEDED_ASSESSED'))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT').one())
    (jobs,complete,good,missing_assessment,invalid_label,missing_usage,
     usage_without_valid_label,zero_attempts,sentiment_only,pending,processing,failed,superseded)=map(int,counts)
    discrepancies=complete-good
    # A PROCESSING job older than the interrupted-call grace window is a
    # historical review signal, NOT a safe instruction to replay provider work.
    stale_cutoff=datetime.utcnow()-timedelta(minutes=10)
    stale_processing=(db.query(func.count(AIAssessmentJob.id))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                AIAssessmentJob.state=='PROCESSING',
                AIAssessmentJob.updated_at<stale_cutoff).scalar()) or 0
    # Scope the source-side usage audit by both assessment and usage campaign.
    # A mismatched campaign ID must not be silently considered verified usage.
    total_usage,mismatched,unreported,negative_tokens,missing_model=(db.query(
        func.count(AssessmentAIUsage.id),
        func.coalesce(func.sum(case((
            AssessmentAIUsage.campaign_id!=EvidenceAssessment.campaign_id,1
        ),else_=0)),0),
        func.coalesce(func.sum(case((
            AssessmentAIUsage.usage_reported==False,1
        ),else_=0)),0),
        func.coalesce(func.sum(case((
            (AssessmentAIUsage.input_tokens<0)|(AssessmentAIUsage.output_tokens<0),1
        ),else_=0)),0),
        func.coalesce(func.sum(case((
            func.length(func.trim(func.coalesce(AssessmentAIUsage.provider_model,'')))==0,1
        ),else_=0)),0))
        .join(EvidenceAssessment,EvidenceAssessment.id==AssessmentAIUsage.assessment_id)
        .filter(EvidenceAssessment.campaign_id==cid).one())
    # Historical gaps are not safe to replay. Read only aggregates, never
    # source IDs or individual job metadata. A later edited version can be
    # the latest model even when earlier work is the original assessment.
    from sqlalchemy.orm import aliased
    latest_id=(db.query(EvidenceAssessment.id)
        .filter(EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
                EvidenceAssessment.result_id==AIAssessmentJob.result_id)
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).limit(1)
        .correlate(AIAssessmentJob).scalar_subquery())
    latest=aliased(EvidenceAssessment)
    # A verified historical provider call need not be the latest assessment
    # version. Relevance revisions are legitimate, but a completed job whose
    # latest version is UNASSESSED or missing needs a distinct review signal.
    latest_label=func.upper(func.trim(func.coalesce(latest.relevance_label,'')))
    latest_rows=(db.query(
        func.count(AIAssessmentJob.id),
        func.coalesce(func.sum(case((and_(
            completed,latest.id.is_(None)),1),else_=0)),0),
        func.coalesce(func.sum(case((and_(
            completed,latest.id.is_not(None),
            ~latest_label.in_(_VALID_LABELS)),1),else_=0)),0),
        func.coalesce(func.sum(case((and_(
            completed,verified,
            ~latest_label.in_(_VALID_LABELS)),1),else_=0)),0))
        .outerjoin(latest,latest.id==latest_id)
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                completed).one())
    _,latest_missing,latest_invalid,verified_historical_with_invalid_latest=latest_rows
    versions=(db.query(func.count(EvidenceAssessment.id))
        .filter(EvidenceAssessment.campaign_id==AIAssessmentJob.campaign_id,
                EvidenceAssessment.result_id==AIAssessmentJob.result_id)
        .correlate(AIAssessmentJob).scalar_subquery())
    is_gap=and_(completed,valid_assessment,~usage_link)
    history=(db.query(
        func.count(AIAssessmentJob.id),
        amount(and_(is_gap,AIAssessmentJob.attempts>0)),
        amount(and_(is_gap,versions>1)),
        func.min(case((is_gap,AIAssessmentJob.created_at),else_=None)),
        func.max(case((is_gap,AIAssessmentJob.created_at),else_=None)))
        .outerjoin(latest,latest.id==latest_id)
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                is_gap).one())
    gap_jobs,attempted_gaps,multi_version_gaps,earliest_gap,latest_gap=history
    # Count by the latest saved model *label*. This is a grouping clue, not
    # evidence of which historical request incurred an AI provider charge.
    model_rows=(db.query(
        func.coalesce(func.nullif(latest.model_version,''),'UNSPECIFIED'),
        func.count(AIAssessmentJob.id))
        .outerjoin(latest,latest.id==latest_id)
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                is_gap)
        .group_by(func.coalesce(func.nullif(latest.model_version,''),'UNSPECIFIED'))
        .order_by(func.count(AIAssessmentJob.id).desc()).limit(10).all())
    model_buckets=[{'latest_model':str(name)[:100],'jobs':int(n)}
                   for name,n in model_rows]
    return {
        'scope':'AUTHORIZED_CAMPAIGN_ORDINARY_ASSESSMENT_JOBS',
        'campaign_id':str(cid),'ordinary_jobs':jobs,
        'completed_jobs':complete,'verified_usage_backed_completed_jobs':good,
        'completed_missing_any_assessment':missing_assessment,
        'completed_without_valid_relevance':invalid_label,
        'completed_valid_relevance_missing_linked_usage':missing_usage,
        'completed_usage_without_valid_relevance':usage_without_valid_label,
        'completed_zero_attempts':zero_attempts,
        'completed_sentiment_usage_without_classification_usage':sentiment_only,
        'classification_usage_request_kind_required':True,
        'latest_completion_classification_review':{
            'completed_missing_latest_assessment':int(latest_missing),
            'completed_latest_unclassified_or_invalid':int(latest_invalid),
            'historically_usage_verified_but_latest_invalid':int(verified_historical_with_invalid_latest),
            'requires_manual_review':bool(latest_missing or latest_invalid),
            'does_not_invalidate_historical_usage':True,
            'automatic_reassessment_permitted':False,
        },
        'completed_requiring_manual_history_review':discrepancies,
        'historical_missing_usage_triage':{
            'completed_valid_relevance_without_usage':int(gap_jobs),
            'with_recorded_attempts':int(attempted_gaps),
            'with_multiple_assessment_versions':int(multi_version_gaps),
            'earliest_job_created_date':earliest_gap.date().isoformat() if earliest_gap else None,
            'latest_job_created_date':latest_gap.date().isoformat() if latest_gap else None,
            'latest_saved_model_distribution':model_buckets,
            'latest_model_is_not_original_call_proof':True,
            'cause_of_missing_usage':'UNDETERMINED',
            'manual_provenance_review_required':int(gap_jobs)>0,
            'automatic_reprocessing_permitted':False,
        },
        'usage_lineage_quality':{
            'assessment_linked_usage_rows':int(total_usage),
            'campaign_id_mismatch':int(mismatched),
            'provider_usage_not_reported':int(unreported),
            'negative_token_counts':int(negative_tokens),
            'provider_model_missing':int(missing_model),
            'quality_checks_passed':not (mismatched or unreported or negative_tokens or missing_model),
            'usage_records_repaired':0,
        },
        'stale_processing_jobs':int(stale_processing),
        'stale_processing_requires_history_review':int(stale_processing)>0,
        'stale_processing_automatically_retried':False,
        'pending_jobs':pending,'processing_jobs':processing,'failed_jobs':failed,
        'superseded_assessed_jobs':superseded,
        'completion_reconciled':complete==good,
        'counts_reconciled':jobs==complete+pending+processing+failed+superseded,
        'missing_usage_requires_manual_history_review':True,
        'automatically_retry_missing_usage':False,
        'relevance_is_not_legal_determination':True,
        'source_text_or_ids_returned':False,
        'paid_provider_called':False,'database_writes':0,
    }
