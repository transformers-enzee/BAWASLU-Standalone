from app.smart_radar_qa_reference_audit import reference_diagnostic

def test_offline_reference_audit_is_development_only_and_no_provider():
    targets=[{"qa_id":"QA-1","shahrin_category":"Election Operations"},
             {"qa_id":"QA-2","shahrin_category":"Disputes / Legal"}]
    refs={"QA-1":[{"qa_id":"QA-3","shahrin_category":"Election Operations","similarity":.4},
                    {"qa_id":"QA-4","shahrin_category":"Allegations / Violations","similarity":.39}],
          "QA-2":[{"qa_id":"QA-5","shahrin_category":"Allegations / Violations","similarity":.1}]}
    report=reference_diagnostic(targets,refs)
    assert report["evaluated_development_posts"]==2
    assert report["nearest_reference_agreement"]==1
    assert report["weak_or_conflicting"]==2
    assert report["items"][0]["category_margin"]==.01
    assert report["items"][1]["reference_agrees"] is False
    assert "not measured AI" in report["warning"]
