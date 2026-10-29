"""V17's 105 cap must never be presented as 105 eligible exemplar posts."""
from app.smart_radar_qa_tuning import eligible_exemplar_audit_targets,EXEMPLAR_V17_PILOT_LIMIT

def test_v17_105_ceiling_reduces_to_real_eligible_cohort():
    rows=[{'qa_id':'QA-'+str(i),'cohort':'exemplar'} for i in range(72)]
    rows+= [{'qa_id':'DEV-'+str(i),'cohort':'development'} for i in range(13)]
    rows+= [{'qa_id':'SEALED-'+str(i),'cohort':'sealed_holdout'} for i in range(13)]
    approved={'QA-'+str(i) for i in range(66)}
    targets=eligible_exemplar_audit_targets(rows,{},approved)
    assert EXEMPLAR_V17_PILOT_LIMIT==105
    assert len(targets)==66
    assert all(x['cohort']=='exemplar' for x in targets)
    assert all(x['qa_id'] in approved for x in targets)

def test_blocked_ids_do_not_appear_and_selection_is_order_independent():
    rows=[{'qa_id':'QA-'+str(i),'cohort':'exemplar'} for i in range(72)]
    approved={'QA-'+str(i) for i in range(66)}
    blocked={'QA-1':'Analyst review pending','QA-2':'Duplicate unresolved'}
    got=eligible_exemplar_audit_targets(rows,blocked,approved)
    reversed_rows=eligible_exemplar_audit_targets(list(reversed(rows)),blocked,approved)
    assert len(got)==64
    assert [x['qa_id'] for x in got]==[x['qa_id'] for x in reversed_rows]
    assert all(x['qa_id'] not in blocked for x in got)

def test_original_105_ceiling_remains_a_ceiling_not_a_paid_run():
    rows=[{'qa_id':'QA-'+str(i),'cohort':'exemplar'} for i in range(130)]
    approved={r['qa_id'] for r in rows}
    got=eligible_exemplar_audit_targets(rows,{},approved)
    assert len(got)==105
    assert got==eligible_exemplar_audit_targets(list(reversed(rows)),{},approved)
