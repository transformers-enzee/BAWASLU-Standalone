"""Read-only Inbox job count regression guard."""
from pathlib import Path

def test_inbox_job_status_is_counted_not_hardcoded():
    text=Path(__file__).resolve().parents[1].joinpath('app','campaigns.py').read_text()
    inbox=text.split("if action=='campaignIntelligenceInbox':",1)[1].split("    if action==",1)[0]
    assert 'job_counts[job.state]+=1' in inbox
    assert 'AIAssessmentJob.result_id.in_(linked_ids)' in inbox
    assert "'job_counts':job_counts" in inbox

def test_assessment_audit_remains_independent():
    text=Path(__file__).resolve().parents[1].joinpath('app','campaigns.py').read_text()
    audit=text.split("if action in ('campaignAssessmentAudit','campaignAssessmentCorrection'):",1)[1].split("    if action=='campaignIntelligenceInbox':",1)[0]
    assert 'job_counts' not in audit
