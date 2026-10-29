"""No-credit runtime checks for the defined officer permission matrix."""
from app.access import ROLE_DEFINITIONS, default_permissions, has

def test_national_admin_has_full_administration_permissions():
    p=default_permissions('National Administrator')
    for key in ('administration','manage_users','human_validation','verify_evidence','manage_watchlist','add_intelligence'):
        assert p[key] is True

def test_provincial_analyst_can_read_and_submit_but_cannot_admin_or_validate():
    p=default_permissions('Provincial Analyst')
    assert p['view_intelligence'] and p['add_intelligence'] and p['review_ai_suggestions']
    assert not p['administration'] and not p['manage_users']
    assert not p['human_validation'] and not p['verify_evidence']

def test_provincial_administrator_has_scoped_management_role():
    p=default_permissions('Provincial Administrator')
    assert ROLE_DEFINITIONS['Provincial Administrator']['scope']=='Province'
    assert p['human_validation'] and p['manage_watchlist'] and p['administration']

def test_regency_officer_is_restricted_from_management():
    p=default_permissions('Regency/City Officer')
    assert ROLE_DEFINITIONS['Regency/City Officer']['scope']=='Regency/City'
    assert p['view_intelligence'] and p['add_intelligence']
    assert not p['administration'] and not p['manage_users'] and not p['human_validation']

def test_viewer_is_strictly_read_only():
    p=default_permissions('Viewer')
    assert p['view_intelligence'] is True
    assert all(not value for key,value in p.items() if key!='view_intelligence')
