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
            'page_path':'/demo/inbox','language':'id','visitor_key':'a'*32}

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
    assert len(report['recent'])==1
    assert report['recent'][0]['message']==payload()['message']
    assert 'visitor_hash' not in report['recent'][0]
    db=SessionLocal()
    assert db.query(DemoFeedback).count()==1
    assert len(db.query(DemoFeedback).first().visitor_hash)==64
    db.close()

def test_public_submission_validation_and_spam_protection():
    client=TestClient(app)
    assert client.post('/api/demo-feedback',json=payload('short')).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'page_path':'/administration'}).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'category':'secret'}).status_code==422
    assert client.post('/api/demo-feedback',json={**payload(),'website':'hidden-bot-field'}).status_code==400
    assert client.post('/api/demo-feedback',json=payload()).status_code==201
    assert client.post('/api/demo-feedback',json=payload()).status_code==409
    assert client.post('/api/demo-feedback',json=payload('Second useful piece of training feedback.')).status_code==201
    assert client.post('/api/demo-feedback',json=payload('Third useful piece of training feedback.')).status_code==201
    assert client.post('/api/demo-feedback',json=payload('Fourth useful piece of training feedback.')).status_code==429
    # A second visitor behind the same NAT/Wi-Fi must still be able to submit.
    second={**payload('Another visitor sharing the same training Wi-Fi.'),'visitor_key':'b'*32}
    assert client.post('/api/demo-feedback',json=second).status_code==201

def test_private_feedback_cannot_be_read_by_unauthenticated_demo():
    client=TestClient(app)
    assert client.get('/api/demo-feedback/admin',headers={'Authorization':'Bearer fake'}).status_code==401
    assert client.post('/api/demo-feedback',json={**payload(),'rating':6}).status_code==422
    assert client.get('/api/demo-feedback').status_code==405
