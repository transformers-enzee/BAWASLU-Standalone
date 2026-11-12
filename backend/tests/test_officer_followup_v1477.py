"""v147.7 officer follow-up integration and latest-report security regressions.

Tests use only isolated SQLite fixtures. No client cases, database writes to
Supabase, paid provider calls or automatic takedown/approval actions.
"""
from datetime import datetime,timedelta
import json
from urllib.parse import parse_qs,urlsplit

import pytest
from fastapi import HTTPException
from sqlalchemy import event

from app.models import User,AccessGrant
from app.access import default_permissions,profile
from app.casework import (
    CaseAssignment,CaseReport,CaseTransition,
    NewCase,ReportDraft,ReportAction,
    create_case,create_report,update_report,transition_report,list_cases,case_detail,
    assistant_workspace,
)
from app.finding_assessments import contextual_casework_links,finding_assessments
from test_casework_workflow import dataset,confirmed


def user(db,id):
    return db.get(User,id)


def permission(db,id):
    return profile(db,user(db,id))


def evidence(source="11",campaign="90"):
    return {"id":"INBOX-V-11-90",
        "title":"Saved electoral oversight evidence",
        "players":["violations"],
        "supporting_posts":1,
        "posts":[{
            "canonical_source_id":"social:"+source,
            "result_id":source,"campaign_id":campaign,
            "source_url":"https://example.test/post/"+source,
            "message_original":"Dugaan pelanggaran di Riau perlu ditelaah.",
            "platform":"Instagram",
            "sentiment":"NEGATIVE","review_status":"FURTHER_INVESTIGATION",
        }]}


def draft():
    return ReportDraft(
        title="Source-backed officer review",
        executive_summary="This source requires independent checking.",
        findings="Saved post reports an allegation but does not establish a violation.",
        verification_notes="Inspect original post, source documents and verified jurisdiction.",
        recommendations="Escalate only after competent officer review.",
    )


def test_finding_handoff_selects_exact_authorized_source_without_write():
    db=dataset()
    try:
        finding=evidence()
        before=db.query(CaseTransition).count()
        follow=contextual_casework_links(db,permission(db,1),1,finding)
        assert len(follow["source_actions"])==1
        action=follow["source_actions"][0]
        url=parse_qs(urlsplit(action["casework_url"]).query)
        assert url["source_type"]==["SOCIAL"]
        assert url["source_id"]==["11"]
        assert url["campaign_id"]==["90"]
        assert url["casework"]==["1"]
        assert action["existing_case_id"] is None
        assert action["can_create_assignment"] is True
        assert follow["officer_confirmation_required"] is True
        assert follow["no_assignment_created"] is True
        assert db.query(CaseAssignment).count()==0
        assert db.query(CaseTransition).count()==before
    finally:
        db.close()


def test_existing_case_link_reuses_case_and_hides_other_provinces_cases():
    db=dataset()
    try:
        confirmed(db)
        created=create_case(NewCase(source_type="SOCIAL",source_id="11",
            campaign_id=90,department="Penanganan Pelanggaran",
            target_scope="PROVINCE",target_province="Riau",assignee_id=2),
            user(db,1),db)
        case_id=created["id"]
        before=db.query(CaseAssignment).count()
        follow=contextual_casework_links(db,permission(db,2),2,evidence())
        action=follow["source_actions"][0]
        assert action["existing_case_id"]==case_id
        assert action["existing_case_status"]=="ASSIGNED"
        assert action["casework_url"].startswith("/inbox?casework=1")
        assert parse_qs(urlsplit(action["casework_url"]).query)["case_id"]==[str(case_id)]
        assert follow["visible_existing_case_count"]==1
        assert follow["no_assignment_created"] is True
        assert db.query(CaseAssignment).count()==before

        # This low-level helper receives only already-authorized finding posts;
        # even with forged input, it never reveals the unrelated case ID.
        bali=contextual_casework_links(db,permission(db,3),3,evidence())
        assert bali["visible_existing_case_count"]==0
        assert bali["source_actions"][0]["existing_case_id"] is None
        assert parse_qs(urlsplit(bali["source_actions"][0]["casework_url"]).query).get("case_id") is None
        with pytest.raises(HTTPException) as err:
            case_detail(case_id,user(db,3),db)
        assert err.value.status_code==404
    finally:
        db.close()


def test_viewer_cannot_start_case_but_can_read_authorized_existing_case():
    db=dataset()
    try:
        db.add(User(id=8,email="viewer-followup@test.invalid",
            full_name="Viewer",password_hash="unused"))
        db.add(AccessGrant(user_id=8,access_role="Viewer",status="Active",
            geographic_scope="Nationwide",province="",
            permissions_json=json.dumps(default_permissions("Viewer"))))
        db.commit()
        empty=contextual_casework_links(db,permission(db,8),8,evidence())
        assert empty["can_create_assignment"] is False
        assert empty["source_actions"][0]["casework_url"] is None

        existing=create_case(NewCase(source_type="SOCIAL",source_id="11",
            campaign_id=90,department="Pengawasan",target_scope="NATIONAL"),
            user(db,1),db)
        visible=contextual_casework_links(db,permission(db,8),8,evidence())
        assert visible["source_actions"][0]["existing_case_id"]==existing["id"]
        assert "case_id=" in visible["source_actions"][0]["casework_url"]
        assert visible["source_actions"][0]["can_create_assignment"] is False
    finally:
        db.close()


def test_forged_source_id_is_never_injected_into_handoff_url():
    db=dataset()
    try:
        item=evidence(source="11%26case_id%3D999",campaign="90")
        result=contextual_casework_links(db,permission(db,1),1,item)
        assert result["source_actions"]==[]
        assert result["source_actions_total"]==0
        assert result["casework_url"]=="/inbox?casework=1"
    finally:
        db.close()


def test_report_versions_have_single_current_approval_queue_and_stale_409():
    db=dataset()
    try:
        case=create_case(NewCase(source_type="SOCIAL",source_id="11",
            campaign_id=90,department="Hukum & Sengketa",
            target_scope="NATIONAL"),user(db,1),db)
        first=create_report(case["id"],draft(),user(db,1),db)
        submitted=transition_report(first["id"],
            ReportAction(status="SUBMITTED"),user(db,1),db)
        assert submitted["status"]=="SUBMITTED"
        assert list_cases(user(db,4),db)["queue_counts"]["needs_my_review"]==1
        assert assistant_workspace(user(db,4),db)["reports_for_my_review"]==1

        second=create_report(case["id"],draft(),user(db,1),db)
        detail=case_detail(case["id"],user(db,4),db)
        current=next(x for x in detail["reports"] if x["id"]==second["id"])
        old=next(x for x in detail["reports"] if x["id"]==first["id"])
        assert current["is_latest_version"] is True
        assert old["is_latest_version"] is False
        assert list_cases(user(db,4),db)["queue_counts"]["needs_my_review"]==0
        assert assistant_workspace(user(db,4),db)["reports_for_my_review"]==0
        with pytest.raises(HTTPException) as ex:
            transition_report(first["id"],
                ReportAction(status="APPROVED"),user(db,4),db)
        assert ex.value.status_code==409
        assert db.get(CaseReport,first["id"]).status=="SUBMITTED"
        with pytest.raises(HTTPException) as ex:
            update_report(first["id"],draft(),user(db,1),db)
        assert ex.value.status_code==403  # A submitted version is never editable.

        transition_report(second["id"],ReportAction(status="SUBMITTED"),user(db,1),db)
        assert list_cases(user(db,4),db)["queue_counts"]["needs_my_review"]==1
        with pytest.raises(HTTPException) as ex:
            transition_report(second["id"],
                ReportAction(status="APPROVED"),user(db,1),db)
        assert ex.value.status_code==403
        approved=transition_report(second["id"],
            ReportAction(status="APPROVED"),user(db,4),db)
        assert approved["status"]=="APPROVED"
        assert approved["reviewed_by"]==4
        assert list_cases(user(db,4),db)["queue_counts"]["needs_my_review"]==0
        assert assistant_workspace(user(db,4),db)["reports_for_my_review"]==0
    finally:
        db.close()



def test_old_draft_cannot_be_mutated_after_newer_report_exists():
    db=dataset()
    try:
        case=create_case(NewCase(source_type="SOCIAL",source_id="11",
            campaign_id=90,department="Data & Analisis",
            target_scope="NATIONAL"),user(db,1),db)
        old=create_report(case["id"],draft(),user(db,1),db)
        new=create_report(case["id"],draft(),user(db,1),db)
        with pytest.raises(HTTPException) as err:
            update_report(old["id"],draft(),user(db,1),db)
        assert err.value.status_code==409
        with pytest.raises(HTTPException) as err:
            transition_report(old["id"],ReportAction(status="SUBMITTED"),user(db,1),db)
        assert err.value.status_code==409
        edited=update_report(new["id"],draft(),user(db,1),db)
        assert edited["id"]==new["id"] and edited["status"]=="DRAFT"
    finally:
        db.close()


def test_scoped_case_queue_is_filtered_in_sql_before_300_row_limit():
    db=dataset()
    statements=[]
    try:
        older=datetime.utcnow()-timedelta(days=7)
        db.add(CaseAssignment(id=900,title="Authorized Riau assignment",
            source_type="SOCIAL",source_id="11",campaign_id=90,
            originating_scope="NATIONAL",originating_province="",
            target_scope="PROVINCE",target_province="Riau",
            verified_province="Riau",target_department="Pengawasan",
            created_by=1,updated_at=older,status="OPEN"))
        for i in range(1000,1320):
            db.add(CaseAssignment(id=i,title="Unrelated Bali assignment",
                source_type="SOCIAL",source_id=str(i),campaign_id=90,
                originating_scope="PROVINCE",originating_province="Bali",
                target_scope="PROVINCE",target_province="Bali",
                verified_province="Bali",target_department="Pengawasan",
                created_by=3,updated_at=datetime.utcnow(),status="OPEN"))
        db.commit()
        def observe(conn,cursor,statement,parameters,context,executemany):
            if "FROM case_assignments" in statement and " LIMIT " in statement.upper():
                statements.append(statement)
        event.listen(db.bind,"before_cursor_execute",observe)
        try:
            riau=list_cases(user(db,2),db)
        finally:
            event.remove(db.bind,"before_cursor_execute",observe)
        assert riau["queue_counts"]["all"]==1
        assert [x["id"] for x in riau["cases"]]==[900]
        assert riau["query_scope"]=="SQL_AND_CASEWORK_VISIBILITY"
        assert riau["queue_window_limit"]==300
        assert riau["queue_is_sample"] is False
        assert statements
        assert any("originating_province" in sql and "target_province" in sql
                   for sql in statements)
        assert assistant_workspace(user(db,2),db)["visible_open_cases"]==1
    finally:
        db.close()


def test_finding_endpoint_rejects_unavailable_source_before_casework_lookup(monkeypatch):
    from app import smart_radar
    db=dataset()
    try:
        monkeypatch.setattr(smart_radar,"access_findings",
            lambda connection,principal: [evidence()] if principal.id==1 else [])
        with pytest.raises(HTTPException) as ex:
            finding_assessments(evidence()["id"],user(db,3),db)
        assert ex.value.status_code==404
        assert db.query(CaseAssignment).count()==0
    finally:
        db.close()
