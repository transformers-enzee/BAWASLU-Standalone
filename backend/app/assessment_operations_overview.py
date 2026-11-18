"""Campaign-scoped operational status without activating processing or billing."""
from datetime import datetime, timezone
from .campaign_ai_readiness import campaign_ai_worker_readiness
from .campaign_assessment_coverage import campaign_link_assessment_coverage
from .assessment_completion_audit import campaign_completion_audit
from .assessment_interrupted_recovery import interrupted_campaign_preview
from .assessment_superseded_reconcile import superseded_preview
from .assessment_operational_acceptance import assess_operational_acceptance
from .assessment_snapshot_consistency import assessment_snapshot_consistency
from .assessment_queue_triage import assessment_queue_triage
from .assessment_exception_review import assessment_exception_review

def campaign_assessment_operations_overview(db,campaign_id):
    cid=int(campaign_id)
    readiness=campaign_ai_worker_readiness(db,cid)
    coverage=campaign_link_assessment_coverage(db,cid)
    completion=campaign_completion_audit(db,cid)
    interrupted=interrupted_campaign_preview(db,cid)
    superseded=superseded_preview(db,cid)
    consistency=assessment_snapshot_consistency(readiness,completion,interrupted,superseded)
    queue_triage=assessment_queue_triage(readiness,interrupted,superseded,completion)
    issues=[]
    if not consistency['all_consistent']:
        issues.append({'code':'SNAPSHOT_AGGREGATE_DRIFT',
            'count':len(consistency['failed_checks']),
            'next_step':'Refresh read-only counts; investigate only if differences persist across refreshed snapshots.'})
    if coverage['pending_monitoring_without_job']>0:
        issues.append({'code':'UNQUEUED_EVIDENCE',
            'count':coverage['pending_monitoring_without_job'],
            'next_step':'Review no-cost job reconciliation. No AI request is started.'})
    if readiness.get('pending_already_assessed_excluded_from_ai',0)>0:
        issues.append({'code':'PENDING_ALREADY_ASSESSED',
            'count':readiness['pending_already_assessed_excluded_from_ai'],
            'next_step':'Review queue state versus saved relevance; do not resend an already-assessed source.'})
    if superseded['superseded_without_current_classification']>0:
        issues.append({'code':'SUPERSEDED_CLASSIFICATION_CHANGED',
            'count':superseded['superseded_without_current_classification'],
            'next_step':'Review the newest saved assessment and prior usage before any new processing.'})
    if interrupted['stale_processing_jobs']>0:
        issues.append({'code':'STALE_PROCESSING',
            'count':interrupted['stale_processing_jobs'],
            'next_step':'Review provider history before confirmed quarantine; never replay automatically.'})
    if interrupted['already_quarantined_for_manual_review']>0:
        issues.append({'code':'INTERRUPTED_HISTORY_REVIEW',
            'count':interrupted['already_quarantined_for_manual_review'],
            'next_step':'Verify prior provider result or billing before any new AI request.'})
    if completion['completed_requiring_manual_history_review']>0:
        issues.append({'code':'COMPLETION_PROVENANCE_GAP',
            'count':completion['completed_requiring_manual_history_review'],
            'next_step':'Review saved classifications and original provider usage lineage.'})
    if completion['completed_sentiment_usage_without_classification_usage']>0:
        issues.append({'code':'SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF',
            'count':completion['completed_sentiment_usage_without_classification_usage'],
            'next_step':'Review classification provenance; sentiment-only usage cannot verify completed relevance screening.'})
    if completion['latest_completion_classification_review']['requires_manual_review']:
        latest_review=completion['latest_completion_classification_review']
        issues.append({'code':'COMPLETED_LATEST_CLASSIFICATION_REVIEW',
            'count':latest_review['completed_missing_latest_assessment']+
                    latest_review['completed_latest_unclassified_or_invalid'],
            'next_step':'Review the latest classification without erasing historical provider-usage evidence.'})
    lifecycle_quality=completion['classification_usage_lifecycle_quality']
    if lifecycle_quality['requires_manual_review']:
        issues.append({'code':'CLASSIFICATION_USAGE_LIFECYCLE_CONFLICT',
            'count':lifecycle_quality['noncompleted_jobs_with_classification_usage']+
                    lifecycle_quality['assessments_with_duplicate_classification_usage'],
            'next_step':'Investigate job state and recorded provider calls; do not replay or delete usage automatically.'})
    if not completion['usage_lineage_quality']['quality_checks_passed']:
        issues.append({'code':'USAGE_INTEGRITY_WARNING',
            'count':sum(completion['usage_lineage_quality'][k] for k in (
                'campaign_id_mismatch','provider_usage_not_reported',
                'negative_token_counts','provider_model_missing')),
            'next_step':'Inspect recorded usage history; do not infer provider charges.'})
    if not coverage['link_count_reconciled'] or not completion['counts_reconciled']:
        issues.append({'code':'INVENTORY_RECONCILIATION_WARNING',
            'count':1,'next_step':'Investigate inconsistent campaign-link or job counts.'})
    # Independent read-only aggregates are not one transactional snapshot.
    # Report this explicitly rather than implying atomicity across subqueries.
    lifecycle_status=(
        'REVIEW_REQUIRED' if issues else
        'PROCESSING' if readiness['queue_counts']['processing'] else
        'AWAITING_PROCESSING' if readiness['queue_counts']['pending'] else
        'NO_EXCEPTIONS'
    )
    acceptance=assess_operational_acceptance(readiness,issues)
    exception_review=assessment_exception_review(issues,queue_triage,acceptance)
    return {
        'operational_acceptance':acceptance,
        'exception_review':exception_review,
        'snapshot_consistency':consistency,
        'queue_triage':queue_triage,
        'generated_at_utc':datetime.now(timezone.utc).isoformat(),
        'snapshot_is_atomic':False,
        'lifecycle_status':lifecycle_status,
        'campaign_id':str(cid),
        'scope':'ONE_AUTHORIZED_CAMPAIGN_READ_ONLY_OPERATIONS',
        'assessment_link_coverage':coverage,
        'worker_readiness':readiness,
        'completion_audit':completion,
        'interrupted_recovery':interrupted,
        'already_assessed_queue_reconciliation':superseded,
        'review_required':bool(issues),
        'issues':issues,
        'automatic_ai_authorized':False,
        'automatically_retries_jobs':False,
        'provider_budget_reserved':False,
        'paid_provider_called':False,
        'socialcrawl_credits':0,
        'database_writes':0,
    }
