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

from app.intelligence_assistant import ANSWER_SCHEMA, SYSTEM_PROMPT, format_assistant_answer, deterministic_assistant_answer

def test_operational_actions_required_in_schema():
    assert 'recommended_actions' in ANSWER_SCHEMA['required']
    assert ANSWER_SCHEMA['properties']['recommended_actions']['maxItems'] == 5
    assert 'bounded evidence selection' in SYSTEM_PROMPT

def test_actionable_answer_section_is_rendered():
    answer=format_assistant_answer({
        'answer_summary':'Contoh',
        'key_observations':[],
        'evidence_status':[],
        'recommended_actions':['Tim penelaah: periksa sumber dan catat hasil verifikasi.'],
        'date_basis':'Tidak ada',
        'limitations':[]
    })
    assert 'REKOMENDASI TINDAK LANJUT' in answer
    assert 'Tim penelaah: periksa sumber' in answer

def test_fallback_does_not_claim_full_database_coverage():
    output=deterministic_assistant_answer('Analisis sentimen Gibran', [{
        'record_id':'INT-TEST-001',
        'title':'Contoh uji',
        'review_status':'',
        'verification_status':'UNVERIFIED',
    }])
    assert 'bukan total seluruh dataset' in output['answer']
    assert 'REKOMENDASI TINDAK LANJUT' in output['answer']
    assert output['cited_record_ids']==['INT-TEST-001']
