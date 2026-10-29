"""No credit deployment readiness and authorized diagnostics."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app import deployment_readiness as module

def test_reports_missing_staging_as_missing_not_done():
 p={'status':'Active','permissions':{'administration':True,'view_intelligence':True}}
 data=module.deployment_snapshot(p,{'APP_ENV':'production','RENDER_GIT_COMMIT':'abc'})
 assert data['revision_identified'] is True
 assert data['separate_staging_environment_verified'] is False
 assert data['deployment_approval_recorded'] is False
 assert data['paid_provider_called'] is False

def test_readiness_requires_active_admin(monkeypatch):
 monkeypatch.setattr(module,'profile',lambda db,user:{'status':'Active','permissions':{'view_intelligence':True,'administration':False}})
 with pytest.raises(HTTPException) as e:
  module.deployment_readiness(SimpleNamespace(id=1),None)
 assert e.value.status_code==403

def test_readiness_does_not_leak_service_secrets():
 payload=module.deployment_snapshot({}, {'APP_ENV':'staging','RENDER_GIT_BRANCH':'qa',
 'OPENAI_API_KEY':'should-never-appear','DATABASE_URL':'db-secret'})
 assert 'should-never-appear' not in str(payload)
 assert 'db-secret' not in str(payload)
