"""Command Centre saved Inbox source-of-truth: sentiment, geography, Watchlist."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import WatchlistItem
from app.registry import registry_action
from app.inbox_radar import compile_inbox_findings
from app.access import default_permissions

def item(id,**kw):
    row={'id':str(id),'campaign_id':'1','relevance_label':'RELEVANT',
         'text_content':'Information about election operations',
         'canonical_url':'https://example.org/post/'+str(id),'author_name':'Source '+str(id),
         'sentiment':'UNCLASSIFIED','location_signals':[],
         'incident_jurisdiction_review':{'decision':'UNREVIEWED','incident_jurisdiction_verified':False},
         'topic_labels':[],'candidate_signals':[],'public_concern_signals':[],
         'is_flagged':False}
    row.update(kw)
    return row

def test_sentiment_coverage_uses_saved_labels_not_made_up_neutral():
    findings=compile_inbox_findings([
        item(1,sentiment='POSITIVE'),item(2,sentiment='NEUTRAL'),
        item(3,sentiment='NEGATIVE'),item(4),item(5,relevance_label='IRRELEVANT')])
    counts={}
    for finding in findings:
        for label,n in finding['sentiment_counts'].items():
            counts[label]=counts.get(label,0)+n
    assert counts=={'POSITIVE':1,'NEUTRAL':1,'NEGATIVE':1,'UNCLASSIFIED':1}
    assert sum(f['supporting_posts'] for f in findings)==4

def test_saved_geographic_reference_is_not_a_verified_incident():
    findings=compile_inbox_findings([
        item(1,location_signals=[{'name':'Aceh','province':'Aceh'}]),
        item(2,location_signals=[{'name':'Aceh','province':'Aceh'}],
             incident_jurisdiction_review={'decision':'REJECTED','incident_jurisdiction_verified':False}),
        item(3,location_signals=[{'name':'Aceh','province':'Aceh'}],
             incident_jurisdiction_review={'decision':'CONFIRMED','incident_jurisdiction_verified':True,
                                            'incident_province':'Aceh'})])
    assert sum(x['geo_signal_counts'].get('Aceh',0) for x in findings)==3
    assert sum(x['verified_incident_counts'].get('Aceh',0) for x in findings)==1
    assert sum(len(x['posts']) for x in findings)==3
    assert all(x['geography']=='Incident geography not inferred' for x in findings)

def test_unreviewed_geography_never_becomes_verified_by_location_name():
    finding=compile_inbox_findings([item(1,location_signals=[{'province':'Jawa Barat'}])])[0]
    assert finding['geo_signal_counts']=={'Jawa Barat':1}
    assert finding['verified_incident_counts']=={}
    assert finding['posts'][0]['verified_incident_province']==''

def test_authorized_watchlist_profile_summary_is_registered_only():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    try:
        db.add_all([
            WatchlistItem(id=1,name='Candidate A',type='Candidate',
                         priority='Critical',status='Under Review',province='Jawa Barat'),
            WatchlistItem(id=2,name='Candidate B',type='Candidate',
                         priority='High',status='Active',province=''),
            WatchlistItem(id=3,name='Institution X',type='Institution',
                         priority='High',status='Active'),
        ])
        db.commit()
        principal={'id':'11','status':'Active','role':'National Administrator',
                   'geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}
        result=registry_action(db,principal,'watchlistSummary',{})
        assert len(result['items'])==2
        assert [x['name'] for x in result['items']]==['Candidate A','Candidate B']
        assert result['items'][0]['priority']=='Critical'
        assert 'source_posts' not in result and result['paid_provider_called'] is False
        regional={**principal,'geographic_scope':'Province','province':'Jawa Barat'}
        restricted=registry_action(db,regional,'watchlistSummary',{})
        assert [x['name'] for x in restricted['items']]==['Candidate A']
    finally:
        db.close()
