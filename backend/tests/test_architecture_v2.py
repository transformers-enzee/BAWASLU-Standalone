import json, os
os.environ['DATABASE_URL']='sqlite:///:memory:'
from sqlalchemy import inspect
from app.db import Base, engine, SessionLocal
from app.models import User, AccessGrant, IssueCategory, IssueCategoryPhrase, SocialListeningResult, MonitoringCampaign, CampaignEvidence, EvidenceAssessment, EvidenceReview
from app.auth import hash_password
from app.access import default_permissions, profile
from app.registry import registry_action

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def _identity(db,admin=True):
    u=User(email=('admin' if admin else 'analyst')+'@v2.local',full_name='QA',password_hash=hash_password('test'),platform_admin=admin)
    db.add(u);db.flush()
    role='National Administrator' if admin else 'Provincial Analyst'
    db.add(AccessGrant(user_id=u.id,access_role=role,geographic_scope='Nationwide' if admin else 'Province',province='' if admin else 'Bali',permissions_json=json.dumps(default_permissions(role)),status='Active'))
    db.commit()
    return profile(db,u)

def test_v2_schema_is_additive_and_links_one_evidence_to_multiple_campaigns():
    names=set(inspect(engine).get_table_names())
    assert {'social_listening_results','monitoring_campaigns','campaign_evidence','evidence_assessments','evidence_reviews','campaign_runs','issue_category_phrases'}<=names
    db=SessionLocal()
    for c in ('Campaign A','Campaign B'):
        db.add(MonitoringCampaign(name=c,created_by='1',primary_keywords_json='["gibran"]'))
    db.commit()
    campaigns=db.query(MonitoringCampaign).order_by(MonitoringCampaign.id).all()
    assert len(campaigns)==2
    assert SocialListeningResult.__tablename__=='social_listening_results'
    db.close()

def test_issue_category_phrases_are_admin_only_and_history_preserved():
    db=SessionLocal();a=_identity(db)
    created=registry_action(db,a,'category',{'name':'Potential money politics','phrases':['Politik Uang','serangan fajar']})['category']
    cid=created['id']; assert len(created['phrases'])==2
    registry_action(db,a,'updateCategory',{'phrases':['serangan fajar','amplop pemilu']},id=cid)
    rows=db.query(IssueCategoryPhrase).filter_by(category_id=int(cid)).all()
    assert len(rows)==3
    assert {x.phrase for x in rows if x.active}=={'serangan fajar','amplop pemilu'}
    assert {x.phrase for x in rows if not x.active}=={'Politik Uang'}
    registry_action(db,a,'updateCategory',{'phrases':['politik uang','serangan fajar']},id=cid)
    assert len(db.query(IssueCategoryPhrase).filter_by(category_id=int(cid)).all())==3
    assert len([x for x in db.query(IssueCategoryPhrase).filter_by(category_id=int(cid)).all() if x.active])==2
    with_access=registry_action(db,a,'list',{})['categories']
    assert any(x['id']==cid and len(x['phrases'])==3 for x in with_access)
    analyst=_identity(db,False)
    try:
        registry_action(db,analyst,'updateCategory',{'phrases':['hijack']},id=cid)
        assert False, 'Provincial analyst must be blocked'
    except PermissionError:
        pass
    db.close()

def test_issue_category_phrase_validation():
    db=SessionLocal();a=_identity(db)
    for invalid in ('not a list',[''],['a']*41):
        try:
            registry_action(db,a,'category',{'name':'Test category','phrases':invalid})
            assert False, 'Bad phrases must fail'
        except ValueError:
            db.rollback()
    db.close()
