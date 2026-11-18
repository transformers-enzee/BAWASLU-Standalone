"""v169.1 compare real Inbox eligibility with Command Center activity/coverage.

All evidence is synthetic and loaded in isolated SQLite. No provider calls,
casework mutations or production Supabase changes.
"""
from datetime import datetime
from app.models import SocialListeningResult,EvidenceAssessment,CampaignEvidence,MonitoringCampaign
from app.campaigns import campaign_action
from app.command_center import build_command_center
from app.inbox_radar import compile_inbox_findings
from app.module_acceptance_evidence import module_acceptance_evidence
from test_e2e_handoff_acceptance_v1689 import fixture

def view(db,p):
    inbox=campaign_action(db,p,'campaignIntelligenceInbox',{'campaign_id':'31'},'31')
    command=build_command_center(db,p,{'period':'all'})
    return inbox,command

def test_latest_saved_relevance_matches_command_indicator_and_inbox():
    e,db,p=fixture()
    try:
        inbox,command=view(db,p)
        assert {str(x['id']) for x in inbox['findings']}=={'1','3'}
        assert command['indicators']['relevant_mentions']==2
        assert command['coverage']['relevant_distinct_posts']==2
        assert module_acceptance_evidence(db)['counts']['eligible_saved_inbox_links']==2
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()

def test_preliminary_relevant_source_does_not_inflate_coverage_or_alerts():
    e,db,p=fixture()
    try:
        db.add(SocialListeningResult(id=7,run_id=1,platform='twitter-ai-search',
            text_content='A synthetic complaint about Bawaslu voter register',
            author_name='Test',canonical_url='https://example.invalid/seven',
            published_at=datetime.utcnow().date().isoformat()+'T08:00:00Z'))
        db.add(CampaignEvidence(campaign_id=31,result_id=7,match_method='KEYWORD'))
        db.add(EvidenceAssessment(campaign_id=31,result_id=7,assessment_version=1,
            relevance_label='RELEVANT',model_version='PRISM_PENDING_OPENAI',
            sentiment='NEGATIVE'))
        db.commit()
        inbox,command=view(db,p)
        assert {str(x['id']) for x in inbox['findings']}=={'1','3'}
        assert command['indicators']['relevant_mentions']==2
        assert command['coverage']['assessed_posts_in_period']==3
        assert command['coverage']['unassessed_posts_in_period']==3
        assert command['coverage']['captured_posts_in_period']==6
        assert module_acceptance_evidence(db)['counts']['eligible_saved_inbox_links']==2
        assert command['paid_provider_called'] is False
    finally:db.close();e.dispose()

def test_platform_activity_uses_same_normalized_vocabulary_as_inbox():
    e,db,p=fixture()
    try:
        db.get(SocialListeningResult,1).platform='twitter-ai-search'
        db.get(SocialListeningResult,3).platform='x'
        db.commit()
        inbox,command=view(db,p)
        normalized={x['id']:x['platform'] for x in inbox['findings']}
        assert normalized['1']=='twitter-ai-search'
        assert normalized['3']=='x'
        platforms={x['platform']:x['count'] for x in command['activity']['top_platforms']}
        assert platforms=={'Instagram':3,'X':2}
        highlighted={x['platform'] for x in command['activity']['recent_captured']}
        assert highlighted <= {'Instagram','X'}
        radar=compile_inbox_findings(inbox['findings'])
        assert all(x['platform'] in ('Instagram','X')
                   for f in radar for x in f['posts'])
    finally:db.close();e.dispose()

def test_irrelevant_latest_revision_removes_source_from_both_modules():
    e,db,p=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=31,result_id=1,
            assessment_version=2,relevance_label='IRRELEVANT'))
        db.commit()
        inbox,command=view(db,p)
        assert {x['id'] for x in inbox['findings']}=={'3'}
        assert command['indicators']['relevant_mentions']==1
        assert command['coverage']['relevant_distinct_posts']==1
        assert module_acceptance_evidence(db)['counts']['eligible_saved_inbox_links']==1
        assert all(x['result_id']!='1' for x in command['alerts'])
    finally:db.close();e.dispose()
