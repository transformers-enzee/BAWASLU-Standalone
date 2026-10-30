"""Difficult text cases for zero-credit classification screening."""
from app.processing_hints import (
    source_hints, public_concern_cues, incident_location_cues,
    summarize_scoped_findings, attention_evidence_readiness,
)


def test_public_concern_requires_explicit_grievance_not_generic_election_talk():
    assert public_concern_cues('Rapat persiapan pemilu berlangsung lancar')==[]
    assert public_concern_cues('Tidak ada keluhan warga soal DPT')==[]
    assert public_concern_cues('Warga mempertanyakan daftar pemilih di TPS')==['Warga mempertanyakan']


def test_public_concern_is_provisional_only_for_scoped_relevant_saved_findings():
    rows=[{'id':'5','campaign_id':'A','text_content':'Warga mempertanyakan daftar pemilih',
           'relevance_label':'RELEVANT','potential_issues':[],'is_flagged':False}]
    result=summarize_scoped_findings(rows)
    item=result['intelligence_players']['Public Concerns']['entries'][0]
    assert item['status']=='TEXTUAL_CONCERN_REVIEW_CANDIDATE'
    assert item['evidence_verified'] is False
    assert result['intelligence_players']['Needs Attention']['count']==0


def test_negated_public_concern_does_not_enter_player():
    rows=[{'id':'5','campaign_id':'A','text_content':'Tidak ada keluhan warga mengenai DPT',
           'relevance_label':'RELEVANT','potential_issues':[],'is_flagged':False}]
    assert summarize_scoped_findings(rows)['intelligence_players']['Public Concerns']['count']==0


def test_incident_locations_require_explicit_incident_context_and_remain_unverified():
    hints=source_hints('Akun di Riau mengabarkan dugaan pelanggaran di Jawa Timur')
    assert hints['incident_location_cues_unverified']==['Jawa Timur']
    assert hints['incident_jurisdiction_status']=='UNVERIFIED'
    assert hints['province_mentions_are_incident_location'] is False
    assert incident_location_cues('Akun berada di Riau dan pemilu berlangsung')==[]


def test_attention_evidence_quality_requires_verbatim_quote_not_summary():
    row={'text_content':'Dugaan pelanggaran pemilu di Riau dilaporkan warga.',
         'potential_issues':[{'evidence_quote':'Dugaan pelanggaran pemilu di Riau'}],
         'flag_review_status':'FURTHER_INVESTIGATION'}
    posture=attention_evidence_readiness(row)
    assert posture['evidence_quality']=='SOURCE_QUOTED_UNCORROBORATED'
    assert posture['urgency']=='OFFICER_REQUESTED_FOLLOW_UP'
    assert posture['seriousness']=='NOT_ASSESSED'
    assert posture['legal_violation_confirmed'] is False
    row['potential_issues']=[{'evidence_quote':'fabricated quote'}]
    assert attention_evidence_readiness(row)['evidence_quality']=='NOT_ASSESSED'


def test_attention_record_keeps_human_triage_not_automated_legal_conclusion():
    row={'id':'6','campaign_id':'A','text_content':'Dugaan pelanggaran pemilu di Riau',
         'potential_issues':[{'evidence_quote':'Dugaan pelanggaran pemilu'}],
         'is_flagged':True,'flag_review_status':'FURTHER_INVESTIGATION'}
    result=summarize_scoped_findings([row])
    entry=result['needs_attention_candidates'][0]
    assert entry['urgency']=='OFFICER_REQUESTED_FOLLOW_UP'
    assert entry['legal_violation_confirmed'] is False
    assert result['processing_diagnostics']['posts_with_source_quoted_attention_evidence']==1


def test_inbox_ui_shows_saved_player_counts_without_paid_ai():
    from pathlib import Path
    frontend=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text(encoding='utf-8')
    assert 'classification_processing' in frontend
    assert 'Five Intelligence Players · saved evidence screening' not in frontend
    assert 'Processing and QA diagnostics' in frontend
    radar=(Path(__file__).resolve().parents[2]/'frontend/src/pages/SmartRadar.jsx').read_text()
    assert 'aria-label="Command Centre"' in radar
