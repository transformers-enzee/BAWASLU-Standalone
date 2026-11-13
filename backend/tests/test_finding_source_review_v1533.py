"""v153.3: source-by-source officer checklists and management quality actions."""
from app.finding_source_review import source_review_plan
from app.finding_assessments import assess_finding
from app.management_reporting import monitoring_snapshot_from_findings
from app.management_report_templates import build_interim_template
from test_reporting_monitoring_v1482 import post,finding,NOW,START

def source(number=1,**kwargs):
    return {"canonical_source_id":"social:"+str(number),"result_id":str(number),
            "campaign_id":"42","message_original":"Ordinary public discussion",
            "source_url":"https://example.invalid/post/"+str(number),
            "platform":"X",**kwargs}

def policy(status="NO_DIRECT_SIGNAL_IDENTIFIED",platform="X"):
    return {"status":status,"platform":platform}

def plan(rows,groups=None,outcomes=None,flagged=False):
    return source_review_plan(rows,groups or [[r] for r in rows],
        outcomes or [policy() for _ in rows],flagged)

def test_unique_source_has_verification_and_officer_steps():
    result=plan([source()])
    assert result["source_count"]==1
    item=result["actions"][0]
    assert item["officer_check_codes"]==[
        "VERIFY_ORIGINAL_POST_CONTEXT_AND_PUBLICATION","OFFICER_DECISION_REQUIRED"]
    assert item["priority"]=="P3"
    assert item["casework_url"] is None

def test_missing_original_evidence_is_p1_and_recoverable():
    row=source();row.update(message_original="",source_url="")
    item=plan([row])["actions"][0]
    assert item["priority"]=="P1"
    assert "RECOVER_ORIGINAL_POST_TEXT" in item["officer_check_codes"]
    assert "RECOVER_OR_VALIDATE_ORIGINAL_POST_URL" in item["officer_check_codes"]
    assert not item["original_url_available"]

def test_malicious_url_never_passes_scheme_check():
    row=source();row["source_url"]="javascript:alert(1)"
    item=plan([row])["actions"][0]
    assert item["source_url"]==""
    assert item["priority"]=="P1"

def test_source_variants_dedupe_and_require_reconciliation():
    row=source()
    variation={**row,"message_original":"Different saved post","source_url":"https://example.invalid/changed"}
    item=plan([row],[[row,variation]])["actions"][0]
    assert item["linked_variants"]==2
    assert item["saved_text_conflict"] is True
    assert item["saved_url_conflict"] is True
    assert "RECONCILE_SAVED_SOURCE_VARIANTS" in item["officer_check_codes"]
    assert item["priority"]=="P1"

def test_secondary_variant_url_can_be_used_without_verifying_content():
    row=source();row["source_url"]=""
    variation={**row,"source_url":"https://example.invalid/valid"}
    item=plan([row],[[row,variation]])["actions"][0]
    assert item["source_url"]=="https://example.invalid/valid"
    assert item["source_url_verification"]=="SCHEME_ONLY_NOT_CONTENT_VERIFIED"

def test_platform_cues_require_current_policy_but_no_platform_verdict():
    item=plan([source()],outcomes=[policy("CONTEXT_REVIEW_REQUIRED")])["actions"][0]
    assert "COMPARE_CURRENT_PLATFORM_RULES" in item["officer_check_codes"]
    assert item["source_level_platform_violation_confirmed"] is False
    assert item["priority"]=="P2"

def test_unconfigured_policy_uses_distinct_step():
    item=plan([source()],outcomes=[policy("POLICY_NOT_CONFIGURED")])["actions"][0]
    assert "LOCATE_CURRENT_PLATFORM_POLICY" in item["officer_check_codes"]

def test_finding_level_flag_never_becomes_a_source_legal_verdict():
    item=plan([source()],flagged=True)["actions"][0]
    assert item["finding_level_potential_violation_flag"] is True
    assert item["source_level_legal_violation_confirmed"] is False
    assert "CHECK_ELECTORAL_LAW_AND_JURISDICTION" in item["officer_check_codes"]

def test_sample_caps_at_twelve_in_priority_order():
    rows=[source(i) for i in range(1,16)]
    rows[14]["source_url"]=""
    result=plan(rows)
    assert result["source_count"]==15
    assert result["sampled"] is True
    assert len(result["actions"])==12
    assert result["actions"][0]["source_id"]=="social:15"
    assert sum(result["priorities"].values())==15

def test_non_numeric_ids_not_usable_for_casework_routing():
    row=source();row["result_id"]="١٢";row["campaign_id"]="42x"
    item=plan([row])["actions"][0]
    assert item["result_id"]==""
    assert item["campaign_id"]==""
    assert item["casework_url"] is None

def test_assessment_integration_reuses_previously_screened_posts(monkeypatch):
    import app.finding_assessments as module
    monkeypatch.setattr(module,"retrieve_knowledge",lambda *args,**kwargs:[])
    f={"id":"f","title":"Public concern","players":["concerns"],
       "posts":[source(7),source(7)]}
    result=assess_finding(None,{},f)
    assert result["source_investigation"]["source_count"]==1
    assert result["source_investigation"]["actions"][0]["linked_variants"]==2
    assert result["source_investigation"]["paid_provider_called"] is False
    assert result["review_readiness"]["issue_count"]>=0

def test_authorized_casework_urls_only_from_existing_handoff(monkeypatch):
    import app.finding_assessments as module
    import app.smart_radar as radar
    monkeypatch.setattr(module,"profile",lambda *_: {})
    monkeypatch.setattr(module,"has",lambda _,permission:permission=="view_intelligence")
    monkeypatch.setattr(module,"retrieve_knowledge",lambda *a,**k:[])
    f={"id":"visible","title":"Public concern","players":["concerns"],
       "posts":[source(7),source(8)]}
    monkeypatch.setattr(radar,"access_findings",lambda *_:[f])
    monkeypatch.setattr(module,"contextual_casework_links",lambda *a,**k:{
        "source_actions":[
            {"source_id":"7","campaign_id":"42","casework_url":"/inbox?casework=1&source_id=7"},
            {"source_id":"99","campaign_id":"42","casework_url":"/inbox?casework=1&source_id=99"}
        ],"no_assignment_created":True})
    person=type("Officer",(),{"id":1})()
    result=module.finding_assessments("visible",person,None)
    links={item["result_id"]:item["casework_url"]
           for item in result["source_investigation"]["actions"]}
    assert links["7"]=="/inbox?casework=1&source_id=7"
    assert links["8"] is None
    assert all(item["casework_url"] is None or "/inbox?" in item["casework_url"]
               for item in result["source_investigation"]["actions"])

def test_quality_priority_list_excludes_sensitive_source_text():
    p1=post(1);p1.update(message_original="",source_url="")
    p2=post(2,platform="mastodon");p2.update(message_original="Sensitive synthetic",source_url="")
    snap=monitoring_snapshot_from_findings([finding("discussion",p1,p2)],START,NOW)
    quality=snap["source_quality"]
    codes=[x["code"] for x in quality["review_priorities"]]
    assert "VERIFY_ORIGINAL_POST_TEXT" in codes
    assert "VERIFY_ORIGINAL_SOURCE_URL" in codes
    assert "CHECK_CURRENT_PLATFORM_RULES" in codes
    assert "Sensitive synthetic" not in str(quality)
    assert quality["review_priorities_are_not_casework_actions"] is True

def test_conflicting_source_text_is_counted_once():
    p1=post(1);p2={**p1,"message_original":"another saved wording"}
    snap=monitoring_snapshot_from_findings([finding("discussion",p1,p2)],START,NOW)
    priority=[x for x in snap["source_quality"]["review_priorities"]
              if x["code"]=="RECONCILE_CONFLICTING_SAVED_EXCERPTS"]
    assert len(priority)==1 and priority[0]["affected_sources"]==1

def test_undated_sources_are_separate_from_dated_quality_denominator():
    p1=post(1,published="unknown",text="")
    p2=post(2)
    snap=monitoring_snapshot_from_findings([finding("discussion",p1,p2)],START,NOW)
    quality=snap["source_quality"]
    assert quality["sampled_published_sources"]==1
    assert quality["undated_sources_outside_published_denominator"]==1
    assert any(x["code"]=="RECOVER_EXPLICIT_PUBLICATION_TIME"
               for x in quality["review_priorities"])

def test_empty_monitoring_has_no_fabricated_recommendations():
    snap=monitoring_snapshot_from_findings([],START,NOW)
    assert snap["source_quality"]["review_priorities"]==[]

def template(monitoring):
    return build_interim_template({
       "metrics":{"assignments":0,"unique_linked_sources":0,
                  "active_assignments":0,"closed_assignments":0,
                  "submitted_reports":0,"approved_reports":0},
       "scope":{"geographic_scope":"Nationwide"},"recent_cases":[],
       "period":"weekly","topic_filter":"",
       "window_start_utc":"2026-11-06T00:00:00Z",
       "window_end_utc":"2026-11-13T00:00:00Z",
       "report_coverage":{},"monitoring":monitoring},language="en")

def test_report_export_includes_specific_source_quality_recommendations():
    row=post(1);row.update(message_original="",source_url="")
    snap=monitoring_snapshot_from_findings([finding("discussion",row)],START,NOW)
    report=template(snap)
    assert report["approval_state"]=="DRAFT_NOT_APPROVED"
    assert any("original post text" in action for action in report["recommended_actions"])
    assert any("original links" in action for action in report["recommended_actions"])
    assert report["automated_legal_verdict"] is False

def test_report_without_monitoring_keeps_casework_only_recommendations():
    report=template({"enabled":False})
    assert not any("original links" in action for action in report["recommended_actions"])
    assert report["approval_state"]=="DRAFT_NOT_APPROVED"
