"""Integrated candidate registry, grouping and cross-module persistence QA.

All scenarios use local SQLite and saved source posts. No provider calls.
"""
import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.access import default_permissions
from app.models import (WatchlistItem,MonitoringCampaign,SocialListeningResult,
                        CampaignEvidence,EvidenceAssessment,CampaignFindingGroup)
from app.registry import registry_action
from app.candidate_registry import (
    validate_aliases,candidate_index,resolve_signals,attach_candidate_ids)
from app.finding_groups import finding_group_action
from app.campaigns import campaign_action
from app.saved_assessment_views import saved_classifications_for_posts


def principal(role='National Administrator',scope='Nationwide',province=''):
    return {'id':'11','name':'Test Officer','role':role,'status':'Active',
            'geographic_scope':scope,'province':province,
            'permissions':default_permissions(role)}


def memory_db():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    return Session(engine)


def fixture_posts(db,n=3):
    db.add(MonitoringCampaign(id=91,name='Provincial oversight',
        province='Riau',created_by='11',primary_keywords_json='["pemilu"]',
        secondary_keywords_json='[]',excluded_keywords_json='[]'))
    texts=[
        'Dugaan pelanggaran di Riau terkait daftar pemilih pada TPS A',
        'Dugaan pelanggaran di Riau: daftar pemilih pada TPS B diprotes',
        'Klarifikasi dugaan pelanggaran di Riau atas daftar pemilih TPS C',
    ]
    for i in range(1,n+1):
        db.add(SocialListeningResult(id=i,run_id=1,platform='instagram',
            author_name='Reporter '+str(i),
            canonical_url='https://example.test/post/'+str(i),
            published_at='2026-10-03T08:00:00Z',
            text_content=texts[(i-1)%3]+str(i)))
        db.add(CampaignEvidence(campaign_id=91,result_id=i))
        db.add(EvidenceAssessment(campaign_id=91,result_id=i,
            assessment_version=1,relevance_label='RELEVANT',
            sentiment='NEUTRAL',candidate_signals_json='[]',
            potential_issue_signals_json='[]'))
    db.commit()


def test_officer_registers_alias_without_creating_duplicate_candidate():
    db=memory_db()
    try:
        response=registry_action(db,principal(),'createWatchlist',{'name':'Andika Pratama',
            'type':'Candidate','status':'Active','candidate_aliases':['Andika P.','A. Pratama']})
        assert response['item']['canonical_candidate_id'].startswith('candidate:')
        assert response['item']['candidate_aliases']==['Andika P.','A. Pratama']
        assert db.query(WatchlistItem).count()==1
        resolved=resolve_signals(['Andika Pratama','Andika P.'],candidate_index(db,principal()))
        assert len(resolved)==2
        assert resolved[0]['canonical_candidate_id']==resolved[1]['canonical_candidate_id']
        assert all(x['identity_status']=='TRACKED_CANDIDATE_MATCH_REQUIRES_VERIFICATION'
                   for x in resolved)
    finally:db.close()


def test_conflicting_alias_cannot_silently_merge_two_people():
    db=memory_db()
    try:
        registry_action(db,principal(),'createWatchlist',{'name':'Person First',
            'type':'Candidate','candidate_aliases':['Known Alternate']})
        with pytest.raises(ValueError,match='conflicts'):
            registry_action(db,principal(),'createWatchlist',{'name':'Person Second',
                'type':'Candidate','candidate_aliases':['Known Alternate']})
        assert db.query(WatchlistItem).count()==1
    finally:db.close()


def test_alias_revoke_and_permission_enforcement():
    db=memory_db()
    try:
        saved=registry_action(db,principal(),'createWatchlist',{'name':'Person First',
            'type':'Candidate','candidate_aliases':['Known Alternate']})
        candidate_id=saved['item']['id']
        viewer=principal('Viewer')
        with pytest.raises(PermissionError):
            registry_action(db,viewer,'updateWatchlist',
                {'candidate_aliases':['Different Name']},candidate_id)
        updated=registry_action(db,principal(),'updateWatchlist',
            {'candidate_aliases':[]},candidate_id)
        assert updated['item']['candidate_aliases']==[]
        result=resolve_signals(['Known Alternate'],candidate_index(db,principal()))
        assert result[0]['identity_status']=='UNMATCHED_CANDIDATE_NAME'
    finally:db.close()


def test_generic_aliases_are_rejected_and_unknown_names_remain_distinct():
    for candidate in (['Bawaslu'],['Caleg']):
        with pytest.raises(ValueError):
            validate_aliases(candidate,'Person First')
    db=memory_db()
    try:
        assert resolve_signals(['Person First','Person Second'],
            candidate_index(db,principal()))==[
                {'source_name':'Person First','canonical_candidate_id':None,
                 'identity_status':'UNMATCHED_CANDIDATE_NAME'},
                {'source_name':'Person Second','canonical_candidate_id':None,
                 'identity_status':'UNMATCHED_CANDIDATE_NAME'}]
    finally:db.close()


def test_inbox_and_watchlist_share_persistent_candidate_id():
    db=memory_db()
    try:
        registry_action(db,principal(),'createWatchlist',{'name':'Andika Pratama',
            'type':'Candidate','status':'Active','province':'Riau',
            'candidate_aliases':['Andika P.']})
        fixture_posts(db,1)
        assessment=db.query(EvidenceAssessment).one()
        assessment.candidate_signals_json='["Andika P."]'
        db.commit()
        inbox=campaign_action(db,principal(),'campaignIntelligenceInbox',
            {'campaign_id':'91'},None)
        finding=inbox['findings'][0]
        assert finding['canonical_candidate_ids']==['candidate:1']
        assert inbox['candidate_registry_diagnostics']['matched_mentions']==1
        linked=saved_classifications_for_posts(
            db,principal(),[db.get(SocialListeningResult,1)])[1][0]
        assert linked['candidate_identity_matches'][0]['canonical_candidate_id']=='candidate:1'
        assert linked['assessment_persisted'] is True
    finally:db.close()


def test_scoped_candidate_lookup_does_not_leak_out_of_region():
    db=memory_db()
    try:
        registry_action(db,principal(),'createWatchlist',{'name':'Person First',
            'type':'Candidate','province':'Jawa Barat','candidate_aliases':['Known Alternate']})
        provincial=principal('Provincial Analyst','Province','Riau')
        results=resolve_signals(['Known Alternate'],candidate_index(db,provincial))
        assert results[0]['canonical_candidate_id'] is None
    finally:db.close()


def test_preview_uses_only_saved_relevant_posts_and_zero_paid_calls():
    db=memory_db()
    try:
        fixture_posts(db)
        result=finding_group_action(db,principal(),'campaignFindingGroupsPreview',{},'91')
        assert result['eligible_posts']==3
        assert result['proposal_count']>=2  # Incident cluster and emerging narrative
        assert result['paid_provider_called'] is False
        assert {x['type'] for x in result['proposals']} >= {
            'NARRATIVE_CANDIDATE','INCIDENT_CANDIDATE'}
        assert db.query(CampaignFindingGroup).count()==0
    finally:db.close()


def test_save_is_confirmed_idempotent_and_rejects_unprivileged_role():
    db=memory_db()
    try:
        fixture_posts(db)
        with pytest.raises(ValueError,match='Explicit confirmation'):
            finding_group_action(db,principal(),'campaignFindingGroupsSave',{},'91')
        first=finding_group_action(db,principal(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')
        assert first['newly_saved']>=2
        second=finding_group_action(db,principal(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')
        assert second['newly_saved']==0
        assert second['already_saved']>=2
        assert db.query(CampaignFindingGroup).count()==first['newly_saved']
        with pytest.raises(PermissionError):
            finding_group_action(db,principal('Viewer'),'campaignFindingGroupsSave',
                {'confirm_save':True},'91')
    finally:db.close()


def test_human_acceptance_and_rejection_does_not_assert_legal_guilt():
    db=memory_db()
    try:
        fixture_posts(db)
        result=finding_group_action(db,principal(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')
        group_id=result['saved_group_ids'][0]
        with pytest.raises(ValueError,match='10-1200'):
            finding_group_action(db,principal(),'campaignFindingGroupsReview',
                {'group_id':group_id,'decision':'ACCEPTED','rationale':'short'},'91')
        reply=finding_group_action(db,principal(),'campaignFindingGroupsReview',
            {'group_id':group_id,'decision':'ACCEPTED',
             'rationale':'Verified grouping of listed source posts, not legal wrongdoing.'},'91')
        assert reply['group']['review_status']=='ACCEPTED'
        assert reply['group']['legal_violation_confirmed'] is False
        listing=finding_group_action(db,principal(),'campaignFindingGroupsList',{},'91')
        assert listing['accepted_count']==1
        with pytest.raises(ValueError,match='immutable'):
            finding_group_action(db,principal(),'campaignFindingGroupsReview',
                {'group_id':group_id,'decision':'REJECTED',
                 'rationale':'Now reject this established human decision.'},'91')
    finally:db.close()


def test_review_without_human_validation_is_denied():
    db=memory_db()
    try:
        fixture_posts(db)
        group=finding_group_action(db,principal(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')['saved_group_ids'][0]
        with pytest.raises(PermissionError):
            finding_group_action(db,principal('Provincial Analyst'),'campaignFindingGroupsReview',
                {'group_id':group,'decision':'ACCEPTED',
                 'rationale':'Reviewed incident grouping thoroughly'},'91')
    finally:db.close()


def test_cross_campaign_access_denied_even_when_id_exists():
    db=memory_db()
    try:
        fixture_posts(db)
        group=finding_group_action(db,principal(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')['saved_group_ids'][0]
        with pytest.raises(PermissionError):
            finding_group_action(db,principal('Provincial Analyst','Province','Bali'),
                'campaignFindingGroupsList',{},'91')
        with pytest.raises(PermissionError):
            finding_group_action(db,principal(),'campaignFindingGroupsReview',{
                'group_id':group,'decision':'ACCEPTED',
                'rationale':'Valid rationale but wrong campaign'},'999')
    finally:db.close()


def test_group_list_does_not_expose_unlinked_or_inaccessible_sources():
    db=memory_db()
    try:
        fixture_posts(db)
        result=finding_group_action(db,principal(),'campaignFindingGroupsSave',
            {'confirm_save':True},'91')
        db.query(CampaignEvidence).filter_by(result_id=1).delete()
        db.commit()
        assert not finding_group_action(db,principal(),
            'campaignFindingGroupsList',{},'91')['groups']
    finally:db.close()


def test_frontend_offers_alias_editor_and_grouping_review_without_ai_calls():
    from pathlib import Path
    root=Path(__file__).resolve().parents[2]/'frontend'
    js=(root/'public/ui-freeze/watchlist-live.js').read_text(encoding='utf-8')
    html=(root/'public/ui-freeze/watchlist-v2_2.html').read_text(encoding='utf-8')
    inbox=(root/'src/pages/Inbox.jsx').read_text(encoding='utf-8')
    assert 'onUpdateAliases' in js
    assert "sentiment,flag:validatedFlag" in js
    assert 'newCandidateAliases' in html and 'editCandidateAliases' in html
    assert 'campaignFindingGroupsSave' in inbox
    assert 'campaignFindingGroupsReview' in inbox
    assert 'Preview groups (free)' in inbox
