"""Public demo feedback endpoint must never expose private feedback to visitors."""
import os,json
os.environ['DATABASE_URL']='sqlite:///:memory:'
from fastapi.testclient import TestClient
from app.main import app
from app.db import Base,engine,SessionLocal
from app.models import User,AccessGrant,DemoFeedback
from app.access import default_permissions
from app.auth import hash_password,create_session

def setup_function():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

def headers(role='National Administrator'):
    db=SessionLocal()
    user=User(email=f'feedback-{role.replace(" ","-")}@qa.test',
              full_name='Feedback QA',password_hash=hash_password('test'))
    db.add(user);db.flush()
    db.add(AccessGrant(user_id=user.id,access_role=role,geographic_scope='Nationwide',
           permissions_json=json.dumps(default_permissions(role)),status='Active'))
    db.commit()
    token=create_session(db,user);db.close()
    return {'Authorization':'Bearer '+token}

def payload(message='The demo navigation is easy to follow.'):
    return {'category':'usability','rating':4,'message':message,
            'page_path':'/demo/inbox','language':'id','department':'Tim Pengawasan','visitor_key':'a'*32}

def test_anonymous_submit_and_admin_only_aggregate():
    client=TestClient(app)
    result=client.post('/api/demo-feedback',json=payload())
    assert result.status_code==201,result.text
    assert result.json()['ok'] is True
    assert client.get('/api/demo-feedback/admin').status_code==401
    assert client.get('/api/demo-feedback/admin',headers=headers('Viewer')).status_code==403
    national=client.get('/api/demo-feedback/admin',headers=headers())
    assert national.status_code==200,national.text
    report=national.json()
    assert report['total']==1 and report['average_rating']==4
    assert report['by_category']=={'usability':1}
    assert report['by_page']=={'/demo/inbox':1}
    assert report['by_department']=={'Tim Pengawasan':1}
    assert len(report['recent'])==1
    assert report['recent'][0]['message']==payload()['message']
    assert 'visitor_hash' not in report['recent'][0]
    db=SessionLocal()
    assert db.query(DemoFeedback).count()==1
    assert len(db.query(DemoFeedback).first().visitor_hash)==64
    db.close()

def test_public_submission_validation_and_spam_protection():
    client=TestClient(app)
    assert client.post('/api/demo-feedback',json={**payload(),'message':'','rating':None}).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'page_path':'/administration'}).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'category':'secret'}).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'website':'hidden-bot-field'}).status_code==400
    assert client.post('/api/demo-feedback',json={**payload(),'message':'','rating':5}).status_code==201
    assert client.post('/api/demo-feedback',json={**payload(),'message':'','rating':5}).status_code==409
    assert client.post('/api/demo-feedback',json={**payload(),'message':'','rating':4}).status_code==201
    assert client.post('/api/demo-feedback',json=payload('Short')).status_code==201
    assert client.post('/api/demo-feedback',json=payload('Fourth useful piece of training feedback.')).status_code==429
    # Another visitor behind the same Wi-Fi should not inherit this limit.
    second={**payload('Another visitor sharing the same training Wi-Fi.'),'visitor_key':'b'*32}
    assert client.post('/api/demo-feedback',json=second).status_code==201

def test_rating_only_feedback_visible_in_admin_aggregates():
    client=TestClient(app)
    body={'rating':5,'message':'','department':'Biro Humas','page_path':'/demo/smart-radar','visitor_key':'c'*32}
    assert client.post('/api/demo-feedback',json=body).status_code==201
    report=client.get('/api/demo-feedback/admin',headers=headers()).json()
    assert report['total']==1
    assert report['average_rating']==5
    assert report['recent'][0]['message']==''
    assert report['by_category']=={'general':1}


def test_private_feedback_cannot_be_read_by_unauthenticated_demo():
    client=TestClient(app)
    assert client.get('/api/demo-feedback/admin',headers={'Authorization':'Bearer fake'}).status_code==401
    assert client.post('/api/demo-feedback',json={**payload(),'rating':6}).status_code==422
    assert client.get('/api/demo-feedback').status_code==405

def test_feedback_delete_requires_national_administrator_and_updates_aggregates():
    client=TestClient(app)
    first=client.post('/api/demo-feedback',json={**payload(),'rating':5,'message':'First rating'});assert first.status_code==201
    second=client.post('/api/demo-feedback',json={**payload(),'rating':2,'message':'Second rating'});assert second.status_code==201
    national=headers()
    initial=client.get('/api/demo-feedback/admin',headers=national).json()
    assert initial['total']==2 and initial['average_rating']==3.5
    target=initial['recent'][0]['id']
    url=f'/api/demo-feedback/admin/{target}'
    assert client.delete(url).status_code==401
    assert client.delete(url,headers=headers('Viewer')).status_code==403
    assert client.delete(url,headers={'Authorization':'Bearer invalid'}).status_code==401
    assert client.get('/api/demo-feedback/admin',headers=national).json()['total']==2
    removed=client.delete(url,headers=national)
    assert removed.status_code==200 and removed.json()['deleted_id']==target
    summary=client.get('/api/demo-feedback/admin',headers=national).json()
    assert summary['total']==1 and summary['average_rating']==5
    assert summary['rated_count']==1
    assert len(summary['recent'])==1
    assert client.delete(url,headers=national).status_code==404
    assert client.delete('/api/demo-feedback/admin/0',headers=national).status_code==404
    db=SessionLocal();assert db.query(DemoFeedback).count()==1;db.close()

def test_required_team_or_bureau_saved_and_visible_only_to_national_admin():
    client=TestClient(app)
    assert client.post('/api/demo-feedback',json={k:v for k,v in payload().items() if k!='department'}).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'department':''}).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'department':'   '}).status_code==422
    body={**payload(),'department':'Tim Pengawasan Pemilu','rating':5}
    result=client.post('/api/demo-feedback',json=body)
    assert result.status_code==201,result.text
    assert client.get('/api/demo-feedback/admin').status_code==401
    national=client.get('/api/demo-feedback/admin',headers=headers())
    assert national.status_code==200
    report=national.json()
    assert report['by_department']=={'Tim Pengawasan Pemilu':1}
    assert report['recent'][0]['department']=='Tim Pengawasan Pemilu'
    assert not any(k in report['recent'][0] for k in ('visitor_hash','network_hash','email','name'))
    assert client.post('/api/demo-feedback',json={**body,'department':'X'*101}).status_code==422
