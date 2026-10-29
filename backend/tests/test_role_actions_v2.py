"""Zero-credit role/action regressions against actual registry entrypoints."""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import User, AccessGrant
from app.access import profile, default_permissions, has
from app.registry import registry_action


def setup_users():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    db=Session(engine)
    admin=User(id=1,email='admin@example.test',full_name='Admin',password_hash='unused')
    analyst=User(id=2,email='analyst@example.test',full_name='Analyst',password_hash='unused')
    db.add_all([admin,analyst])
    db.add(AccessGrant(user_id=1,access_role='National Administrator',
        geographic_scope='Nationwide',status='Active',
        permissions_json=json.dumps(default_permissions('National Administrator'))))
    db.add(AccessGrant(user_id=2,access_role='Provincial Analyst',
        geographic_scope='Province',province='Riau',status='Active',
        permissions_json=json.dumps(default_permissions('Provincial Analyst'))))
    db.commit()
    return db,admin,analyst


def test_empty_permission_grant_fails_closed_instead_of_role_defaults():
    db,admin,analyst=setup_users()
    try:
        grant=db.query(AccessGrant).filter_by(user_id=2).one()
        grant.permissions_json='{}'
        db.commit()
        p=profile(db,analyst)
        assert p['status']=='Active'
        assert not any(p['permissions'].values())
        assert not has(p,'view_intelligence')
        with pytest.raises(PermissionError):
            registry_action(db,p,'list',{})
    finally: db.close()


def test_invalid_permission_data_fails_closed():
    db,admin,analyst=setup_users()
    try:
        grant=db.query(AccessGrant).filter_by(user_id=2).one()
        grant.permissions_json='not-json'
        db.commit()
        assert not has(profile(db,analyst),'view_intelligence')
    finally:db.close()


def test_explicit_empty_assigned_permissions_stay_revoked_after_relogin():
    db,admin,analyst=setup_users()
    try:
        saved=registry_action(db,profile(db,admin),'setUser',{
            'access_role':'Provincial Analyst','geographic_scope':'Province',
            'province':'Riau','permissions':{},'status':'Active'},'2')
        assert saved['user']['permissions']['view_intelligence'] is False
        assert not has(profile(db,analyst),'view_intelligence')
        with pytest.raises(PermissionError):
            registry_action(db,profile(db,analyst),'createWatchlist',{'name':'Test'})
    finally:db.close()


def test_omitted_permission_list_uses_role_defaults_on_assignment():
    db,admin,analyst=setup_users()
    try:
        registry_action(db,profile(db,admin),'setUser',{
            'access_role':'Provincial Analyst','geographic_scope':'Province',
            'province':'Riau','status':'Active'},'2')
        assert has(profile(db,analyst),'view_intelligence')
        assert not has(profile(db,analyst),'manage_users')
    finally:db.close()


def test_null_permission_input_is_rejected_not_silently_granted():
    db,admin,analyst=setup_users()
    try:
        with pytest.raises(ValueError,match='Permissions must be an object'):
            registry_action(db,profile(db,admin),'setUser',{
                'access_role':'Viewer','geographic_scope':'Province',
                'province':'Riau','permissions':None},'2')
    finally:db.close()


def test_provincial_admin_cannot_assign_nationwide_scope():
    db,admin,analyst=setup_users()
    try:
        p=profile(db,admin)
        p.update(role='Provincial Administrator',geographic_scope='Province',province='Riau')
        with pytest.raises(PermissionError):
            registry_action(db,p,'setUser',{'access_role':'National Analyst',
                'geographic_scope':'Nationwide'},'2')
    finally:db.close()


def test_inactive_national_administrator_cannot_manage_users():
    db,admin,analyst=setup_users()
    try:
        p=profile(db,admin)
        p['status']='Inactive'
        with pytest.raises(PermissionError):
            registry_action(db,p,'setUser',{'access_role':'Viewer'},'2')
    finally:db.close()
