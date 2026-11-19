"""v173.1: shared read-only bulk location statuses and query regression."""
from sqlalchemy import event as sa_event
from app.jurisdiction_review import (
    jurisdiction_status, jurisdiction_statuses_for_posts, jurisdiction_action)
from app.models import (
    SocialListeningResult,CampaignEvidence,EvidenceAssessment,
    MonitoringCampaign,CampaignJurisdictionReview)
from app.campaigns import campaign_action
from app.saved_assessment_views import saved_classifications_for_posts
from test_regency_officer_review_v1723 import fixture,ready,preview,submit,user

def test_batch_agrees_with_single_for_unreviewed_confirmed_rejected_and_stale():
    db=fixture()
    try:
        ready(db)
        source=db.get(SocialListeningResult,1)
        pair=(91,1,source)
        def equal():
            assert jurisdiction_statuses_for_posts(db,[pair])[(91,1)]==(
                jurisdiction_status(db,91,1,source))
        equal()
        submit(db,preview(db))
        equal()
        submit(db,preview(db),'REJECTED')
        equal()
        submit(db,preview(db))
        source.text_content='Kasus terjadi di Kota Surabaya.'
        db.commit()
        equal()
    finally:db.close()

def test_batch_status_preserves_campaign_isolation_and_conflicts():
    db=fixture()
    try:
        ready(db)
        source=db.get(SocialListeningResult,1)
        submit(db,preview(db))
        db.add(MonitoringCampaign(id=92,name='Other',province='Jawa Barat',
            created_by='11',primary_keywords_json='[]',
            secondary_keywords_json='[]',excluded_keywords_json='[]'))
        db.add(CampaignEvidence(campaign_id=92,result_id=1))
        db.add(EvidenceAssessment(campaign_id=92,result_id=1,
            assessment_version=1,relevance_label='RELEVANT'))
        db.commit()
        values=jurisdiction_statuses_for_posts(db,[(91,1,source),(92,1,source)])
        assert values[(91,1)]['regency_city_review']['incident_regency_city_verified']
        assert not values[(92,1)]['regency_city_review']['incident_regency_city_verified']
        assert values[(92,1)]['regency_city_review']['decision']=='UNREVIEWED'
        from app.jurisdiction_review import fingerprint
        db.add(CampaignJurisdictionReview(campaign_id=91,result_id=1,
            province='Bali',evidence_fingerprint=fingerprint(source.text_content),
            decision='CONFIRMED',rationale='Old contradictory review'))
        db.commit()
        values=jurisdiction_statuses_for_posts(db,[(91,1,source),(92,1,source)])
        assert values[(91,1)]['regency_city_review']['decision']=='PROVINCE_REVIEW_CONFLICT'
        assert not values[(91,1)]['regency_city_review']['incident_regency_city_verified']
        assert not values[(92,1)]['incident_jurisdiction_verified']
    finally:db.close()

def test_batch_query_count_is_bounded_for_40_source_records():
    db=fixture()
    try:
        ready(db)
        from app.jurisdiction_review import fingerprint
        for i in range(2,41):
            db.add(SocialListeningResult(id=i,run_id=1,platform='X',
                text_content='Kasus pemilu di Kota Bandung.'))
            db.add(CampaignEvidence(campaign_id=91,result_id=i))
        db.commit()
        posts=db.query(SocialListeningResult).all()
        sql=[]
        engine=db.get_bind()
        def trace(conn,cursor,statement,parameters,context,executemany):
            if statement.lstrip().upper().startswith('SELECT'):
                sql.append(statement)
        sa_event.listen(engine,'before_cursor_execute',trace)
        try:
            statuses=jurisdiction_statuses_for_posts(
                db,[(91,post.id,post) for post in posts])
        finally:
            sa_event.remove(engine,'before_cursor_execute',trace)
        assert len(statuses)==40
        assert len(sql)<=3, f'Unexpected N+1 queries: {len(sql)}'
    finally:db.close()

def test_inbox_and_social_saved_views_share_officer_city_status():
    db=fixture()
    try:
        ready(db)
        submit(db,preview(db))
        post=db.get(SocialListeningResult,1)
        saved=saved_classifications_for_posts(db,user(),[post])[1][0]
        inbox=campaign_action(db,user(),'campaignIntelligenceInbox',{'campaign_id':'91'})
        info=inbox['findings'][0]
        assert saved['incident_jurisdiction_review']==info['incident_jurisdiction_review']
        assert saved['incident_jurisdiction_review']['regency_city_review'][
            'incident_regency_city_verified']
    finally:db.close()

def test_rejected_city_remains_reviewed_not_an_open_queue_lead():
    db=fixture()
    try:
        ready(db)
        submit(db,preview(db),'REJECTED')
        report=jurisdiction_action(db,user(),'campaignJurisdictionReadiness',{},'91')
        assert report['counts']['city_rejected']==1
        assert report['officer_review_leads']==[]
    finally:db.close()
