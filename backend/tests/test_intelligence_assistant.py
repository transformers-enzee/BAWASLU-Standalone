from app.intelligence_assistant import assistant_evidence_record, assistant_record_view
from app.models import IntelligenceItem

def test_assistant_validation_timestamp_is_canonical_utc():
    item=IntelligenceItem(
      intelligence_id='INT-2026-TEST01',
      title='Timestamp',
      validated_at='2026-10-08T09:57:16+00:00',
      review_status='Validated as Relevant Intelligence',
      jurisdiction_type='National',
      jurisdiction_confirmed=True
    )
    evidence=assistant_evidence_record(item)
    view=assistant_record_view(item)
    assert evidence['validated_at']=='2026-10-08T09:57:16Z'
    assert evidence['validated_at_display_utc']=='2026-10-08 09:57:16 UTC'
    assert view['validated_at']=='2026-10-08T09:57:16Z'
    assert view['validated_at_display_utc']=='2026-10-08 09:57:16 UTC'

def test_assistant_flags_legacy_validated_unresolved_record():
    item=IntelligenceItem(
      intelligence_id='INT-2026-TEST02',
      title='Legacy validation',
      review_status='Validated as Relevant Intelligence',
      validated_at='2026-10-08T09:57:16Z',
      jurisdiction_type='Unresolved',
      jurisdiction_confirmed=False
    )
    evidence=assistant_evidence_record(item)
    view=assistant_record_view(item)
    assert evidence['validation_governance_state']=='LEGACY_GOVERNANCE_EXCEPTION'
    assert 'JURISDICTION_NOT_CONFIRMED' in evidence['validation_governance_blockers']
    assert view['validation_governance_state']=='LEGACY_GOVERNANCE_EXCEPTION'

def test_assistant_marks_current_validated_record_clean():
    item=IntelligenceItem(
      intelligence_id='INT-2026-TEST03',
      title='Current validation',
      review_status='Validated as Relevant Intelligence',
      validated_at='2026-10-12T01:02:03Z',
      jurisdiction_type='National',
      jurisdiction_confirmed=True
    )
    evidence=assistant_evidence_record(item)
    assert evidence['validation_governance_state']=='CURRENT_RULES_SATISFIED'
    assert evidence['validation_governance_blockers']==[]
