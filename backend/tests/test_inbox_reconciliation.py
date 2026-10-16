from pathlib import Path

def test_reconciliation_is_read_only_and_scoped():
    s=Path(__file__).resolve().parents[1].joinpath('app','campaigns.py').read_text()
    part=s.split("if action=='campaignIntelligenceInbox':",1)[1].split("    if action==",1)[0]
    assert 'campaign_job_states[job.result_id]=job.state' in part
    assert 'if item and _result_in_scope(db,p,item):linked_ids.add(item.id)' in part
    for key in ('unassessed_without_job','assessed_without_job','pending_job_with_assessment','completed_job_without_assessment'):
        assert key in part
    assert "'reconciliation':reconciliation" in part
