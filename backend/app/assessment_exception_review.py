"""v171.4: deterministic read-only administrator exception investigation sequence.

Exception categories are advisory, not distinct job counts. Queue closure and
historical provider usage verification are independent conditions.
"""
GROUPS = (
    ('SNAPSHOT', 'Snapshot reliability', ('SNAPSHOT_AGGREGATE_DRIFT', 'INVENTORY_RECONCILIATION_WARNING')),
    ('HISTORY', 'Provider and assessment history', (
        'STALE_PROCESSING', 'INTERRUPTED_HISTORY_REVIEW',
        'CLASSIFICATION_USAGE_LIFECYCLE_CONFLICT', 'USAGE_INTEGRITY_WARNING',
        'COMPLETION_PROVENANCE_GAP', 'SENTIMENT_USAGE_NOT_CLASSIFICATION_PROOF',
        'COMPLETED_LATEST_CLASSIFICATION_REVIEW', 'SUPERSEDED_CLASSIFICATION_CHANGED')),
    ('QUEUE', 'Queue reconciliation', ('UNQUEUED_EVIDENCE', 'PENDING_ALREADY_ASSESSED')),
)

def assessment_exception_review(issues, triage, acceptance, snapshot_consistency=None):
    """Summarize aggregate exceptions without DB work or paid provider requests."""
    issue_by_code = {}
    for item in issues:
        code = str(item.get('code', '')).strip()
        count = max(0, int(item.get('count', 0)))
        if code and count:
            issue_by_code[code] = issue_by_code.get(code, 0) + count
    recognized = {code for _, _, codes in GROUPS for code in codes}
    unknown = sorted(set(issue_by_code) - recognized)
    groups = []
    for order, (group, title, codes) in enumerate(GROUPS, 1):
        entries = [{'code':code,'flag_count':issue_by_code[code]}
                   for code in codes if code in issue_by_code]
        if group == 'HISTORY' and unknown:
            entries.extend({'code':code, 'flag_count':issue_by_code[code]} for code in unknown)
        groups.append({
            'group':group, 'investigation_order':order, 'title':title,
            'active_categories':len(entries), 'exceptions':entries,
            'state':'REVIEW_REQUIRED' if entries else 'NO_RECORDED_EXCEPTIONS',
            'flag_counts_are_not_distinct_jobs':True,
        })
    snapshot_valid=bool(triage.get('buckets_partition_all_jobs',False)
        and triage.get('pending_breakdown',{}).get('breakdown_reconciled',False)
        and triage.get('completion_snapshot_reconciled',False)
        and (snapshot_consistency is None or snapshot_consistency.get('all_consistent') is True))
    history_flags=next(g['active_categories'] for g in groups if g['group']=='HISTORY')
    usage=triage.get('provider_usage_integrity') or {}
    provenance=triage.get('completion_provenance') or {}
    # No exceptions in the provider-integrity subaudit is not a proof that
    # original invoices/provider history were independently verified.
    usage_audit_available=usage.get('status') in ('NO_RECORDED_ISSUES','REVIEW_REQUIRED')
    completion_audit_available=bool(provenance) and all(k in provenance for k in (
        'completed_jobs','usage_backed_completed','requires_historical_usage_review',
        'completed_partition_reconciled'))
    missing_audits=[]
    if not usage_audit_available: missing_audits.append('PROVIDER_USAGE_INTEGRITY')
    if not completion_audit_available: missing_audits.append('COMPLETION_PROVENANCE')
    # Fail closed if nested diagnostics disagree with the top-level issue list.
    # Cross-query reads can race; never silently treat missing issue codes
    # as proof that the underlying diagnostic counts have cleared.
    diagnostic_conflicts=[]
    if usage.get('status')=='REVIEW_REQUIRED' and not any(
        code in issue_by_code for code in
        ('USAGE_INTEGRITY_WARNING','CLASSIFICATION_USAGE_LIFECYCLE_CONFLICT')):
        diagnostic_conflicts.append('PROVIDER_FLAGS_MISSING_FROM_EXCEPTIONS')
    if max(0,int(provenance.get('requires_historical_usage_review',0))) and (
        'COMPLETION_PROVENANCE_GAP' not in issue_by_code):
        diagnostic_conflicts.append('PROVENANCE_GAPS_MISSING_FROM_EXCEPTIONS')
    if provenance.get('completed_partition_reconciled') is False:
        diagnostic_conflicts.append('COMPLETED_PARTITION_DRIFT')
    if triage.get('status')=='RECHECK_INDEPENDENT_SNAPSHOTS':
        diagnostic_conflicts.append('QUEUE_SNAPSHOT_RECHECK_REQUIRED')
    if (snapshot_consistency is not None and
        snapshot_consistency.get('failed_checks') and
        snapshot_consistency.get('all_consistent') is True):
        diagnostic_conflicts.append('CONTRADICTORY_SNAPSHOT_REPORT')
    history_verified=False
    queue_review_clear=next(g['active_categories'] for g in groups if g['group']=='QUEUE')==0
    queue_has_no_active_work=triage.get('status')=='NO_ACTIVE_WORK'
    # The legacy acceptance preflight evaluates its own exception list. This
    # consolidated gate also accounts for independently observed audit absence,
    # cross-snapshot drift and unknown future exception codes. It cannot grant
    # authorization; its only role is to block misleading UI approval hints.
    blockers=[]
    if snapshot_consistency is None: blockers.append('SNAPSHOT_AUDIT_UNAVAILABLE')
    if not snapshot_valid: blockers.append('UNRECONCILED_SNAPSHOT')
    if missing_audits: blockers.append('MISSING_DIAGNOSTIC_AUDITS')
    if diagnostic_conflicts: blockers.append('CONFLICTING_DIAGNOSTICS')
    if unknown: blockers.append('UNRECOGNIZED_EXCEPTION')
    if history_flags: blockers.append('HISTORICAL_EXCEPTION')
    if not queue_review_clear: blockers.append('QUEUE_RECONCILIATION_REQUIRED')
    original_status=str((acceptance or {}).get('status') or 'UNKNOWN')
    capacity=max(0,int((acceptance or {}).get('manual_request_capacity_if_separately_approved') or 0))
    if original_status!='ELIGIBLE_FOR_SEPARATE_MANUAL_APPROVAL':
        blockers.append('LEGACY_PREFLIGHT_NOT_ELIGIBLE')
    if capacity==0: blockers.append('NO_SEPARATELY_APPROVABLE_CAPACITY')
    review_gate={
        'status':'BLOCKED' if blockers else 'PREFLIGHT_ONLY',
        'blockers':blockers,
        'legacy_preflight_status':original_status,
        'legacy_preflight_capacity':capacity,
        'displayable_capacity_if_all_checks_clear':capacity if not blockers else 0,
        'separate_explicit_approval_required':True,
        'never_authorizes_paid_processing':True,
        'no_provider_requests':True,
        'snapshot_audit_supplied':snapshot_consistency is not None,
    }
    return {
        'manual_approval_review_gate':review_gate,
        'groups':groups,
        'review_order':['SNAPSHOT','HISTORY','QUEUE'],
        'active_exception_categories':sum(g['active_categories'] for g in groups),
        'unknown_codes':unknown,
        'snapshot_reconciled':snapshot_valid,
        'queue_exceptions_clear':queue_review_clear,
        'queue_has_no_active_work':queue_has_no_active_work,
        'usage_audit_available':usage_audit_available,
        'completion_audit_available':completion_audit_available,
        'missing_audits':missing_audits,
        'diagnostic_conflicts':diagnostic_conflicts,
        'diagnostics_consistent':not diagnostic_conflicts,
        'history_verification_blocked_by_missing_audits':bool(missing_audits),
        'historical_provider_usage_independently_verified':history_verified,
        'historical_usage_state':('AUDIT_UNAVAILABLE' if missing_audits else
                                  'REVIEW_REQUIRED' if history_flags else
                                  'NOT_INDEPENDENTLY_VERIFIED'),
        'completion_counts_reconciled':bool(provenance.get('completed_partition_reconciled',False)),
        'no_issues_does_not_verify_provider_usage':True,
        'administrative_queue_clearance_is_not_provider_usage_proof':True,
        'next_review_step':('REFRESH_SNAPSHOT' if not snapshot_valid or diagnostic_conflicts else
                            'RESTORE_MISSING_AUDITS' if missing_audits else
                            'INVESTIGATE_PROVIDER_HISTORY' if history_flags else
                            'RECONCILE_QUEUE' if not queue_review_clear else
                            'VERIFY_HISTORICAL_USAGE_INDEPENDENTLY'),
        'read_only':True,
        'counts_may_overlap_across_issue_codes':True,
        'snapshot_readings_are_nonatomic':True,
        'requires_separate_authorization_for_remediation':True,
        'automatic_paid_ai_authorized':False,
        'database_writes':0,
        'paid_provider_called':False,
    }
