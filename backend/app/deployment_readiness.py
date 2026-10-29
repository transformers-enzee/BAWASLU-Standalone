"""Read-only staging/deployment contracts. No service mutation or credentials."""
import os
from fastapi import APIRouter,Depends,HTTPException
from .auth import current_user
from .access import profile,has
from .db import get_db

router=APIRouter(prefix='/api/deployment',tags=['deployment'])
def deployment_snapshot(p,env=None):
    env=env if env is not None else os.environ
    configured=str(env.get('APP_ENV') or env.get('ENVIRONMENT') or 'production').lower()
    branch=str(env.get('RENDER_GIT_BRANCH') or '')
    commit=str(env.get('RENDER_GIT_COMMIT') or '')
    is_staging=configured in ('staging','test')
    return {'environment':configured,
      'is_staging':is_staging,
      'render_service_connected':bool(env.get('RENDER_SERVICE_ID')),
      'revision_identified':bool(commit),
      'branch_identified':bool(branch),
      'commit':commit or None,
      'branch':branch or None,
      'live_requires_health_check':True,
      'deployment_approval_recorded':False,
      'separate_staging_environment_verified':False,
      'role_gates_review_required':True,
      'paid_provider_called':False}

@router.get('/readiness')
def deployment_readiness(user=Depends(current_user),db=Depends(get_db)):
    p=profile(db,user)
    if not (has(p,'view_intelligence') and has(p,'administration')):
        raise HTTPException(403,'Administration permission required')
    return deployment_snapshot(p)
