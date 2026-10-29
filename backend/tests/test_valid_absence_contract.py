"""Valid candidate absence and empty grouping outcomes require no manual QA."""
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.candidate_registry import attach_candidate_ids,resolve_signals
from app.models import MonitoringCampaign
from app.finding_groups import finding_group_action
from app.access import default_permissions

def user():
    return {'id':'1','role':'National Administrator','status':'Active',
            'geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}

def db_session():
    db=Session(create_engine('sqlite:///:memory:'))
    Base.metadata.create_all(db.get_bind())
    return db

def test_no_candidate_is_valid_and_not_blocked():
    db=db_session()
    try:
        rows=[{'candidate_signals':[]},{'candidate_signals':['calon']},
              {'candidate_signals':['Unidentified public figure']}]
        diagnostics=attach_candidate_ids(db,user(),rows)
        assert all(x['candidate_classification']=='NO_CANDIDATE' for x in rows)
        assert all(x['candidate_classification_requires_manual_qa'] is False for x in rows)
        assert diagnostics['no_candidate_posts']==3
        assert diagnostics['requires_candidate_manual_qa'] is False
    finally:db.close()

def test_ambiguous_or_unknown_name_does_not_block_processing():
    db=db_session()
    try:
        rows=[{'candidate_signals':['Person A','Person B']}]
        attach_candidate_ids(db,user(),rows)
        assert rows[0]['canonical_candidate_ids']==[]
        assert rows[0]['candidate_classification']=='NO_CANDIDATE'
    finally:db.close()

def test_empty_group_preview_is_valid_and_free():
    db=db_session()
    try:
        db.add(MonitoringCampaign(id=5,name='Test',created_by='1',
            primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
        db.commit()
        result=finding_group_action(db,user(),'campaignFindingGroupsPreview',{},'5')
        assert result['proposal_count']==0
        assert result['no_matching_groups_is_valid'] is True
        assert result['grouping_evidence_missing_not_an_error'] is True
        assert result['paid_provider_called'] is False
    finally:db.close()
