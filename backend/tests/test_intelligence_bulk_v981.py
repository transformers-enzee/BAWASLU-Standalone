"""No-cost cross-player, source integrity and Shahrin QA acceptance tests."""
import pytest
from app.processing_hints import summarize_scoped_findings
from app.qa_saved_accuracy import qa_history_summary,summarize_version_stats,QUERY
from app.access import default_permissions
TEXT='Warga mempertanyakan daftar pemilih dan meminta penjelasan BAWASLU.'
QUOTE='Warga mempertanyakan daftar pemilih dan meminta penjelasan'
def actor(role='National Administrator'):
    return {'id':'11','role':role,'status':'Active','geographic_scope':'Nationwide',
        'permissions':default_permissions(role)}

def test_multiple_players_topics_summaries_and_attention_from_one_saved_post():
    row={'id':'1','campaign_id':'91','text_content':TEXT,'relevance_label':'RELEVANT',
        'topic_labels':['Electoral Operations','BAWASLU Reputation'],
        'public_concern_signals':[{'evidence_quote':QUOTE,'concern':'Voter list question'}],
        'attention_assessment':{'status':'AI_ASSESSMENT_UNVERIFIED',
            'seriousness':'HIGH','urgency':'MEDIUM','evidence_quote':QUOTE},
        'player_summaries':[{'player':'Public Concerns',
            'source_quote':QUOTE,'summary':'Residents question the voter list.',
            'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW'}],
        'potential_issues':[],'is_flagged':False}
    summary=summarize_scoped_findings([row])
    assert {x['topic'] for x in summary['topic_groups']}=={
        'Electoral Operations','BAWASLU Reputation'}
    assert summary['intelligence_players']['Public Concerns']['count']==1
    assert summary['intelligence_players']['Needs Attention']['count']==1
    assert summary['intelligence_players']['Potential Violations']['count']==0
    assert summary['intelligence_players']['Public Concerns']['entries'][0]['ai_summary_draft']['source_quote']==QUOTE
    entry=summary['needs_attention_candidates'][0]
    assert entry['urgency']=='MEDIUM' and entry['seriousness']=='HIGH'
    assert entry['legal_violation_confirmed'] is False
    assert summary['paid_provider_called'] is False

def test_source_change_removes_stale_ai_attention_and_draft():
    row={'id':'1','campaign_id':'91','text_content':'Unrelated text.',
        'relevance_label':'RELEVANT','potential_issues':[],
        'attention_assessment':{'status':'AI_ASSESSMENT_UNVERIFIED',
            'seriousness':'HIGH','urgency':'HIGH','evidence_quote':QUOTE},
        'player_summaries':[{'player':'Public Concerns',
            'summary':'A long speculative summary about old concerns.',
            'status':'AI_DRAFT_REQUIRES_HUMAN_REVIEW','source_quote':QUOTE}]}
    summary=summarize_scoped_findings([row])
    assert summary['intelligence_players']['Needs Attention']['count']==0
    assert summary['intelligence_players']['Public Concerns']['count']==0

def test_multiple_players_can_use_same_source():
    row={'id':'1','campaign_id':'91','text_content':TEXT,'relevance_label':'RELEVANT',
        'potential_issues':[{'evidence_quote':QUOTE}],
        'public_concern_signals':[{'evidence_quote':QUOTE,'concern':'Voter register'}],
        'is_flagged':True}
    summary=summarize_scoped_findings([row])
    assert summary['intelligence_players']['Potential Violations']['count']==1
    assert summary['intelligence_players']['Public Concerns']['count']==1
    assert summary['intelligence_players']['Needs Attention']['count']==1
    assert summary['intelligence_players']['Potential Violations']['entries'][0]['evidence_verified'] is False

def test_historical_accuracy_cannot_pass_by_tiny_sample_or_unsigned_labels():
    values=summarize_version_stats([
        {'prompt_version':'v17','model':'mock','evaluated':33,'correct':20,
         'missing_prediction':0,'unsigned_labels':33},
        {'prompt_version':'tiny','model':'mock','evaluated':2,'correct':2,
         'missing_prediction':0,'unsigned_labels':0}])
    assert values[0]['accuracy_percent']==60.6
    assert not values[0]['accuracy_target_met']
    assert values[1]['accuracy_percent']==100.0
    assert not values[1]['accuracy_target_met']

def test_private_qa_history_requires_admin_and_excludes_holdout():
    class NoDB:
        def execute(self,*_):raise AssertionError('Unauthorized query')
    with pytest.raises(PermissionError):
        qa_history_summary(NoDB(),actor('Viewer'))
    with pytest.raises(PermissionError):
        qa_history_summary(NoDB(),{**actor(),'permissions':{'administration':False}})
    query=str(QUERY)
    assert "NOT ILIKE '%holdout%'" in query
    assert "GROUP BY prompt_version,model" in query
    assert "h.source_url=sp.source_url" in query
    assert "h.original_excel_row=sp.original_excel_row" in query

def test_inbox_renders_player_and_topic_evidence_and_shahrin_qa():
    from pathlib import Path
    source=(Path(__file__).resolve().parents[2]/'frontend/src/pages/Inbox.jsx').read_text()
    for term in ('Open saved intelligence findings and source-grounded summaries',
                'SAVED_AI_TOPIC','Saved AI draft (unverified)',
                'campaignQAHistorySummary','Inspect source {id}'):
        assert term in source
