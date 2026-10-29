from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import WatchlistItem
from app.access import default_permissions
from app.candidate_registry import attach_candidate_ids

def officer():
    return {'id':'11','role':'National Administrator','status':'Active',
        'geographic_scope':'Nationwide','permissions':default_permissions('National Administrator')}

def test_explicit_full_candidate_name_matches_existing_id_without_ai():
    db=Session(create_engine('sqlite:///:memory:'))
    try:
        Base.metadata.create_all(db.get_bind())
        db.add(WatchlistItem(name='Andika Pratama',type='Candidate',status='Active',
            priority='Medium',candidate_aliases_json='[]'))
        db.commit()
        row={'text_content':'Andika Pratama membahas pemilu.','candidate_signals':[]}
        result=attach_candidate_ids(db,officer(),[row])
        assert row['canonical_candidate_ids']==['candidate:1']
        assert row['candidate_classification']=='MATCHED'
        assert result['paid_provider_called'] is False
    finally:db.close()

def test_partial_name_and_generic_caleg_are_valid_no_candidate():
    db=Session(create_engine('sqlite:///:memory:'))
    try:
        Base.metadata.create_all(db.get_bind())
        db.add(WatchlistItem(name='Andika Pratama',type='Candidate',status='Active',
            priority='Medium',candidate_aliases_json='[]'))
        db.commit()
        row={'text_content':'Andika bertemu caleg.','candidate_signals':[]}
        attach_candidate_ids(db,officer(),[row])
        assert row['candidate_classification']=='NO_CANDIDATE'
        assert row['canonical_candidate_ids']==[]
    finally:db.close()

def test_missing_candidate_does_not_require_manual_qa():
    db=Session(create_engine('sqlite:///:memory:'))
    try:
        Base.metadata.create_all(db.get_bind())
        row={'text_content':'Daftar pemilih sedang diperiksa.','candidate_signals':[]}
        result=attach_candidate_ids(db,officer(),[row])
        assert result['no_candidate_posts']==1
        assert result['requires_candidate_manual_qa'] is False
    finally:db.close()
