"""v168.9: saved relevance → real Inbox → Command Center; casework → reporting."""
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import MonitoringCampaign,SocialListeningResult,CampaignEvidence,EvidenceAssessment,User,AccessGrant
from app.access import default_permissions,profile
from app.campaigns import campaign_action
from app.inbox_radar import compile_inbox_findings
from app.module_acceptance_evidence import module_acceptance_evidence
from app.casework import CaseAssignment,CaseReport
from app.management_reporting import build_briefing

def fixture():
    e=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(e)
    db=Session(e)
    db.add(User(id=1,email='qa@example.invalid',full_name='Synthetic QA',password_hash='unused'))
    db.add(AccessGrant(user_id=1,access_role='National Administrator',
        geographic_scope='Nationwide',status='Active',
        permissions_json=__import__('json').dumps(default_permissions('National Administrator'))))
    db.add(MonitoringCampaign(id=31,name='Synthetic election operations',created_by='1',
        primary_keywords_json='[]',secondary_keywords_json='[]',excluded_keywords_json='[]'))
    for rid,version_label in [
        (1,[(1,'RELEVANT')]),(2,[(1,'RELEVANT'),(2,'IRRELEVANT')]),
        (3,[(1,'HIGHLY_RELEVANT')]),(4,[(1,'UNASSESSED')]),
        (5,[(1,'RELEVANT')])]:
        db.add(SocialListeningResult(id=rid,run_id=1,platform='instagram',
            text_content='Daftar pemilih tetap perlu diverifikasi di TPS',author_name='Synthetic',
            canonical_url='https://example.invalid/evidence/'+str(rid),
            published_at='2026-11-12T08:00:00Z'))
        db.add(CampaignEvidence(campaign_id=31,result_id=rid,
            match_method='WATCHLIST_ACCOUNT' if rid==5 else 'KEYWORD'))
        for version,label in version_label:
            db.add(EvidenceAssessment(campaign_id=31,result_id=rid,assessment_version=version,
                relevance_label=label,sentiment='NEGATIVE',topic_labels_json='["Electoral Operations"]'))
    db.commit()
    p=profile(db,db.get(User,1))
    return e,db,p

def test_saved_versions_inbox_and_command_center_share_authoritative_sources():
    e,db,p=fixture()
    try:
        inventory=module_acceptance_evidence(db)
        assert inventory['counts']['eligible_saved_inbox_links']==2
        assert inventory['counts']['monitoring_links_without_valid_latest_relevance']==1
        result=campaign_action(db,p,'campaignIntelligenceInbox',{'campaign_id':'31'},'31')
        rows=result['findings']
        ids={r['id'] for r in rows}
        assert ids=={'1','3'}
        assert {r['relevance_label'] for r in rows}=={'RELEVANT','HIGHLY_RELEVANT'}
        groups=compile_inbox_findings(rows)
        grouped_ids={src for group in groups for src in group['source_ids']}
        assert grouped_ids=={'social:1','social:3'}
        assert sum(x['supporting_posts'] for x in groups)==2
        assert all(x['source_evidence_verified'] is False for x in groups)
        assert db.query(EvidenceAssessment).count()==6
    finally:db.close();e.dispose()

def test_latest_relevance_revision_drops_inbox_and_radar_without_paid_reanalysis():
    e,db,p=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=31,result_id=1,assessment_version=2,
            relevance_label='IRRELEVANT',sentiment='UNKNOWN'))
        db.commit()
        out=campaign_action(db,p,'campaignIntelligenceInbox',{'campaign_id':'31'},'31')
        ids={x['id'] for x in out['findings']}
        assert ids=={'3'}
        radar=compile_inbox_findings(out['findings'])
        assert {s for x in radar for s in x['source_ids']}=={'social:3'}
        inventory=module_acceptance_evidence(db)
        assert inventory['counts']['eligible_saved_inbox_links']==1
        assert inventory['provider_requests']==inventory['database_writes']==0
    finally:db.close();e.dispose()

def test_casework_reporting_scoped_counts_never_infer_legal_outcome():
    e,db,p=fixture()
    try:
        now=datetime.utcnow()
        db.add(CaseAssignment(id=1,title='Synthetic source review',source_type='SOCIAL',
            source_id='1',campaign_id=31,originating_scope='NATIONAL',
            target_scope='NATIONAL',target_department='Pengawasan',
            verified_province='',created_by=1,status='IN_REVIEW',created_at=now))
        db.add(CaseReport(id=1,case_id=1,title='Synthetic report',created_by=1,
            status='SUBMITTED',created_at=now))
        db.commit()
        report=build_briefing(db,p,1,period='weekly',now=now)
        assert report['metrics']['assignments']==1
        assert report['metrics']['submitted_reports']==1
        assert report['metrics']['approved_reports']==0
        assert report['metrics']['unique_linked_sources']==1
        assert not report['generated_by_ai']
        assert not report['management_consistency']['legal_verdict_confirmed']
        assert module_acceptance_evidence(db)['counts']['orphan_case_reports']==0
    finally:db.close();e.dispose()

def test_equal_version_latest_assessment_id_wins_inbox_and_radar():
    e,db,p=fixture()
    try:
        db.add(EvidenceAssessment(campaign_id=31,result_id=1,assessment_version=2,
            relevance_label='IRRELEVANT'))
        db.add(EvidenceAssessment(campaign_id=31,result_id=2,assessment_version=3,
            relevance_label='RELEVANT'))
        db.commit()
        # Distinct version-2 revisions are both valid records; the latest
        # assessment version must decide whether the source is surfaced.
        out=campaign_action(db,p,'campaignIntelligenceInbox',{'campaign_id':'31'},'31')
        assert {x['id'] for x in out['findings']}=={'2','3'}
        assert {src for g in compile_inbox_findings(out['findings'])
            for src in g['source_ids']}=={'social:2','social:3'}
    finally:db.close();e.dispose()
