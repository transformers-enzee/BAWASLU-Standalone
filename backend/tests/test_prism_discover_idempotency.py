"""No-cost, database-backed regression for SocialCrawl Discover duplicate posts.

This test deliberately uses the application's autoflush=False session and a
fake provider response: no live Supabase, SocialCrawl or OpenAI requests.
"""
import json
import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
from app.db import Base, engine, SessionLocal
from app.models import (
    MonitoringCampaign, SocialListeningRun, SocialListeningResult,
    CampaignRun, CampaignEvidence, EvidenceAssessment,
)
from app import prism_discover


def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def seed(db):
    campaign = MonitoringCampaign(
        name='Discover local QA', description='Gibran election monitoring',
        primary_keywords_json='["Gibran"]',
        platforms_json='["instagram","tiktok"]',
        created_by='qa-admin', status='DRAFT',
    )
    db.add(campaign)
    db.flush()
    run = SocialListeningRun(
        provider='SOCIALCRAWL_PRISM', status='QUEUED',
        query_json=json.dumps({
            'campaign_id': campaign.id,
            'body': {'groups': [{'keywords': ['Gibran']}]},
        }),
        executed_by='qa-admin',
    )
    db.add(run)
    db.flush()
    db.add(CampaignRun(
        campaign_id=campaign.id, social_listening_run_id=run.id,
        triggered_by='PRISM_DISCOVER',
    ))
    db.commit()
    return campaign, run


def post(source_id, url, stance='negative', platform='instagram'):
    return {
        'id': source_id, 'platform': platform, 'url': url,
        'text': 'Warga membahas Gibran dan pengawasan Pilkada Jawa Barat.',
        'published_at': '2026-10-29T12:00:00Z',
        'author': {'username': 'public_news'},
        'judgments': {
            'stance': {'label': stance, 'confidence': 0.91},
            'relevance': {'p': 0.94},
        },
        'matched_keywords': ['Gibran'],
    }


def test_duplicate_id_and_url_in_single_provider_batch(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    first = post('post-1', 'https://instagram.com/p/source-1')
    duplicate_id = post('post-1', 'https://instagram.com/p/source-1')
    alternate_id_same_url = post('post-2', 'https://instagram.com/p/source-1')
    second = post('post-3', 'https://instagram.com/p/source-3', 'positive')
    saved = prism_discover.store(
        db, run, campaign,
        [first, duplicate_id, alternate_id_same_url, second],
    )
    assert saved == 2
    assert db.query(SocialListeningResult).count() == 2
    assert db.query(CampaignEvidence).count() == 2
    assessments = db.query(EvidenceAssessment).order_by(
        EvidenceAssessment.result_id).all()
    assert len(assessments) == 2
    assert {x.sentiment for x in assessments} == {'NEGATIVE', 'POSITIVE'}
    assert all(x.sentiment_model == 'socialcrawl-prism-stance' for x in assessments)
    assert all(x.relevance_label == 'RELEVANT' for x in assessments)
    db.close()


def test_repeated_run_reuses_existing_assessments_and_links(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    items = [
        post('post-1', 'https://instagram.com/p/source-1'),
        post('post-2', 'https://instagram.com/p/source-2'),
    ]
    assert prism_discover.store(db, run, campaign, items) == 2
    initial = {
        x.result_id: x.id for x in db.query(EvidenceAssessment).all()
    }
    assert prism_discover.store(
        db, run, campaign,
        items + [post('post-new-provider-id', 'https://instagram.com/p/source-1')],
    ) == 2
    assert db.query(SocialListeningResult).count() == 2
    assert db.query(CampaignEvidence).count() == 2
    assert {x.result_id: x.id for x in db.query(EvidenceAssessment).all()} == initial
    db.close()


def test_existing_human_assessment_is_not_overwritten(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    item = SocialListeningResult(
        run_id=run.id, provider='SOCIALCRAWL', provider_result_id='manual-1',
        platform='instagram', canonical_url='https://instagram.com/p/manual',
        text_content='Gibran public news',
    )
    db.add(item)
    db.flush()
    human = EvidenceAssessment(
        campaign_id=campaign.id, result_id=item.id,
        assessment_version=1, model_version='HUMAN',
        relevance_label='RELEVANT', sentiment='NEUTRAL',
    )
    db.add(human)
    db.commit()
    assert prism_discover.store(
        db, run, campaign,
        [post('discover-99', 'https://instagram.com/p/manual')],
    ) == 1
    assert db.query(CampaignEvidence).count() == 1
    assert db.query(SocialListeningResult).count() == 1
    rows = db.query(EvidenceAssessment).all()
    assert len(rows) == 1
    assert rows[0].id == human.id
    assert rows[0].model_version == 'HUMAN'
    assert rows[0].sentiment == 'NEUTRAL'
    db.close()


def test_execute_full_mock_provider_flow_completes_without_spending(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db = SessionLocal()
    campaign, run = seed(db)
    provider_calls = []

    def fake_provider(method, url, body=None, timeout=50):
        provider_calls.append((method, url))
        return {
            'run': {'run_id': 'mock-provider', 'status': 'completed',
                    'credits': {'spent': 0}},
            'items': [
                post('same', 'https://instagram.com/p/same'),
                post('same', 'https://instagram.com/p/same'),
            ],
            'next': {},
        }, {'request_id': 'offline-mock', 'success': True}

    monkeypatch.setattr(prism_discover, 'call', fake_provider)
    prism_discover.execute(run.id)
    db.expire_all()
    saved_run = db.get(SocialListeningRun, run.id)
    assert saved_run.status == 'COMPLETED', saved_run.error_text
    assert saved_run.result_count == 1
    assert saved_run.credits_used == 0
    assert len(provider_calls) == 1
    assert db.query(CampaignEvidence).count() == 1
    assert db.query(EvidenceAssessment).count() == 1
    db.close()

def test_activate_defaults_seven_platforms_100_posts_without_provider_calls(monkeypatch):
    from app.socialcrawl import DEFAULT_CAMPAIGN_PLATFORMS
    db=SessionLocal()
    campaign=MonitoringCampaign(name='Default seven sources',description='Election topic',
        primary_keywords_json='["gibran"]',platforms_json=json.dumps(DEFAULT_CAMPAIGN_PLATFORMS),
        created_by='qa-admin',status='DRAFT')
    db.add(campaign);db.commit()
    params,signature=prism_discover.body_for(db,campaign)
    assert params['limit']==prism_discover.CANDIDATE_CAP
    assert params['max_credits']==100
    assert params['platforms']==['tiktok','instagram','youtube','facebook','twitter','threads','news']
    assert len(signature)==64
    assert db.query(SocialListeningRun).count()==0
    db.close()

def test_store_up_to_100_unique_results_without_ai_or_paid_provider(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    db=SessionLocal();campaign,run=seed(db)
    items=[post('qa-'+str(i),'https://instagram.com/p/qa-'+str(i)) for i in range(104)]
    assert prism_discover.store(db,run,campaign,items)==100
    assert db.query(CampaignEvidence).count()==100
    assert db.query(SocialListeningResult).count()==100
    assert db.query(EvidenceAssessment).count()==100
    db.close()


def test_missing_provider_stance_is_pending_not_falsely_assessed(monkeypatch):
    from app.sentiment_processing import sentiment_is_assessed
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db=SessionLocal()
    campaign,run=seed(db)
    item=post('missing-stance','https://instagram.com/p/missing-stance')
    item['judgments']['stance']={'label':None,'confidence':0.47}
    prism_discover.store(db,run,campaign,[item],full_assessment=True)
    record=db.query(EvidenceAssessment).filter_by(campaign_id=campaign.id).one()
    assert record.relevance_label=='RELEVANT'
    assert record.sentiment=='UNCLASSIFIED'
    assert record.sentiment_model==''
    assert record.sentiment_confidence==''
    assert not sentiment_is_assessed(record)
    assert 'did not supply' in record.sentiment_explanation
    db.close()


def test_boolean_project_discover_links_only_true_matches(monkeypatch):
    """No paid calls; provider candidates are screened before evidence linking."""
    from app.project_boolean import encode_boolean_project_query
    monkeypatch.delenv('OPENAI_API_KEY', raising=False)
    db=SessionLocal()
    campaign,run=seed(db)
    campaign.primary_keywords_json=encode_boolean_project_query(
        'Gibran AND (ijazah OR pendidikan) NOT hoaks')
    db.commit()
    params,_=prism_discover.body_for(db,campaign)
    # The positive anchor broadens retrieval; only complete Boolean matches enter evidence.
    assert params['groups'][0]['keywords']==['gibran','gibran ijazah','gibran pendidikan']
    assert 'contains' not in params
    assert 'exclude_terms' not in params['groups'][0]
    assert params['max_credits']==100
    assert params['relevance']=='score'

    matched=post('boolean-true','https://instagram.com/p/boolean-true')
    matched['text']='Warga membahas ijazah Gibran.'
    wrong_topic=post('boolean-wrong','https://instagram.com/p/boolean-wrong')
    wrong_topic['text']='Gibran membahas jalan tol.'
    excluded=post('boolean-excluded','https://instagram.com/p/boolean-excluded')
    excluded['text']='Gibran membantah hoaks ijazah.'
    assert prism_discover.store(db,run,campaign,[matched,wrong_topic,excluded])==1
    links=db.query(CampaignEvidence).all()
    assert len(links)==1
    approved=db.get(SocialListeningResult,links[0].result_id)
    assert approved.provider_result_id=='boolean-true'
    assert db.query(EvidenceAssessment).count()==1
    meta=json.loads(links[0].matched_fields_json)
    assert meta['search_mode']=='BOOLEAN'
    assert meta['matched'] is True
    queued_ids=json.loads(run.query_json or '{}').get('assessment_result_ids')
    assert queued_ids==[approved.id]  # Excluded posts cannot enter the paid AI queue.
    diagnostics=json.loads(run.query_json or '{}')['collection_diagnostics']
    assert diagnostics['raw_provider_items']==3
    assert diagnostics['unique_candidates']==3
    assert diagnostics['accepted_boolean_matches']==1
    assert diagnostics['excluded_by_boolean']==2
    assert diagnostics['new_evidence_links']==1
    db.close()


def test_standard_matching_and_revision_without_paid_calls(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    db=SessionLocal();c,run=seed(db)
    c.primary_keywords_json='["Gibran","KPU"]'
    c.secondary_keywords_json='["Pilkada"]'
    c.excluded_keywords_json='["concert"]'
    snapshot=prism_discover.search_snapshot(c)
    run.query_json=json.dumps({'campaign_id':c.id,'search_snapshot':snapshot})
    c.primary_keywords_json='["Prabowo"]'
    db.commit()
    yes=post('qa-yes','https://instagram.com/p/qa-yes')
    no=post('qa-no','https://instagram.com/p/qa-no');no['text']='Gibran concert'
    unrelated=post('qa-other','https://instagram.com/p/qa-other');unrelated['text']='Prabowo speaks'
    assert prism_discover.store(db,run,c,[yes,no,unrelated],full_assessment=True)==1
    link=db.query(CampaignEvidence).one()
    fields=json.loads(link.matched_fields_json)
    assert fields['search_mode']=='KEYWORDS'
    assert fields['query_revision']==prism_discover.snapshot_signature(snapshot)
    assert db.query(EvidenceAssessment).count()==1
    diag=json.loads(run.query_json)['collection_diagnostics']
    assert diag['excluded_by_search']==2 and diag['new_evidence_links']==1
    assert prism_discover.store(db,run,c,[yes],full_assessment=True)==1
    assert json.loads(run.query_json)['collection_diagnostics']['already_linked_matches']==1
    db.close()


def test_all_standard_keywords_dates_and_credit_ledger():
    import pytest
    from datetime import datetime
    from app.campaign_scheduler import used_credits_24h
    from app.models import SocialListeningProviderUsage
    db=SessionLocal();c,run=seed(db)
    words=['topic'+str(i) for i in range(30)]
    c.primary_keywords_json=json.dumps(words)
    c.date_from='2026-10-01';c.date_to='2026-11-20'
    run.credits_used=16
    db.add(SocialListeningProviderUsage(provider='SOCIALCRAWL',credits_used=3))
    db.commit()
    body,sig=prism_discover.body_for(db,c)
    assert body['groups'][0]['keywords']==words
    assert body['since']=='2026-10-01' and body['until']=='2026-11-20'
    assert body['relevance']=='score'
    c.excluded_keywords_json='["hoaks"]'
    assert prism_discover.body_for(db,c)[1]!=sig
    assert used_credits_24h(db,datetime.utcnow())==19
    c.primary_keywords_json=json.dumps(words+['extra'])
    with pytest.raises(ValueError,match='more than 30'):
        prism_discover.body_for(db,c)
    db.close()


def test_worker_claim_prevents_duplicate_paid_submission(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    db=SessionLocal();c,run=seed(db)
    calls=[]
    def fake(method,url,body=None,timeout=50):
        calls.append(method)
        return {'run':{'run_id':'mock','status':'completed','credits':{'spent':4}},'items':[]},{}
    monkeypatch.setattr(prism_discover,'call',fake)
    prism_discover.execute(run.id)
    prism_discover.execute(run.id)
    db.expire_all()
    assert calls==['POST']
    assert db.get(SocialListeningRun,run.id).credits_used==4
    db.close()


def test_candidate_scan_can_find_matches_after_first_hundred(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    db=SessionLocal();c,run=seed(db)
    run.query_json=json.dumps({'campaign_id':c.id,'body':{'limit':300}})
    db.commit()
    noise=[post('noise-'+str(i),'https://instagram.com/p/noise-'+str(i)) for i in range(150)]
    for item in noise:item['text']='Unrelated topic'
    matches=[post('match-'+str(i),'https://instagram.com/p/match-'+str(i)) for i in range(120)]
    assert prism_discover.store(db,run,c,noise+matches,full_assessment=True)==100
    assert db.query(CampaignEvidence).count()==100
    assert db.query(EvidenceAssessment).count()==100
    diag=json.loads(run.query_json)['collection_diagnostics']
    assert diag['excluded_by_search']==150
    assert diag['matched_over_target']==20
    assert diag['candidate_limit']==300
    db.close()


def test_recovery_only_reads_original_run_without_ai(monkeypatch):
    from app import activation_assessment
    db=SessionLocal();c,run=seed(db)
    snapshot=prism_discover.search_snapshot(c)
    run.query_json=json.dumps({'campaign_id':c.id,'body':{'limit':300},'search_snapshot':snapshot,
        'query_revision':prism_discover.snapshot_signature(snapshot)})
    run.status='FAILED';run.provider_request_id='run_existing';run.credits_used=8
    db.commit()
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    calls=[]
    def fake(method,url,body=None,timeout=50):
        calls.append((method,url))
        assert method=='GET'
        return {'run':{'run_id':'run_existing','status':'completed','credits':{'spent':8}},
                'items':[post('recovered','https://instagram.com/p/recovered')]},{}
    monkeypatch.setattr(prism_discover,'call',fake)
    def no_ai(*args):raise AssertionError('Recovery must not submit AI requests')
    monkeypatch.setattr(activation_assessment,'execute_run',no_ai)
    result=prism_discover.action(db,{},'campaignDiscoverRecover',{'run_id':run.id},c.id)
    assert result['recovery_only'] and result['run_id']==run.id
    prism_discover.execute(run.id)
    db.expire_all()
    assert calls==[('GET',prism_discover.BASE+'/prism/discover/runs/run_existing')]
    assert db.get(SocialListeningRun,run.id).status=='COMPLETED'
    assert db.get(SocialListeningRun,run.id).credits_used==8
    assert db.query(CampaignEvidence).count()==1
    assert db.query(SocialListeningRun).count()==1
    db.close()


def test_stale_known_run_can_recover_without_post(monkeypatch):
    from datetime import datetime,timedelta,timezone
    from app import activation_assessment
    db=SessionLocal();c,run=seed(db)
    snapshot=prism_discover.search_snapshot(c)
    run.status='RUNNING';run.provider_request_id='run_stale'
    run.query_json=json.dumps({'campaign_id':c.id,'body':{'limit':300},'search_snapshot':snapshot,
        'query_revision':prism_discover.snapshot_signature(snapshot),'worker_token':'old-worker',
        'worker_heartbeat_at':(datetime.now(timezone.utc)-timedelta(hours=2)).isoformat()})
    db.commit()
    monkeypatch.setattr(prism_discover,'campaign',lambda db,p,cid,write=False:c)
    monkeypatch.setattr(prism_discover,'allowed',lambda p,c:True)
    assert prism_discover.latest_collection_outcome(db,c)['recovery_available']
    result=prism_discover.action(db,{},'campaignDiscoverRecover',{'run_id':run.id},c.id)
    assert result['recovery_only']
    calls=[]
    def read(method,url,body=None,timeout=50):
        calls.append(method)
        return {'run':{'run_id':'run_stale','status':'completed','credits':{'spent':4}},'items':[]},{}
    monkeypatch.setattr(prism_discover,'call',read)
    monkeypatch.setattr(activation_assessment,'execute_run',lambda *a: (_ for _ in ()).throw(AssertionError('No AI')))
    prism_discover.execute(run.id);db.expire_all()
    assert calls==['GET']
    assert db.get(SocialListeningRun,run.id).status=='COMPLETED'
    db.close()


def test_reused_provider_run_credits_not_double_counted(monkeypatch):
    from app import activation_assessment
    from app.prism_collection_budget import snapshot
    db=SessionLocal();c,first=seed(db)
    first.status='COMPLETED';first.provider_request_id='run_shared';first.credits_used=12
    first.query_json=json.dumps({'campaign_id':c.id,'provider_diagnostics':{'collected':420}})
    second=SocialListeningRun(provider='SOCIALCRAWL_PRISM',status='QUEUED',query_json=json.dumps({'campaign_id':c.id,'body':{'limit':300}}))
    db.add(second);db.flush();db.add(CampaignRun(campaign_id=c.id,social_listening_run_id=second.id));db.commit()
    monkeypatch.setattr(prism_discover,'call',lambda *a,**k:({'run':{'run_id':'run_shared','status':'completed','credits':{'spent':12}},'items':[],
        'summary':{'rows':{'collected':420}}},{}))
    monkeypatch.setattr(activation_assessment,'execute_run',lambda *a:None)
    prism_discover.execute(second.id);db.expire_all()
    assert db.get(SocialListeningRun,second.id).credits_used==0
    assert db.get(SocialListeningRun,second.id).cached
    assert snapshot(db)['monthly_counted']==420
    db.close()


def test_unknown_failed_submission_is_flagged_without_retry(monkeypatch):
    db=SessionLocal();c,run=seed(db);calls=[]
    def timeout(method,url,body=None,timeout=50):
        calls.append(method);raise RuntimeError('provider request timeout')
    monkeypatch.setattr(prism_discover,'call',timeout)
    prism_discover.execute(run.id);prism_discover.execute(run.id);db.expire_all()
    saved=db.get(SocialListeningRun,run.id)
    assert calls==['POST'] and saved.status=='FAILED'
    assert json.loads(saved.query_json)['submission_uncertain']
    db.close()


def test_legacy_collection_guard_reserves_and_counts_raw_results(monkeypatch):
    import pytest
    from app import socialcrawl
    from app.prism_collection_budget import snapshot
    db=SessionLocal()
    principal={'id':'qa','status':'Active','role':'National Administrator','geographic_scope':'Nationwide','permissions':{'view_intelligence':True}}
    calls=[]
    def fake(filters):
        calls.append(filters)
        return {'success':True,'request_id':'legacy-mock','credits_used':1,'data':{'items':[
            {'id':'a','platform':'tiktok','text':'pemilu','url':'https://example.com/a'},
            {'id':'a','platform':'tiktok','text':'pemilu','url':'https://example.com/a'}]}}
    monkeypatch.setenv('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT','1')
    with pytest.raises(ValueError,match='Monthly collection allowance'):
        socialcrawl.execute_search(db,principal,{'query':'pemilu','platforms':['tiktok'],'limit':2},provider_client=fake)
    assert not calls
    monkeypatch.setenv('BAWASLU_MONTHLY_COLLECTION_POST_LIMIT','3000000')
    monkeypatch.setenv('MEDIA_THUMBNAIL_CACHE_ENABLED','false')
    result=socialcrawl.execute_search(db,principal,{'query':'pemilu','platforms':['tiktok'],'limit':2},provider_client=fake)
    assert len(calls)==1
    assert result['diagnostics']['provider_items']==2
    assert snapshot(db)['monthly_counted']==2
    assert snapshot(db)['monthly_reserved']==0
    db.close()


def test_explicit_prism_date_window_never_accepts_outside_or_undated_candidate(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    db=SessionLocal();c,run=seed(db)
    run.query_json=json.dumps({'campaign_id':c.id,'body':{'limit':300,'since':'2026-10-01','until':'2026-10-31'}})
    db.commit()
    yes=post('date-yes','https://instagram.com/p/date-yes')
    old=post('date-old','https://instagram.com/p/date-old');old['published_at']='2026-09-30T23:59:59Z'
    unknown=post('date-unknown','https://instagram.com/p/date-unknown');unknown['published_at']=''
    assert prism_discover.store(db,run,c,[yes,old,unknown],full_assessment=True)==1
    assert db.query(CampaignEvidence).count()==1
    assert json.loads(run.query_json)['collection_diagnostics']['excluded_by_publication_date']==2
    db.close()


def test_candidate_cap_prioritizes_new_project_links(monkeypatch):
    monkeypatch.delenv('OPENAI_API_KEY',raising=False)
    db=SessionLocal();c,first=seed(db)
    first.query_json=json.dumps({'campaign_id':c.id,'body':{'limit':300}})
    db.commit()
    old=[post('old-'+str(i),'https://instagram.com/p/old-'+str(i)) for i in range(100)]
    assert prism_discover.store(db,first,c,old,full_assessment=True)==100
    run=SocialListeningRun(provider='SOCIALCRAWL_PRISM',status='QUEUED',query_json=json.dumps({'campaign_id':c.id,'body':{'limit':300}}))
    db.add(run);db.flush();db.add(CampaignRun(campaign_id=c.id,social_listening_run_id=run.id));db.commit()
    new=[post('new-'+str(i),'https://instagram.com/p/new-'+str(i)) for i in range(25)]
    assert prism_discover.store(db,run,c,old+new,full_assessment=True)==100
    assert db.query(CampaignEvidence).count()==125
    assert json.loads(run.query_json)['collection_diagnostics']['new_evidence_links']==25
    db.close()
