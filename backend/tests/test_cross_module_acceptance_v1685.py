"""v168.5 cross-module readiness is read-only, authenticated and non-certifying."""
import json
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session,sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db import Base,get_db
from app.models import (User,AccessGrant,MonitoringCampaign,SocialListeningResult,
    CampaignEvidence,EvidenceAssessment,AIAssessmentJob)
from app.access import default_permissions
from app.auth import create_session
from app.module_acceptance_evidence import module_acceptance_evidence,MODULE_COUNTS_SQL

def fixture():
    e=create_engine('sqlite:///:memory:',connect_args={'check_same_thread':False},poolclass=StaticPool)
    Base.metadata.create_all(e)
    factory=sessionmaker(bind=e,expire_on_commit=False)
    with factory() as db:
        for uid,role in [(1,'National Administrator'),(2,'Viewer'),(3,'Provincial Administrator')]:
            db.add(User(id=uid,email=f'cross-{uid}@example.invalid',full_name=f'Test {uid}',password_hash='unused'))
            db.add(AccessGrant(user_id=uid,access_role=role,
                geographic_scope='Nationwide' if uid!=3 else 'Province',status='Active',
                permissions_json=json.dumps(default_permissions(role))))
        db.add(MonitoringCampaign(id=41,name='Synthetic UAT',created_by='1',
            primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
        for rid,label in ((1,'RELEVANT'),(2,'UNASSESSED')):
            db.add(SocialListeningResult(id=rid,run_id=1,platform='instagram',
                text_content=f'Synthetic source {rid}',canonical_url='https://example.invalid/'+str(rid)))
            db.add(CampaignEvidence(campaign_id=41,result_id=rid,match_method='KEYWORD'))
            db.add(EvidenceAssessment(campaign_id=41,result_id=rid,relevance_label=label,assessment_version=1))
            db.add(AIAssessmentJob(campaign_id=41,result_id=rid,state='COMPLETED' if rid==1 else 'PENDING',attempts=0))
        db.commit()
        tokens={uid:{"Authorization":"Bearer "+create_session(db,db.get(User,uid))} for uid in (1,2,3)}
    def override():
        with factory() as db:yield db
    app.dependency_overrides[get_db]=override
    return e,factory,tokens

def test_eight_modules_use_observed_data_without_inferred_completion():
    engine,factory,tokens=fixture()
    try:
        with factory() as db:
            result=module_acceptance_evidence(db)
            assert result['module_count']==8
            assert result['counts']['collected_posts']==2
            assert result['counts']['ordinary_campaign_links']==2
            assert result['counts']['monitoring_links_without_valid_latest_relevance']==1
            assert result['counts']['pending_ai_jobs']==1
            assert result['counts']['completed_ai_jobs']==1
            assert not result['completion_percentages_supported']
            assert all(x['acceptance_state']=='REQUIRES_INDEPENDENT_UAT' for x in result['modules'])
            assert 'UNCLASSIFIED_MONITORING_LINKS' in result['modules'][-1]['attention_codes']
            assert 'https://example.invalid/1' not in str(result)
            assert db.query(AIAssessmentJob).count()==2
    finally:app.dependency_overrides.pop(get_db,None);engine.dispose()

def test_authenticated_http_administrator_only():
    engine,factory,tokens=fixture()
    try:
        client=TestClient(app)
        url='/api/integration/module-acceptance'
        assert client.get(url).status_code==401
        assert client.get(url,headers=tokens[2]).status_code==403
        assert client.get(url,headers=tokens[3]).status_code==403
        response=client.get(url,headers=tokens[1])
        assert response.status_code==200,response.text
        body=response.json()
        assert body['counts']['collected_posts']==2
        assert body['provider_requests']==body['database_writes']==0
        assert body['release_readiness_certified'] is False
    finally:app.dependency_overrides.pop(get_db,None);engine.dispose()

def test_only_aggregates_and_no_private_columns_in_sql():
    code=MODULE_COUNTS_SQL.upper()
    assert 'COUNT(' in code and 'SELECT *' not in code
    for forbidden in ('INSERT ','UPDATE ','DELETE ','DROP ','TRUNCATE ','SOURCE_EXCERPT','PASSWORD_HASH'):
        assert forbidden not in code

def test_empty_sources_not_falsely_treated_as_accepted():
    engine,factory,tokens=fixture()
    try:
        with factory() as db:
            db.query(AIAssessmentJob).delete();db.query(EvidenceAssessment).delete()
            db.query(CampaignEvidence).delete();db.query(SocialListeningResult).delete();db.commit()
            result=module_acceptance_evidence(db)
            assert result['counts']['collected_posts']==0
            assert result['modules'][0]['data_presence']=='NOT_OBSERVED'
            assert not result['release_readiness_certified']
    finally:app.dependency_overrides.pop(get_db,None);engine.dispose()

def test_release_gaps_do_not_claim_cross_module_e2e_observed():
    engine,factory,tokens=fixture()
    try:
        with factory() as db:
            result=module_acceptance_evidence(db)
            assert len(result['validation_gaps'])==6
            assert not result['automatically_verified_cross_module_e2e']
            assert not any(x['automatically_verified'] for x in result['validation_gaps'])
            assert result['counts']['closed_officer_cases']==0
    finally:app.dependency_overrides.pop(get_db,None);engine.dispose()
