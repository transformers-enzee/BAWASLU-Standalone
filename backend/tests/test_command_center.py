"""Executive Command Center: scope, data integrity and no fabricated results."""
import json
import os
from datetime import datetime, timedelta
import pytest
os.environ['DATABASE_URL']='sqlite:///:memory:'
from app.db import Base, engine, SessionLocal
from app.models import (User, AccessGrant, MonitoringCampaign, CampaignEvidence,
    SocialListeningRun, SocialListeningResult, EvidenceAssessment, EvidenceReview,
    IssueCategory, SocialListeningProviderUsage, IntelligenceItem)
from app.access import profile, default_permissions
from app.command_center import build_command_center, _period
from app.auth import hash_password

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def _actor(db, email, role, scope, province=''):
    person=User(email=email,full_name=email,password_hash=hash_password('test-value'))
    db.add(person);db.flush()
    db.add(AccessGrant(user_id=person.id,access_role=role,
        geographic_scope=scope,province=province,status='Active',
        permissions_json=json.dumps(default_permissions(role))))
    db.commit()
    return profile(db,person)

def _evidence(db,province,content,with_signal=False,post_id=''):
    today=datetime.utcnow().date().isoformat()
    campaign=MonitoringCampaign(name='Monitoring '+province,province=province,
        primary_keywords_json='["pemilu"]',platforms_json='["instagram"]',
        status='DRAFT',created_by='test')
    run=SocialListeningRun(query_json=json.dumps({'province':province}),
        executed_by='test',status='COMPLETED')
    db.add_all([campaign,run]);db.flush()
    result=SocialListeningResult(run_id=run.id,provider='TEST',
        provider_result_id=post_id,platform='instagram',
        canonical_url='https://www.instagram.com/p/'+post_id,
        author_name='Public Example',published_at=today+'T09:15:00',
        text_content=content,observed_handle='@public_example')
    db.add(result);db.flush()
    db.add(CampaignEvidence(campaign_id=campaign.id,result_id=result.id))
    signal=[{'category_id':1,'signal_type':'POTENTIAL_VIOLATION',
             'evidence_quote':content[:45],
             'explanation':'Preliminary allegation; independent verification needed'}] if with_signal else []
    assessment=EvidenceAssessment(campaign_id=campaign.id,result_id=result.id,
        assessment_version=1,relevance_label='RELEVANT',
        explanation='AI-assessed relevant post',potential_issue_signals_json=json.dumps(signal))
    db.add(assessment);db.commit()
    return campaign,result,assessment

def test_empty_dashboard_is_clear_and_zero_cost():
    db=SessionLocal()
    p=_actor(db,'national@test.local','National Administrator','Nationwide')
    out=build_command_center(db,p)
    assert out['indicators']['relevant_mentions']==0
    assert out['indicators']['emerging_issues'] is None
    assert out['alerts']==[] and out['briefing']['kind']=='DATA_COVERAGE_NOTICE'
    assert out['paid_provider_called'] is False
    assert db.query(SocialListeningProviderUsage).count()==0
    db.close()

def test_region_restriction_applies_to_counts_alerts_and_filters():
    db=SessionLocal()
    national=_actor(db,'national@test.local','National Administrator','Nationwide')
    west=_actor(db,'prov@test.local','Provincial Analyst','Province','Jawa Barat')
    db.add(IssueCategory(id=1,name='Potensi Politik Uang',active=True));db.commit()
    _evidence(db,'Jawa Barat','Allegation of election vote buying in local campaign, unverified.',True,'west01')
    _evidence(db,'Jawa Tengah','Allegation of election vote buying in local campaign, unverified.',True,'central02')
    both=build_command_center(db,national)
    scoped=build_command_center(db,west)
    assert both['indicators']['relevant_mentions']==2
    assert both['indicators']['potential_alerts']==2
    assert scoped['indicators']['relevant_mentions']==1
    assert scoped['indicators']['potential_alerts']==1
    assert scoped['alerts'][0]['province']=='Jawa Barat'
    with pytest.raises(PermissionError):
        build_command_center(db,west,{'province':'Jawa Tengah'})
    assert db.query(SocialListeningProviderUsage).count()==0
    db.close()

def test_latest_assessment_version_is_counted_once_and_dismissed_alert_omitted():
    db=SessionLocal()
    p=_actor(db,'national@test.local','National Administrator','Nationwide')
    db.add(IssueCategory(id=1,name='Potensi Politik Uang',active=True));db.commit()
    c,post,first=_evidence(db,'Jawa Barat',
        'Allegation of election vote buying in local campaign, unverified.',True,'west02')
    updated=EvidenceAssessment(campaign_id=c.id,result_id=post.id,
        assessment_version=2,relevance_label='RELEVANT',
        potential_issue_signals_json=first.potential_issue_signals_json)
    db.add(updated);db.flush()
    db.add(EvidenceReview(assessment_id=updated.id,reviewer_id=p['id'],
        decision='FLAG_DISMISSED',rationale='Requires no additional action'))
    db.commit()
    result=build_command_center(db,p)
    assert result['indicators']['relevant_mentions']==1
    assert result['indicators']['potential_alerts']==0
    assert result['alerts']==[]
    db.close()

def test_date_window_validation_and_unknown_province_rejected():
    db=SessionLocal()
    p=_actor(db,'national@test.local','National Administrator','Nationwide')
    with pytest.raises(ValueError): build_command_center(db,p,{'province':'Imaginary Province'})
    with pytest.raises(ValueError): build_command_center(db,p,{'period':'custom','date_from':'2026-01-05','date_to':'2025-12-05'})
    with pytest.raises(ValueError): build_command_center(db,p,{'period':'custom','date_from':'bad','date_to':'2026-01-01'})
    assert _period({'period':'7d'})[2]=='7d'
    db.close()

def test_manual_inbox_records_are_included_without_inflating_social_metrics():
    db=SessionLocal()
    regional=_actor(db,'regional@test.local','Provincial Analyst','Province','Jawa Barat')
    today=datetime.utcnow().date().isoformat()
    db.add(IntelligenceItem(intelligence_id='INTEL-CC-1',
        title='Manually recorded observation',publication_date=today,
        province='Jawa Barat',source_url='https://example.org/source'))
    db.add(IntelligenceItem(intelligence_id='INTEL-CC-2',
        title='Other province observation',publication_date=today,
        province='Jawa Tengah',source_url='https://example.org/other'))
    db.commit()
    dashboard=build_command_center(db,regional)
    assert dashboard['indicators']['relevant_mentions']==0
    assert len(dashboard['latest_intelligence'])==1
    assert dashboard['latest_intelligence'][0]['record_type']=='INTELLIGENCE_ITEM'
    assert dashboard['latest_intelligence'][0]['campaign_name']=='INTEL-CC-1'
    db.close()
