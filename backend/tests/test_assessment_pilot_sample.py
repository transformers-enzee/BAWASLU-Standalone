"""No-paid-provider pilot selection QA."""
from types import SimpleNamespace
from app.assessment_pilot import choose_platform_sample

def test_sample_spreads_across_platforms_and_is_stable():
    rows=[SimpleNamespace(platform='instagram',result_id=i) for i in range(1,21)]
    rows += [SimpleNamespace(platform='x',result_id=i) for i in range(21,25)]
    rows += [SimpleNamespace(platform='youtube',result_id=25)]
    expected=[1,21,25,2,22,3,23,4,24,5]
    assert [r.result_id for r in choose_platform_sample(rows,10)]==expected
    assert [r.result_id for r in choose_platform_sample(rows,10)]==expected

def test_no_overrun_or_empty_sample():
    assert choose_platform_sample([],50)==[]
    only=[SimpleNamespace(platform=None,result_id=11)]
    assert choose_platform_sample(only,40)==only

def test_pilot_never_includes_registered_account_only_posts():
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session
    from app.db import Base
    from app.models import MonitoringCampaign,CampaignEvidence,SocialListeningResult,SocialListeningRun
    from app.assessment_pilot import assessment_pilot_preview
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        campaign=MonitoringCampaign(name='QA Test campaign',status='DRAFT',
            primary_keywords_json='["gibran"]',platforms_json='["instagram"]')
        run=SocialListeningRun(provider='SOCIALCRAWL',status='COMPLETED')
        db.add_all([campaign,run]);db.flush()
        collected=[]
        for i,method in enumerate(['KEYWORD','WATCHLIST_ACCOUNT']):
            post=SocialListeningResult(run_id=run.id,platform='instagram',
                provider_result_id='pilot-'+str(i),
                canonical_url=f'https://www.instagram.com/p/test{i}/',
                text_content='Gibran official account' if i else 'News mentioning Gibran',
                author_name='candidate' if i else 'news',published_at='2026-10-31T10:00:00Z')
            db.add(post);db.flush()
            db.add(CampaignEvidence(campaign_id=campaign.id,result_id=post.id,match_method=method))
            collected.append(post.id)
        db.commit()
        principal={'id':'1','status':'Active','geographic_scope':'Nationwide',
            'permissions':{'view_intelligence':True}}
        result=assessment_pilot_preview(db,principal,{'sample_size':10},str(campaign.id))
        assert result['total']==1
        assert [row['id'] for row in result['records']]==[str(collected[0])]
        assert result['paid_provider_called'] is False
