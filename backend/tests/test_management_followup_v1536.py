"""v153.6: permission-scoped follow-up queue and management report acceptance."""
from datetime import datetime
from json import dumps
from types import SimpleNamespace as Obj
from io import BytesIO

from docx import Document
from openpyxl import load_workbook
from pypdf import PdfReader

from app.management_followup_queue import management_followup_queue
from app.management_reporting import build_briefing
from app.management_report_templates import render_docx,render_xlsx,render_pdf
from app.access import profile
from app.models import User
from test_management_briefings_v1468 import dataset

def case(ident=1,status="IN_REVIEW"):
    return Obj(id=ident,status=status,source_type="SOCIAL",
               source_id=str(ident),source_url=f"https://example.invalid/{ident}",
               target_department="Penanganan Pelanggaran",
               title="SENSITIVE_PRIVATE_CASE_NOTE",source_excerpt="SENSITIVE_ORIGINAL_TEXT")

def report(status="DRAFT"):
    return Obj(status=status)

def review(ident=1,status="SOURCE_CHECKED",opened=True,source_url=None):
    item=case(ident)
    details={"status":status,"original_source_opened":opened,
             "source_type":item.source_type,"source_id":item.source_id,
             "source_url":source_url if source_url is not None else item.source_url,
             "note":"SENSITIVE_AUDIT_NOTE"}
    return Obj(id=ident,case_id=ident,action="SOURCE_REVIEW_RECORDED",
               details_json=dumps(details))

def follow(*cases,reports=None,events=None):
    return management_followup_queue(cases,reports or {},events or [])

def action(result):
    assert len(result["items"])==1
    return result["items"][0]

def test_empty_authorized_cohort_has_no_actions():
    x=follow()
    assert x["attention_count"]==0
    assert x["items"]==[]
    assert x["additional_database_queries"]==0
    assert x["automatic_casework_actions_created"] is False

def test_open_case_requires_receiving_team_review_not_auto_assignment():
    a=action(follow(case(status="OPEN")))
    assert a["action_code"]=="RECEIVING_TEAM_ACCEPTANCE"
    assert a["priority"]=="P1"
    assert a["responsible_role_hint"]=="RECEIVING_TEAM"
    assert a["recommended_action_is_assignment"] is False

def test_assigned_case_needs_officer_acceptance():
    a=action(follow(case(status="ASSIGNED")))
    assert a["action_code"]=="RECEIVING_TEAM_ACCEPTANCE"

def test_case_needing_information_stays_p1():
    a=action(follow(case(status="NEEDS_INFORMATION")))
    assert a["action_code"]=="CASE_INFORMATION_FOLLOWUP"
    assert a["priority"]=="P1"

def test_source_unavailable_requires_recheck_without_source_truth():
    a=action(follow(case(),events=[review(status="SOURCE_UNAVAILABLE",opened=False)]))
    assert a["action_code"]=="SOURCE_REVIEW_RECHECK"
    assert a["source_review_attested_in_window"] is False
    assert a["legal_outcome_confirmed"] is False

def test_invalid_checked_source_url_is_not_positive_attestation():
    a=action(follow(case(),events=[review(source_url="https://example.invalid/other")]))
    assert a["action_code"]=="SOURCE_REVIEW_RECHECK"
    assert a["source_review_attested_in_window"] is False

def test_no_event_in_window_is_historical_audit_check_not_source_missing():
    a=action(follow(case()))
    assert a["action_code"]=="CHECK_HISTORICAL_SOURCE_REVIEW"
    assert not a["latest_source_review_observed_in_window"]
    assert a["priority"]=="P2"
    x=follow(case())
    assert x["historical_source_review_may_exist"] is True
    assert x["source_review_scope"]=="LATEST_RECORDED_EVENT_WITHIN_REPORTING_WINDOW"

def test_source_attested_and_no_report_suggests_report_preparation():
    a=action(follow(case(),events=[review()]))
    assert a["action_code"]=="CREATE_OFFICER_REPORT"
    assert a["priority"]=="P2"
    assert a["source_review_attested_in_window"] is True

def test_saved_draft_and_source_check_suggests_submitting_latest_version():
    a=action(follow(case(),reports={1:report("DRAFT")},events=[review()]))
    assert a["action_code"]=="SUBMIT_OR_REVISE_LATEST_REPORT"

def test_returned_report_needs_revision():
    a=action(follow(case(),reports={1:report("RETURNED")},events=[review()]))
    assert a["action_code"]=="SUBMIT_OR_REVISE_LATEST_REPORT"

def test_submitted_latest_report_takes_independent_review_priority():
    a=action(follow(case(),reports={1:report("SUBMITTED")}))
    assert a["action_code"]=="INDEPENDENT_REPORT_REVIEW"
    assert a["priority"]=="P1"
    assert a["responsible_role_hint"]=="INDEPENDENT_REVIEWER"
    assert a["source_review_attested_in_window"] is False

def test_latest_approved_report_not_reassigned():
    x=follow(case(),reports={1:report("APPROVED")})
    assert x["attention_count"]==0
    assert x["approved_report_cases_without_open_followup"]==1

def test_closed_case_excluded_even_if_historic_event_pending():
    x=follow(case(status="CLOSED"),reports={1:report("SUBMITTED")})
    assert x["attention_count"]==0
    assert x["closed_cases_excluded"]==1

def test_latest_source_event_supersedes_earlier_checked_event():
    a=action(follow(case(),events=[review(1,"SOURCE_CHECKED"),Obj(
        id=99,case_id=1,action="SOURCE_REVIEW_RECORDED",
        details_json=dumps({"status":"NEEDS_INFORMATION","original_source_opened":False})
    )]))
    assert a["action_code"]=="SOURCE_REVIEW_RECHECK"

def test_no_raw_text_notes_evidence_or_assignee_ids_in_queue():
    x=follow(case(),events=[review()])
    serialized=str(x)
    assert "SENSITIVE_PRIVATE_CASE_NOTE" not in serialized
    assert "SENSITIVE_ORIGINAL_TEXT" not in serialized
    assert "SENSITIVE_AUDIT_NOTE" not in serialized
    assert x["source_truth_verified"] is False
    assert x["legal_verdict_confirmed"] is False

def test_only_whitelisted_safe_inbox_link_from_valid_case_id():
    a=action(follow(case(12,status="OPEN")))
    assert a["casework_url"]=="/inbox?casework=1&case_id=12&tab=reports"
    assert "source_id=" not in a["casework_url"]

def test_preview_is_bounded_but_counts_complete_for_authorized_cohort():
    rows=[case(i,status="OPEN" if i%2 else "IN_REVIEW") for i in range(1,18)]
    x=follow(*rows)
    assert x["attention_count"]==17
    assert x["preview_is_sample"] is True
    assert len(x["items"])==12
    assert sum(x["priority_counts"].values())==17
    assert x["items"][0]["priority"]=="P1"
    assert x["items"][0]["case_id"]==1
    assert [row["case_id"] for row in x["items"][:9]]==[1,3,5,7,9,11,13,15,17]
    assert x["items"][9]["case_id"]==2

def test_queue_item_count_matches_codes_without_double_counting():
    rows=[case(1,"OPEN"),case(2,"ASSIGNED"),case(3,"IN_REVIEW"),case(4,"CLOSED")]
    x=follow(*rows)
    assert x["attention_count"]==3
    assert sum(x["action_counts"].values())==3
    assert sum(x["priority_counts"].values())==3

def test_authorized_province_excludes_other_province_and_old_cases():
    db=dataset()
    try:
        riau=build_briefing(db,profile(db,db.get(User,2)),2,language="en")
        bali=build_briefing(db,profile(db,db.get(User,3)),3,language="en")
        national=build_briefing(db,profile(db,db.get(User,1)),1,language="en")
        assert riau["followup_queue"]["authorized_case_population"]==2
        assert [r["case_id"] for r in riau["followup_queue"]["items"]]==[1]
        assert [r["case_id"] for r in bali["followup_queue"]["items"]]==[3]
        assert national["followup_queue"]["authorized_case_population"]==3
        assert all(r["case_id"]!=4 for r in national["followup_queue"]["items"])
        assert national["followup_queue"]["casework_links_recheck_permissions"] is True
    finally:
        db.close()

def test_interim_template_has_case_specific_actions_but_never_approval():
    db=dataset()
    try:
        snap=build_briefing(db,profile(db,db.get(User,2)),2,language="en")
        template=snap["template"]
        assert template["followup_queue_summary"]["attention_count"]==1
        assert any("Case #1 (P1)" in x for x in template["recommended_actions"])
        assert "review order, not violation severity" in template["executive_summary"]
        assert template["approval_state"]=="DRAFT_NOT_APPROVED"
        assert template["automated_legal_verdict"] is False
        assert template["followup_queue_summary"]["automatic_actions_created"] is False
    finally:
        db.close()

def test_existing_pdf_docx_xlsx_exports_contain_case_specific_next_check():
    db=dataset()
    try:
        template=build_briefing(db,profile(db,db.get(User,2)),2,language="en")["template"]
        word=Document(BytesIO(render_docx(template)))
        assert "Case #1 (P1)" in " ".join(p.text for p in word.paragraphs)
        pdf=PdfReader(BytesIO(render_pdf(template)))
        assert "Case #1 (P1)" in " ".join(p.extract_text() or "" for p in pdf.pages)
        book=load_workbook(BytesIO(render_xlsx(template)),read_only=True)
        cells=" ".join(str(v) for row in book["Report Summary"].values for v in row if v is not None)
        assert "Case #1 (P1)" in cells
    finally:
        db.close()

def test_bilingual_summary_and_actions_present():
    db=dataset()
    try:
        snap=build_briefing(db,profile(db,db.get(User,2)),2,language="id")
        assert "Kasus #1" in " ".join(snap["template"]["recommended_actions"])
        assert "urutan tinjauan" in snap["template"]["executive_summary"]
    finally:
        db.close()

def test_no_new_ai_calls_case_actions_or_database_writes_from_queue():
    x=follow(case(1,"OPEN"))
    assert x["automatic_casework_actions_created"] is False
    assert x["formal_approval_created"] is False
    assert x["paid_provider_called"] is False
    assert x["additional_database_queries"]==0
