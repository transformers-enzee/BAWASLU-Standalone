"""Cross-module use of canonical social IDs only; permission and provenance."""
from types import SimpleNamespace
import pytest
from fastapi import HTTPException
from app import source_lineage as lineage

def test_shared_social_lookup_returns_same_persisted_contract_without_ai(monkeypatch):
    post=SimpleNamespace(id=225,text_content='Election oversight concern')
    db=SimpleNamespace(get=lambda cls,key:post if cls is lineage.SocialListeningResult and key==225 else None)
    monkeypatch.setattr(lineage,'profile',lambda db,user:{'permissions':{'view_intelligence':True}})
    monkeypatch.setattr(lineage,'_result_in_scope',lambda db,p,row:True)
    from app import saved_assessment_views
    expected=[{'campaign_id':'1','assessment_version':4,'topic_labels':['BAWASLU Reputation'],
               'public_concern_signals':[{'status':'HUMAN_CONCERN_REVIEWED'}],
               'canonical_source_id':'social:225'}]
    monkeypatch.setattr(saved_assessment_views,'saved_classifications_for_posts',
                        lambda db,p,posts:{225:expected})
    response=lineage.resolve_saved_assessments('social:225',SimpleNamespace(id=1),db)
    assert response['saved_assessments']==expected
    assert response['identity_scope']=='SOCIAL_SOURCE_ONLY'
    assert response['assessment_count']==1
    assert response['radar_pilot_identity_crosswalk_verified'] is False
    assert response['paid_provider_called'] is False

def test_no_implicit_radar_crosswalk(monkeypatch):
    monkeypatch.setattr(lineage,'profile',lambda db,user:{'permissions':{'view_intelligence':True}})
    with pytest.raises(HTTPException) as exc:
        lineage.resolve_saved_assessments('radar:POST-001',SimpleNamespace(id=1),None)
    assert exc.value.status_code==409

def test_shared_lookup_denies_unauthorized_source(monkeypatch):
    monkeypatch.setattr(lineage,'profile',lambda db,user:{'permissions':{'view_intelligence':True}})
    monkeypatch.setattr(lineage,'_result_in_scope',lambda db,p,row:False)
    db=SimpleNamespace(get=lambda cls,key:SimpleNamespace(id=225))
    with pytest.raises(HTTPException) as exc:
        lineage.resolve_saved_assessments('social:225',SimpleNamespace(id=1),db)
    assert exc.value.status_code==404
