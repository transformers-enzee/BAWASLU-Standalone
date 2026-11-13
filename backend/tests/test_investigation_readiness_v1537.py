"""v153.7: management readiness is observational, scoped, human-review-only."""
from json import dumps
from io import BytesIO
from types import SimpleNamespace as Obj

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

from app.management_investigation_readiness import investigation_readiness_board
from app.management_reporting import build_briefing
from app.management_report_templates import render_docx,render_xlsx,render_pdf
from app.access import profile
from app.models import User
from test_management_briefings_v1468 import dataset
from test_management_followup_v1536 import case, report, review

def board(*cases,reports=None,events=None):
    return investigation_readiness_board(cases,reports or {},events or [])

def one(x):
    assert len(x["preview"])==1
    return x["preview"][0]

def test_empty_population_is_zero_and_does_not_claim_approval():
    x=board()
    assert x["authorized_case_count"]==0
    assert x["review_attention_count"]==0
    assert x["database_queries"]==0
    assert x["any_case_assigned_or_updated"] is False
    assert x["legal_violation_confirmed"] is False
    assert x["independent_review_approved"] is False

def test_missing_recent_source_event_is_history_check_not_missing_evidence():
    x=one(board(case()))
    assert x["group"]=="REVIEW_HISTORY_CHECK"
    assert x["reason_code"]=="NO_WINDOW_SOURCE_REVIEW_EVENT"
    assert not x["source_review_observed_in_window"]
    assert x["next_check_code"]=="INSPECT_EARLIER_AUDIT_HISTORY"
    assert x["prepared_for_legal_determination"] is False

def test_submitted_report_no_window_source_event_requires_history_check():
    x=one(board(case(),reports={1:report("SUBMITTED")}))
    assert x["group"]=="REVIEW_HISTORY_CHECK"
    assert x["reason_code"]=="SUBMITTED_WITHOUT_WINDOW_SOURCE_REVIEW_EVENT"
    assert x["latest_report_status"]=="SUBMITTED"

def test_submitted_report_with_failed_last_source_check_requires_recheck():
    x=one(board(case(),reports={1:report("SUBMITTED")},
                events=[review(status="SOURCE_UNAVAILABLE",opened=False)]))
    assert x["group"]=="EVIDENCE_RECHECK"
    assert x["reason_code"]=="SUBMITTED_WITH_UNRESOLVED_WINDOW_SOURCE_REVIEW"
    assert x["source_check_attested_in_window"] is False

def test_submitted_report_with_source_check_recorded_needs_independent_review():
    x=one(board(case(),reports={1:report("SUBMITTED")},events=[review()]))
    assert x["group"]=="INDEPENDENT_REVIEW"
    assert x["next_check_code"]=="INDEPENDENT_REVIEW_OF_SUBMITTED_REPORT"
    assert x["source_check_attested_in_window"] is True
    assert x["ready_for_independent_review_is_legal_approval"] is False

def test_valid_source_event_and_no_report_is_officer_action():
    x=one(board(case(),events=[review()]))
    assert x["group"]=="OFFICER_ACTION"
    assert x["reason_code"]=="SOURCE_CHECK_LOGGED_REPORT_DECISION_PENDING"
    assert x["next_check_code"]=="OFFICER_REPORT_DECISION"

def test_valid_source_event_with_draft_is_officer_action():
    x=one(board(case(),reports={1:report("DRAFT")},events=[review()]))
    assert x["group"]=="OFFICER_ACTION"

def test_valid_source_event_with_returned_report_is_officer_action():
    x=one(board(case(),reports={1:report("RETURNED")},events=[review()]))
    assert x["group"]=="OFFICER_ACTION"

def test_latest_failed_source_event_replaces_older_success():
    bad=Obj(id=99,case_id=1,action="SOURCE_REVIEW_RECORDED",
            details_json=dumps({"status":"NEEDS_INFORMATION","original_source_opened":False}))
    x=one(board(case(),events=[review(),bad]))
    assert x["group"]=="EVIDENCE_RECHECK"
    assert not x["source_check_attested_in_window"]

def test_latest_successful_source_check_replaces_older_failure():
    bad=Obj(id=1,case_id=1,action="SOURCE_REVIEW_RECORDED",
            details_json=dumps({"status":"SOURCE_UNAVAILABLE","original_source_opened":False}))
    good=review()
    good.id=99
    x=one(board(case(),events=[bad,good]))
    assert x["group"]=="OFFICER_ACTION"
    assert x["source_check_attested_in_window"] is True

def test_mismatched_original_url_blocks_source_attestation():
    x=one(board(case(),events=[review(source_url="https://example.invalid/other")]))
    assert x["group"]=="EVIDENCE_RECHECK"

def test_malformed_audit_detail_is_recheck_not_runtime_error():
    damaged=Obj(id=7,case_id=1,action="SOURCE_REVIEW_RECORDED",
                details_json='["not", "an", "object"]')
    x=one(board(case(),events=[damaged]))
    assert x["group"]=="EVIDENCE_RECHECK"
    assert not x["source_check_attested_in_window"]

def test_new_open_case_requires_officer_acceptance_not_factual_clearance():
    x=one(board(case(status="OPEN"),events=[review()]))
    assert x["group"]=="OFFICER_ACTION"
    assert x["next_check_code"]=="RECEIVING_OFFICER_ACCEPTANCE"

def test_assigned_case_requires_receiving_officer_acceptance():
    x=one(board(case(status="ASSIGNED")))
    assert x["reason_code"]=="RECEIVING_OFFICER_NOT_YET_ACCEPTED"

def test_case_needs_information_is_officer_action():
    x=one(board(case(status="NEEDS_INFORMATION"),events=[review()]))
    assert x["reason_code"]=="CASE_INFORMATION_REQUESTED"

def test_approved_report_with_open_case_status_is_review_conflict_not_case_clearance():
    x=one(board(case(status="OPEN"),reports={1:report("APPROVED")}))
    assert x["group"]=="OTHER_FOLLOWUP"
    assert x["reason_code"]=="APPROVED_REPORT_WITH_UNRESOLVED_CASE_STATUS"
    assert x["next_check_code"]=="VERIFY_UNRECOGNIZED_CASE_STATE"
    assert x["prepared_for_legal_determination"] is False

def test_approved_latest_report_is_workflow_complete_not_legal_clearance():
    x=board(case(),reports={1:report("APPROVED")})
    assert x["group_counts"]["WORKFLOW_COMPLETE"]==1
    assert x["review_attention_count"]==0
    assert x["preview"]==[]
    assert x["legal_violation_confirmed"] is False

def test_closed_case_is_workflow_complete_even_with_submitted_report():
    x=board(case(status="CLOSED"),reports={1:report("SUBMITTED")})
    assert x["group_counts"]["WORKFLOW_COMPLETE"]==1
    assert x["review_attention_count"]==0

def test_unrecognized_case_state_is_not_falsely_approved():
    x=one(board(case(status="UNKNOWN_STATE"),events=[review()],reports={1:report("UNKNOWN_REPORT")}))
    assert x["group"]=="OTHER_FOLLOWUP"
    assert x["next_check_code"]=="VERIFY_UNRECOGNIZED_CASE_STATE"

def test_full_authorized_totals_and_capped_preview_are_not_confused():
    rows=[case(i,"IN_REVIEW") for i in range(1,19)]
    x=board(*rows)
    assert x["authorized_case_count"]==18
    assert x["review_attention_count"]==18
    assert x["group_counts"]["REVIEW_HISTORY_CHECK"]==18
    assert len(x["preview"])==12
    assert x["preview_is_sample"] is True
    assert x["group_counts_cover_full_authorized_cohort"] is True
    assert [item["case_id"] for item in x["preview"]]==list(range(1,13))

def test_one_classification_per_case_with_multiple_group_counts():
    cases=[case(1,"IN_REVIEW"),case(2,"OPEN"),case(3,"CLOSED"),
           case(4,"IN_REVIEW"),case(5,"IN_REVIEW")]
    reports={4:report("SUBMITTED"),5:report("SUBMITTED")}
    events=[review(1,status="SOURCE_UNAVAILABLE",opened=False),review(4)]
    x=board(*cases,reports=reports,events=events)
    assert x["group_counts"]=={
        "EVIDENCE_RECHECK":1,
        "REVIEW_HISTORY_CHECK":1,
        "OFFICER_ACTION":1,
        "INDEPENDENT_REVIEW":1,
        "WORKFLOW_COMPLETE":1,
        "OTHER_FOLLOWUP":0}
    assert sum(x["group_counts"].values())==5
    assert x["review_attention_count"]==4

def test_board_never_exposes_audit_notes_titles_or_raw_source_text():
    x=board(case(),events=[review()])
    output=str(x)
    for secret in ("SENSITIVE_AUDIT_NOTE","SENSITIVE_PRIVATE_CASE_NOTE","SENSITIVE_ORIGINAL_TEXT"):
        assert secret not in output
    assert x["source_truth_verified"] is False
    assert x["platform_violation_confirmed"] is False

def test_casework_link_only_uses_authorized_numeric_case_id_and_rechecks_permission():
    row=one(board(case(17)))
    assert row["casework_url"]=="/inbox?casework=1&case_id=17&tab=reports"
    assert row["casework_permissions_rechecked_on_navigation"] is True

def test_riau_and_bali_are_isolated_and_old_cases_are_outside_window():
    db=dataset()
    try:
        p=lambda uid:profile(db,db.get(User,uid))
        riau=build_briefing(db,p(2),2,language="en")["investigation_readiness"]
        bali=build_briefing(db,p(3),3,language="en")["investigation_readiness"]
        national=build_briefing(db,p(1),1,language="en")["investigation_readiness"]
        assert riau["authorized_case_count"]==2
        assert riau["group_counts"]["OTHER_FOLLOWUP"]==1
        assert riau["group_counts"]["WORKFLOW_COMPLETE"]==1
        assert [r["case_id"] for r in riau["preview"]]==[1]
        assert bali["authorized_case_count"]==1
        assert bali["group_counts"]["REVIEW_HISTORY_CHECK"]==1
        assert [r["case_id"] for r in bali["preview"]]==[3]
        assert national["authorized_case_count"]==3
        assert all(row["case_id"]!=4 for row in national["preview"])
        assert national["database_queries"]==0
    finally:
        db.close()

def test_english_and_indonesian_export_remain_unsigned_and_workflow_only():
    db=dataset()
    try:
        p=profile(db,db.get(User,2))
        en=build_briefing(db,p,2,language="en")["template"]
        ind=build_briefing(db,p,2,language="id")["template"]
        assert en["investigation_readiness_summary"]["authorized_case_count"]==2
        assert en["investigation_readiness_summary"]["group_counts"]["OTHER_FOLLOWUP"]==1
        assert "Investigation follow-up across authorized assignments" in en["executive_summary"]
        assert "Kesiapan tindak lanjut" in ind["executive_summary"]
        assert en["approval_state"]=="DRAFT_NOT_APPROVED"
        assert en["investigation_readiness_summary"]["source_truth_verified"] is False
        assert en["investigation_readiness_summary"]["automatic_actions_created"] is False
    finally:
        db.close()

def test_existing_pdf_word_xlsx_exports_preserve_readiness_summary():
    db=dataset()
    try:
        t=build_briefing(db,profile(db,db.get(User,2)),2,language="en")["template"]
        word=Document(BytesIO(render_docx(t)))
        assert "Investigation follow-up across authorized assignments" in " ".join(p.text for p in word.paragraphs)
        pdf=PdfReader(BytesIO(render_pdf(t)))
        assert "Investigation follow-up across authorized assignments" in " ".join(page.extract_text() or "" for page in pdf.pages)
        book=load_workbook(BytesIO(render_xlsx(t)),read_only=True)
        content=" ".join(str(x) for row in book["Report Summary"].values for x in row if x is not None)
        assert "Investigation follow-up across authorized assignments" in content
    finally:
        db.close()

def test_old_followup_queue_semantics_and_main_metrics_remain_unchanged():
    db=dataset()
    try:
        p=profile(db,db.get(User,2))
        r=build_briefing(db,p,2,language="en")
        assert r["followup_queue"]["attention_count"]==1
        assert r["metrics"]["assignments"]==2
        assert r["metrics"]["approved_reports"]==1
        assert r["template"]["scorecard"][0]["value"]==2
        assert r["investigation_readiness"]["any_case_assigned_or_updated"] is False
    finally:
        db.close()

def test_source_review_event_not_observed_never_means_permanent_absence():
    x=board(case())
    assert x["missing_window_source_event_does_not_mean_never_reviewed"] is True
    assert x["scope"]=="AUTHORIZED_CASES_CREATED_IN_SELECTED_UTC_PERIOD"

def test_no_ai_calls_new_queries_automatic_actions_or_approval():
    x=board(case())
    assert x["paid_ai_calls"]==0
    assert x["database_queries"]==0
    assert x["any_takedown_requested"] is False
    assert x["independent_review_approved"] is False
