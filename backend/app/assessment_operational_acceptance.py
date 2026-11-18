"""Deterministic, read-only preflight acceptance for assessment operations.

This is an advisory decision only. No result grants permission to invoke AI.
Pending manual work and unattended worker readiness are kept separate.
"""
_HISTORICAL=('STALE_PROCESSING','INTERRUPTED_HISTORY_REVIEW',
    'COMPLETION_PROVENANCE_GAP','SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF',
    'COMPLETED_LATEST_CLASSIFICATION_REVIEW','CLASSIFICATION_USAGE_LIFECYCLE_CONFLICT',
    'USAGE_INTEGRITY_WARNING','SUPERSEDED_CLASSIFICATION_CHANGED',
    'SNAPSHOT_AGGREGATE_DRIFT')
_QUEUE=('UNQUEUED_EVIDENCE','PENDING_ALREADY_ASSESSED','INVENTORY_RECONCILIATION_WARNING')

# Each recommended action is advisory. Availability and authorization of the
# underlying action are checked by the existing campaign endpoint at runtime.
# These are resolution *criteria*, not claims that a problem has been fixed.
_RESOLUTIONS={
    'UNQUEUED_EVIDENCE':('QUEUE','Review campaignAssessmentJobReconcile preview; reconcile only genuinely eligible evidence',
        'Refresh overview and confirm eligible ordinary monitoring links have matching durable jobs',
        'campaignAssessmentJobReconcile'),
    'PENDING_ALREADY_ASSESSED':('QUEUE','Inspect latest saved relevance; use confirmed no-credit supersession only for eligible pending jobs',
        'Refresh and confirm no already-classified ordinary pending jobs remain',
        'campaignAssessmentSupersededPreview'),
    'INVENTORY_RECONCILIATION_WARNING':('QUEUE','Compare campaign evidence links and distinct job states; investigate duplicate links before edits',
        'Refresh and confirm independently computed inventory totals reconcile',None),
    'STALE_PROCESSING':('HISTORY','Investigate original provider call, charge and response before confirmed interrupted-job quarantine',
        'After explicit review, confirm stale PROCESSING count is zero and any quarantined jobs remain tracked for follow-up',
        'campaignAssessmentInterruptedPreview'),
    'INTERRUPTED_HISTORY_REVIEW':('HISTORY','Verify interrupted request history, provider result and possible billing; do not auto-retry',
        'Clear only after independent history review; quarantine itself does not resolve unknown provider outcome',None),
    'COMPLETION_PROVENANCE_GAP':('HISTORY','Cross-check historical assessment versions and original classification-provider usage',
        'Confirm completion provenance with authentic records; do not fabricate usage or replay calls',None),
    'SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF':('HISTORY','Review classification-request provenance separately from sentiment usage',
        'Confirm a matching relevance/classification provider usage record or document unresolved history',None),
    'COMPLETED_LATEST_CLASSIFICATION_REVIEW':('HISTORY','Review latest officer assessment against preserved historical provider usage',
        'Confirm valid latest relevance while retaining original classification audit trail',None),
    'CLASSIFICATION_USAGE_LIFECYCLE_CONFLICT':('HISTORY','Compare saved classification usage and job state; check database uniqueness',
        'Resolve inconsistent job state only after verifying historical provider activity',None),
    'USAGE_INTEGRITY_WARNING':('HISTORY','Inspect provider model, token reporting and linked campaign provenance',
        'Reaudit usage integrity from original records; never synthesize provider usage',None),
    'SUPERSEDED_CLASSIFICATION_CHANGED':('HISTORY','Review newer assessment versions against superseded queue history',
        'Resolve latest classification inconsistencies without automatically reopening paid work',None),
    'SNAPSHOT_AGGREGATE_DRIFT':('HISTORY','Refresh the on-demand status; independently compare queue and audit aggregates if inconsistent',
        'Verify the aggregate count differences disappear or identify a persistent data issue',None),
}

def assessment_resolution_plan(issues):
    """Stable, non-identifying instructions for each active exception."""
    active=[]
    for issue in issues:
        code=str(issue.get('code',''))
        count=max(0,int(issue.get('count',0)))
        if not count:
            continue
        group,action,criterion,preview=_RESOLUTIONS.get(code,(
            'HISTORY','Investigate the unrecognized exception code before taking action',
            'Recheck the source diagnostic after investigation',None))
        active.append({'code':code,'group':group,'affected_count':count,
            'investigation_or_action':action,'clearance_criterion':criterion,
            'existing_read_only_preview_action':preview,
            'read_only_preview_payload':{'dry_run':True} if code=='UNQUEUED_EVIDENCE' else {},
            'preview_action_is_not_implicitly_read_only':code=='UNQUEUED_EVIDENCE',
            'requires_separate_permissions_and_confirmation':True,
            'automated_remediation_authorized':False})
    # History comes first, then no-credit queue reconciliation. Preserve
    # code ordering within each category so clients receive stable results.
    return sorted(active,key=lambda x:(0 if x['group']=='HISTORY' else 1,x['code']))

def assess_operational_acceptance(readiness, issues):
    codes={str(i['code']) for i in issues if int(i.get('count',0))>0}
    claimable=max(0,int(readiness['queue_counts']['claimable_pending_with_text']))
    available=min(claimable,max(0,int(readiness['per_run_request_limit'])),
                  max(0,int(readiness['daily_remaining'])),
                  max(0,int(readiness['lifetime_remaining'])),20)
    # Manual batches require a provider and Postgres quota reservation, NOT
    # the background worker or automatic-screening switches.
    blockers=[]
    if not readiness['ai_provider_configured']:blockers.append('PROVIDER_NOT_CONFIGURED')
    if not readiness['database_supports_reservations']:blockers.append('QUOTA_RESERVATION_UNAVAILABLE')
    if not readiness['per_run_request_limit']:blockers.append('PER_RUN_CAP_ZERO')
    if not readiness['daily_remaining'] or not readiness['lifetime_remaining']:
        blockers.append('REQUEST_BUDGET_UNAVAILABLE')
    unknown_codes=codes.difference(_HISTORICAL).difference(_QUEUE)
    # An unfamiliar future exception must fail closed, never be described as
    # eligible for paid processing just because the code is new to this module.
    status=('HOLD_FOR_HISTORY_REVIEW' if codes.intersection(_HISTORICAL) or unknown_codes
        else 'HOLD_FOR_QUEUE_RECONCILIATION' if codes.intersection(_QUEUE)
        else 'NO_ELIGIBLE_WORK' if not claimable
        else 'CONFIGURATION_OR_BUDGET_BLOCKED' if blockers
        else 'ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL')
    plan=assessment_resolution_plan(issues)
    return {
        'resolution_plan':plan,
        'outstanding_resolution_categories':len(plan),
        'all_exception_criteria_satisfied':not bool(plan),
        'status':status,
        'historical_review_codes':sorted(codes.intersection(_HISTORICAL).union(unknown_codes)),
        'unrecognized_review_codes':sorted(unknown_codes),
        'queue_reconciliation_codes':sorted(codes.intersection(_QUEUE)),
        'manual_configuration_blockers':blockers,
        'eligible_unassessed_jobs':claimable,
        'manual_request_capacity_if_separately_approved':available if not blockers and status=='ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL' else 0,
        'automatic_worker_ready':bool(readiness['ready_to_process']) and not bool(codes),
        'read_only_preflight':True,
        'requires_refreshed_verification_after_resolution':True,
        'campaign_wide_hold_is_advisory_not_a_job_lock':True,
        'is_paid_ai_authorization':False,
        'needs_explicit_manual_approval':True,
        'automatically_retry_unknown_provider_requests':False,
        'database_writes':0,
        'paid_provider_called':False,
    }
