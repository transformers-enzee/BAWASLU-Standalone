"""V10 topic categories are saved subject classifications, never campaign keywords."""
import json
import os
os.environ['DATABASE_URL']='sqlite:///:memory:'
from app.db import Base,engine,SessionLocal
from app.models import User,AccessGrant,SocialListeningRun,SocialListeningResult,CampaignEvidence,EvidenceAssessment
from app.auth import hash_password
from app.access import default_permissions,profile
from app.socialcrawl import social_listening_action
from app.topic_themes import category_for_assessment,latest_saved_categories,UNCATEGORIZED
from app.classification_enrichment import normalize_topics

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def test_categories_follow_approved_html_subjects_not_keywords():
    for category in ['Public Information','Voter Registration','Electoral Operations','Campaign Rules','Public Concern','BAWASLU Reputation']:
        assert category_for_assessment('RELEVANT',json.dumps([category]),'[]')==category
    assert category_for_assessment('RELEVANT','[]','[]')==UNCATEGORIZED
    assert category_for_assessment('IRRELEVANT','["Electoral Operations"]','[]')==UNCATEGORIZED
    assert category_for_assessment('RELEVANT','["bawaslu"]','[]')==UNCATEGORIZED
    assert category_for_assessment('RELEVANT','[]','[{"evidence_quote":"Recorded complaint quote"}]')=='Public Concern'
    assert normalize_topics(['Voter Registration','Campaign Rules'],'DPT dan aturan kampanye pemilu','RELEVANT')==['Campaign Rules','Voter Registration']

def test_dashboard_topic_chart_uses_latest_assessments_and_preserves_unclassified():
    db=SessionLocal()
    user=User(email='topic-qa@bawaslu.local',full_name='Topic QA',password_hash=hash_password('test'))
    db.add(user);db.flush()
    db.add(AccessGrant(user_id=user.id,access_role='National Administrator',geographic_scope='Nationwide',
                       permissions_json=json.dumps(default_permissions('National Administrator')),status='Active'))
    db.commit()
    p=profile(db,user)
    campaign=social_listening_action(db,p,'createCampaign',{'name':'Theme monitoring','primary_keywords':['bawaslu'],'platforms':['tiktok']})['campaign']
    run=SocialListeningRun(query_json='{}',credits_used=0)
    db.add(run);db.flush()
    ids=[]
    for i in range(3):
        row=SocialListeningResult(run_id=run.id,platform='tiktok',text_content='bawaslu test sample '+str(i),
                                  author_name='QA',published_at='2026-10-28')
        db.add(row);db.flush();ids.append(row.id)
        db.add(CampaignEvidence(campaign_id=int(campaign['id']),result_id=row.id,matched_fields_json='{"main_keywords":["bawaslu"]}'))
    db.add(EvidenceAssessment(campaign_id=int(campaign['id']),result_id=ids[0],assessment_version=1,
                 relevance_label='RELEVANT',topic_labels_json='["Electoral Operations"]',sentiment='NEGATIVE'))
    db.add(EvidenceAssessment(campaign_id=int(campaign['id']),result_id=ids[1],assessment_version=1,
                 relevance_label='RELEVANT',topic_labels_json='["Public Information"]',sentiment='POSITIVE'))
    db.commit()
    saved=latest_saved_categories(db,int(campaign['id']))
    assert saved[ids[0]]=='Electoral Operations'
    assert saved[ids[1]]=='Public Information'
    dashboard=social_listening_action(db,p,'campaignDashboard',{},campaign['id'])
    themes=dashboard['topics_and_themes']
    assert themes['total_mentions']==3
    assert themes['categorized_mentions']==2
    assert themes['uncategorized_mentions']==1
    counts={row['name']:row['count'] for row in themes['categories']}
    assert counts=={'Electoral Operations':1,'Public Information':1,'Not categorized':1}
    assert 'bawaslu' not in counts
    chart={row['name']:row for row in themes['categories']}
    assert chart['Electoral Operations']['sentiment']['Negative']==1
    assert chart['Public Information']['sentiment']['Positive']==1
    db.close()
