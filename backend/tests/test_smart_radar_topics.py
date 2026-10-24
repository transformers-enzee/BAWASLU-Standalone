"""Phase 3 topic-based intelligence and officer workflow regression tests."""
from app.smart_radar_intelligence import assign_theme, build_topic_findings

def post(pid, message, platform="x"):
    return {"pilot_post_id":pid,"message_original":message,
            "platform":platform,"published_at_raw":"2026-10-01",
            "source_url":"https://example.org/"+pid}

def actor(message):
    return ["Gibran Rakabuming Raka"] if "gibran" in message.lower() else []

def source_view(p):
    return dict(p)

def test_same_court_issue_one_case_different_posts():
    ps=[post("A","Gibran pendidikan ijazah sidang MK"),
        post("B","Gibran syarat pendidikan dan PHPU Mahkamah Konstitusi")]
    findings=build_topic_findings(ps,{}, {},actor,source_view)
    assert len(findings)==1
    f=findings[0]
    assert f["supporting_posts"]==2
    assert f["status"]=="pending"
    assert set(f["perspectives"])=={"operations","reputation"}
    assert "narratives" in f["players"] and "concerns" in f["players"]
    assert f["priority_score"] is None

def test_organizer_ethics_distinct_cases():
    ps=[post("A","Themis Indonesia mengadukan KPU dan Bawaslu ke DKPP"),
        post("B","DKPP periksa Ketua KPU Kabupaten Langkat dugaan etik")]
    findings=build_topic_findings(ps,{}, {},actor,source_view)
    assert len(findings)==2
    assert len({f["id"] for f in findings})==2

def test_review_removes_pending_but_preserves_narrative():
    ps=[post("A","Gibran pendidikan ijazah sidang MK")]
    states={"RADAR-GIBRAN-ELIGIBILITY":{
       "status":"monitoring","first_reviewed_at":"2026-10-24T01:00:00Z"}}
    f=build_topic_findings(ps,states,{},actor,source_view)[0]
    assert f["human_reviewed"] is True
    assert f["status"]=="monitoring"
    assert "narratives" in f["players"]

def test_civic_participation_for_awareness():
    f=build_topic_findings([post("A","Bawaslu edukasi pengawasan partisipatif")],{}, {},actor,source_view)[0]
    assert f["status"]=="awareness"
    assert f["review_basis"]=="For Awareness"

def test_relevance_does_not_create_priority():
    f=build_topic_findings([post("A","Gibran pendidikan ijazah sidang MK")],{}, {},actor,source_view)[0]
    assert f["priority_label"]=="Review suggested · Unscored"
