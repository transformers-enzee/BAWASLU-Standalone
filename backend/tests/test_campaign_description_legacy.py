"""Regression: legacy campaigns with >30 imported keywords can save descriptions.

Full edits still enforce the current keyword limit for modified keyword lists.
"""
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
import pytest
from app.campaigns import _campaign_edit_keywords, campaign_action

def test_unchanged_legacy_keyword_lists_are_preserved():
    original=['keyword '+str(n) for n in range(191)]
    assert _campaign_edit_keywords(list(original),'Main keywords',True,json.dumps(original)) == original
    secondary=['secondary '+str(n) for n in range(325)]
    assert _campaign_edit_keywords(list(secondary),'Secondary keywords',False,json.dumps(secondary)) == secondary

def test_changed_overlimit_keyword_lists_remain_rejected():
    original=['keyword '+str(n) for n in range(191)]
    changed=original+['another new keyword']
    with pytest.raises(ValueError, match='exceeds 30'):
        _campaign_edit_keywords(changed,'Main keywords',True,json.dumps(original))

def test_description_only_update_keeps_existing_keywords_and_saves():
    primary=json.dumps(['main '+str(n) for n in range(191)])
    secondary=json.dumps(['secondary '+str(n) for n in range(325)])
    c=SimpleNamespace(id=12, name='BAWASLU Demo', description='',
                      primary_keywords_json=primary,secondary_keywords_json=secondary,
                      excluded_keywords_json='[]',status='DRAFT',updated_at=None)
    db=MagicMock()
    db.get.return_value=c
    principal={'status':'Active','role':'National Administrator',
               'geographic_scope':'Nationwide',
               'permissions':{'view_intelligence':True,'administration':True}}
    with patch('app.campaigns._view',return_value={'description':'Monitoring Indonesian electoral conversations'}),patch('app.campaigns.audit'):
        result=campaign_action(db,principal,'updateCampaign',
                               {'description':'Monitoring Indonesian electoral conversations'},id='12')
    assert result['campaign']['description']=='Monitoring Indonesian electoral conversations'
    assert c.description=='Monitoring Indonesian electoral conversations'
    assert c.primary_keywords_json==primary
    assert c.secondary_keywords_json==secondary
    db.commit.assert_called_once()

def test_oversized_description_rejected_without_mutation():
    c=SimpleNamespace(id=12,description='Existing',status='DRAFT')
    db=MagicMock();db.get.return_value=c
    principal={'status':'Active','role':'National Administrator',
               'geographic_scope':'Nationwide',
               'permissions':{'view_intelligence':True,'administration':True}}
    with pytest.raises(ValueError, match='2000'):
        campaign_action(db,principal,'updateCampaign',{'description':'X'*2001},id='12')
    assert c.description=='Existing'
    db.commit.assert_not_called()
