"""Regression: Assessment Audit must not reference Inbox-only job progress variables."""
from pathlib import Path

def test_audit_has_no_inbox_job_counter_loop():
    source=Path(__file__).resolve().parents[1].joinpath('app','campaigns.py').read_text()
    begin=source.index("if action in ('campaignAssessmentAudit','campaignAssessmentCorrection'):")
    end=source.index("    if action=='campaignIntelligenceInbox':",begin)
    audit=source[begin:end]
    assert 'job_counts' not in audit
    assert 'db.query(AIAssessmentJob)' not in audit
    assert "return {'assessments':output[:100],'paid_provider_called':False}" in audit
