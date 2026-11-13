"""v153.1 Command Centre review readiness and optional management evidence quality."""
from app.finding_review_readiness import build_finding_review_readiness
from app.management_reporting import monitoring_snapshot_from_findings
from app.finding_assessments import assess_finding
from test_reporting_monitoring_v1482 import post,finding,NOW,START

def sample(pages=None,flagged=True,cues=0,title="Pemilu potential issue"):
    f={"id":"f-1","title":title}
    a={"finding_id":"f-1","source_count_assessed":1,
       "source_provenance":{"missing_original_text":0,"missing_original_url":0,
                            "source_count_matches_finding":True},
       "legal":{"status":"PRELIMINARY_REVIEW_RECOMMENDED" if flagged else "NO_SAVED_POTENTIAL_VIOLATION_FLAG",
                "approved_reference_pages":pages or []},
       "platform_policy":{"status_counts":{"REVIEW_INDICATED":cues},
                          "policy_references":[{"platform":"X","policy_url":"https://x.com/rules"}]}}
    return f,a

def codes(f,a):
    return [x["code"] for x in build_finding_review_readiness(f,a)["issues"]]

def page(scope="PEMILU",version="2026 edition",date="2026-01-01"):
    return {"record_id":"DOC-1-P2","review_status":"OFFICER_REVIEWED",
            "legal_election_type":scope,"legal_version_label":version,
            "legal_effective_date":date}

def test_missing_reviewed_legal_reference():
    f,a=sample()
    assert "REVIEWED_LEGAL_REFERENCE_REQUIRED" in codes(f,a)

def test_reviewed_document_metadata_missing_not_legal_clearance():
    f,a=sample([page(version="",date="")])
    assert "LEGAL_VERSION_METADATA_INCOMPLETE" in codes(f,a)
    assert "LEGAL_CURRENTNESS_AND_AUTHORITY_UNVERIFIED" in codes(f,a)
    assert build_finding_review_readiness(f,a)["legal_currentness_verified"] is False

def test_explicit_scope_mismatch_is_advisory():
    f,a=sample([page(scope="PILKADA")])
    assert "POSSIBLE_ELECTION_TYPE_MISMATCH" in codes(f,a)

def test_both_election_scope_does_not_raise_mismatch():
    f,a=sample([page(scope="BOTH")])
    assert "POSSIBLE_ELECTION_TYPE_MISMATCH" not in codes(f,a)

def test_unreviewed_references_not_exposed_as_approved_citations():
    f,a=sample([page(),{**page(),"record_id":"DOC-9-P1","review_status":"UNREVIEWED"}])
    result=build_finding_review_readiness(f,a)
    assert all("DOC-9-P1" not in x["legal_page_ids"] for x in result["issues"])

def test_conflicting_and_missing_originals_require_review():
    f,a=sample([page()])
    a["source_provenance"].update({"missing_original_text":1,"missing_original_url":1,
                                 "source_text_conflicts":1,"source_count_matches_finding":False})
    c=codes(f,a)
    assert "ORIGINAL_POST_VERIFICATION" in c
    assert "CONFLICTING_SAVED_SOURCE_METADATA" in c
    assert "SOURCE_COUNT_RECONCILIATION" in c

def test_platform_only_cue_does_not_invent_legal_flag():
    f,a=sample([],False,1)
    c=codes(f,a)
    assert "PLATFORM_POST_CONTEXT_REVIEW" in c
    assert "CURRENT_PLATFORM_POLICY_UNVERIFIED" in c
    assert "REVIEWED_LEGAL_REFERENCE_REQUIRED" not in c

def test_unconfigured_platform_tracked_separately():
    f,a=sample([],False,0)
    a["platform_policy"]["status_counts"]={"POLICY_NOT_CONFIGURED":3}
    assert "PLATFORM_POLICY_REFERENCE_UNAVAILABLE" in codes(f,a)

def test_no_auto_decision_or_takedown_and_issue_counts_match():
    f,a=sample([page()],True,1)
    result=build_finding_review_readiness(f,a)
    assert all(result[k] is False for k in (
        "legal_violation_confirmed","platform_violation_confirmed",
        "automatic_assignment_created","automatic_takedown_requested",
        "current_platform_policy_verified","legal_applicability_verified"))
    assert sum(result["priority_counts"].values())==result["issue_count"]

def test_quality_counts_unique_dated_posts_only_and_avoids_unsafe_urls():
    p1=post(1);p1.update(message_original="",source_url="")
    p2=post(2,platform="mastodon");p2.update(source_url="javascript:alert(1)")
    p3=post(3,published="2026-01-01T00:00:00Z");p3.update(message_original="",source_url="")
    data=monitoring_snapshot_from_findings([finding("source_review",p1,dict(p1),p2,p3)],START,NOW)
    q=data["source_quality"]
    assert data["published_in_period"]==2
    assert q["missing_original_text"]==1
    assert q["missing_safe_original_url"]==2
    assert q["platform_policy_reference_unconfigured"]==1
    assert q["counts_are_unique_sources"] is True
    assert q["sample_completeness_verified"] is False

def test_saved_excerpt_conflict_is_one_source_not_two():
    p1=post(4);p2={**p1,"message_original":"different saved original"}
    q=monitoring_snapshot_from_findings([finding("discussion",p1,p2)],START,NOW)["source_quality"]
    assert q["conflicting_saved_original_text"]==1
    assert q["sampled_published_sources"]==1
    assert "message_original" not in q

def test_topic_and_time_boundary_apply_to_quality_population():
    bad=post(3,published="bad",text="")
    good=post(4,text="Riau evidence")
    result=monitoring_snapshot_from_findings([finding("discussion",bad,good)],START,NOW,topic="Riau")
    assert result["source_quality"]["sampled_published_sources"]==1

def test_finding_assessment_has_metadata_and_readiness_but_no_action(monkeypatch):
    import app.finding_assessments as module
    monkeypatch.setattr(module,"retrieve_knowledge",lambda *args,**kwargs:[{
        "document_id":1,"page":2,"title":"Pemilu SOP","issuer":"BAWASLU",
        "source_url":"/api/assistant-knowledge/1/download","record_id":"DOC-1-P2",
        "source_excerpt":"Pasal 21.","review_status":"OFFICER_REVIEWED",
        "document_type":"SOP","legal_election_type":"PEMILU",
        "legal_version_label":"2026 edition","legal_effective_date":"2026-01-01"}])
    f={"id":"f-1","title":"Pemilu issue","players":["violations"],
       "posts":[{"canonical_source_id":"social:1","result_id":"1","campaign_id":"42",
                 "source_url":"https://example.invalid/post/1",
                 "message_original":"Possible voting issue","platform":"X"}]}
    result=assess_finding(None,{},f)
    assert result["review_readiness"]["schema"]=="BAWASLU_COMMAND_CENTRE_FINDING_READINESS_V1531"
    assert result["legal"]["approved_reference_pages"][0]["legal_election_type"]=="PEMILU"
    assert result["legal"]["approved_reference_pages"][0]["legal_version_label"]=="2026 edition"
    assert result["review_readiness"]["automatic_takedown_requested"] is False
    assert result["paid_provider_called"] is False
