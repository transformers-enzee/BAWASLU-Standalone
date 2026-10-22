"""No-paid-provider pilot selection QA."""
from types import SimpleNamespace
from app.assessment_pilot import choose_platform_sample

def test_sample_spreads_across_platforms_and_is_stable():
    rows=[SimpleNamespace(platform='instagram',result_id=i) for i in range(1,21)]
    rows += [SimpleNamespace(platform='x',result_id=i) for i in range(21,25)]
    rows += [SimpleNamespace(platform='youtube',result_id=25)]
    expected=[1,21,25,2,22,3,23,4,24,5]
    assert [r.result_id for r in choose_platform_sample(rows,10)]==expected
    assert [r.result_id for r in choose_platform_sample(rows,10)]==expected

def test_no_overrun_or_empty_sample():
    assert choose_platform_sample([],50)==[]
    only=[SimpleNamespace(platform=None,result_id=11)]
    assert choose_platform_sample(only,40)==only
