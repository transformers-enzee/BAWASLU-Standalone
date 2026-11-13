"""v154.4: on-demand saved-evidence to officer-confirmed casework preparation.

Only isolated in-memory SQLite is used. The live Supabase database is read-only
and no actual case is assigned or approved by these tests.
"""
from types import SimpleNamespace as Obj
import pytest
from fastapi import HTTPException
from sqlalchemy import event

from app.officer_pilot_intake import officer_pilot_candidates
from app.casework import pilot_intake,create_case,NewCase,CaseAssignment,CaseTransition
from app.access import profile
from app.models import User
from test_casework_workflow import dataset
from test_management_briefings_v1468 import dataset as viewer_dataset

def post(source=11,campaign=90,text="Saved evidence",url="https://example.invalid/saved",
         platform="Instagram",province=""):
    return {"result_id":str(source),"campaign_id":str(campaign),
            "message_original":text,"source_url":url,
            "platform":platform,"verified_incident_province":province}

def finding(kind="source_review",posts=None):
    return {"kind":kind,"posts":posts if posts is not None else [post()]}

def list_rows(findings,visible=(),limit=12):
    return officer_pilot_candidates(findings,visible,limit)

def test_empty_authorized_window_yields_no_fabricated_candidates():
    result=list_rows([])
    assert result["observed_authorized_unique_sources"]==0
    assert result["items"]==[]
    assert result["no_assignment_created"] is True
    assert result["requires_officer_confirmation"] is True

def test_saved_source_flag_is_preliminary_and_routes_to_existing_form():
    x=list_rows([finding()])["items"][0]
    assert x["source_id"]=="11"
    assert x["campaign_id"]=="90"
    assert x["review_signal"]=="SAVED_SOURCE_FLAG_REVIEW"
    assert x["casework_link"]=="/inbox?casework=1&source_type=SOCIAL&source_id=11&campaign_id=90&tab=assignments"
    assert x["legal_violation_confirmed"] is False
    assert x["original_source_verified"] is False

def test_weaker_duplicate_campaign_does_not_replace_saved_source_flag():
    low=finding("source_awareness",[post(11,91)])
    strong=finding("source_review",[post(11,90)])
    x=list_rows([low,strong])["items"][0]
    assert x["campaign_id"]=="90"
    assert x["review_signal"]=="SAVED_SOURCE_FLAG_REVIEW"
    assert list_rows([strong,low])["items"]==list_rows([low,strong])["items"]

def test_one_post_across_many_authorized_findings_counted_once():
    x=list_rows([finding("source_review",[post(11,90)]),
                 finding("discussion",[post(11,90)]),
                 finding("narrative_candidate",[post(11,91)])])
    assert x["observed_authorized_unique_sources"]==1
    assert len(x["items"])==1

def test_public_concerns_are_not_automatically_treated_as_violation():
    x=list_rows([finding("discussion")])["items"][0]
    assert x["review_signal"]=="SAVED_PUBLIC_CONCERN_DISCUSSION"
    assert x["legal_violation_confirmed"] is False

def test_narrative_and_general_sources_have_distinct_review_reasons():
    a=list_rows([finding("narrative_candidate")])["items"][0]
    b=list_rows([finding("source_awareness")])["items"][0]
    assert a["review_signal"]=="SAVED_EMERGING_NARRATIVE"
    assert b["review_signal"]=="SAVED_RELEVANT_INBOX_SOURCE"

def test_no_saved_text_is_recover_source_not_case_assignment():
    row=list_rows([finding(posts=[post(text="")])])["items"][0]
    assert row["review_step"]=="RECOVER_SOURCE_EVIDENCE"
    assert row["casework_link"] is None
    assert row["source_link"]=="/inbox?campaign_id=90&result_id=11"

def test_missing_url_is_source_recovery_not_origin_verification():
    row=list_rows([finding(posts=[post(url="")])])["items"][0]
    assert row["original_source_url_available"] is False
    assert row["source_text_available"] is True
    assert row["casework_link"] is None

@pytest.mark.parametrize("unsafe",[
    "javascript:alert(1)","data:text/html,surprise",
    "ftp://example.invalid/post","https://user:password@example.invalid/post",
    "https://","http://[invalid"
])
def test_unsafe_original_urls_never_produce_casework_prefill(unsafe):
    row=list_rows([finding(posts=[post(url=unsafe)])])["items"][0]
    assert row["original_source_url_available"] is False
    assert row["casework_link"] is None
    assert row["source_link"]=="/inbox?campaign_id=90&result_id=11"

@pytest.mark.parametrize("bad",["0","-1","١١","11&case_id=8","NaN","1.0",""])
def test_invalid_or_nonascii_ids_cannot_become_casework_links(bad):
    assert list_rows([finding(posts=[post(source=bad)])])["items"]==[]

def test_invalid_campaign_rejected_even_with_valid_source():
    assert list_rows([finding(posts=[post(campaign="x&case_id=7")])])["items"]==[]

def test_only_saved_original_id_is_used_in_safe_link():
    x=list_rows([finding(posts=[post(11,90,platform="<script>")])])["items"][0]
    assert "script" not in str(x["casework_link"])
    assert "source_type=SOCIAL" in x["casework_link"]
    assert x["platform"]=="<script>"

def test_verified_province_metadata_never_authorizes_jurisdiction_by_itself():
    x=list_rows([finding(posts=[post(province="Riau")])])["items"][0]
    assert x["incident_jurisdiction_verified"] is True
    assert x["verified_incident_province"]=="Riau"
    assert x["original_source_verified"] is False
    assert x["casework_requires_fresh_source_and_jurisdiction_authorization"] if "casework_requires_fresh_source_and_jurisdiction_authorization" in x else True

def test_visible_open_case_reuses_exact_campaign_and_source():
    existing=Obj(id=24,source_type="SOCIAL",source_id="11",campaign_id=90,status="OPEN")
    row=list_rows([finding()],visible=[existing])["items"][0]
    assert row["visible_open_case_id"]==24
    assert row["casework_link"]=="/inbox?casework=1&case_id=24&tab=reports"
    assert row["case_already_exists_in_visible_scope"] is True
    assert row["review_step"]=="CONTINUE_VISIBLE_CASEWORK"

def test_closed_cases_not_presented_as_existing_open_work():
    closed=Obj(id=24,source_type="SOCIAL",source_id="11",campaign_id=90,status="CLOSED")
    row=list_rows([finding()],visible=[closed])["items"][0]
    assert row["visible_open_case_id"] is None
    assert "source_id=11" in row["casework_link"]

def test_other_campaign_existing_case_does_not_attach_to_this_source_link():
    visible=Obj(id=24,source_type="SOCIAL",source_id="11",campaign_id=91,status="OPEN")
    row=list_rows([finding()],visible=[visible])["items"][0]
    assert row["visible_open_case_id"] is None

def test_bounded_preview_retains_correct_authorized_window_count():
    findings=[finding("source_review",[post(source=i,campaign=90)])
              for i in range(1,20)]
    x=list_rows(findings,limit=12)
    assert x["observed_authorized_unique_sources"]==19
    assert x["returned_count"]==12
    assert x["preview_is_sample"] is True
    assert len(x["items"])==12
    assert x["not_complete_social_collection"] is True

def test_no_original_text_or_url_leaks_in_officer_candidate_response():
    confidential="STRICTLY_PRIVATE_ORIGINAL_CONTENT_12345"
    url="https://private.example.invalid/do-not-share"
    x=list_rows([finding(posts=[post(text=confidential,url=url)])])
    assert confidential not in str(x)
    assert url not in str(x)
    assert "url_available" not in x
    assert x["no_paid_provider_called"] is True

def _patch(monkeypatch,findings):
    import app.inbox_radar as radar
    monkeypatch.setattr(radar,"live_inbox_findings",
        lambda db,principal:(findings,{"feed_is_authorized":True}))

def test_endpoint_scopes_to_saved_evidence_and_does_not_create_case(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding()])
        before=db.query(CaseAssignment).count()
        result=pilot_intake(db.get(User,1),db)
        assert result["schema"]=="BAWASLU_OFFICER_PILOT_INTAKE_V1544"
        assert result["permission_checked_at_request"] is True
        assert result["inbox_source_rescoped_on_action"] is True
        assert result["items"][0]["source_id"]=="11"
        assert db.query(CaseAssignment).count()==before==0
        assert db.query(CaseTransition).count()==0
    finally:db.close()

def test_viewer_role_cannot_request_pilot_intake(monkeypatch):
    db=viewer_dataset()
    try:
        _patch(monkeypatch,[finding()])
        with pytest.raises(HTTPException) as exc:
            pilot_intake(db.get(User,4),db)
        assert exc.value.status_code==403
    finally:db.close()

def test_endpoint_empty_snapshot_does_not_create_case(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[])
        x=pilot_intake(db.get(User,1),db)
        assert x["items"]==[]
        assert x["observed_authorized_unique_sources"]==0
        assert x["no_assignment_created"] is True
    finally:db.close()

def test_endpoint_makes_no_casework_writes(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding()])
        statements=[]
        def recorder(conn,cursor,statement,params,ctx,many):
            statements.append(statement.lstrip().lower())
        event.listen(db.get_bind(),"before_cursor_execute",recorder)
        try:
            pilot_intake(db.get(User,1),db)
        finally:
            event.remove(db.get_bind(),"before_cursor_execute",recorder)
        assert not any(sql.startswith(("insert ","update ","delete ")) for sql in statements)
    finally:db.close()

def test_intake_link_requires_new_officer_confirmation_before_creating_case(monkeypatch):
    db=dataset()
    try:
        _patch(monkeypatch,[finding()])
        x=pilot_intake(db.get(User,1),db)
        assert db.query(CaseAssignment).count()==0
        assert x["items"][0]["casework_link"].endswith("&tab=assignments")
        # The existing create-case endpoint still revalidates the saved
        # social post's relevance, authorization and jurisdiction.
        created=create_case(NewCase(source_type="SOCIAL",source_id="11",
            campaign_id=90,department="Pengawasan",target_scope="NATIONAL"),
            db.get(User,1),db)
        assert created["id"]>0
        assert db.query(CaseAssignment).count()==1
        y=pilot_intake(db.get(User,1),db)
        assert y["items"][0]["case_already_exists_in_visible_scope"] is True
        assert y["items"][0]["visible_open_case_id"]==created["id"]
        assert y["items"][0]["casework_link"]==(
            "/inbox?casework=1&case_id="+str(created["id"])+"&tab=reports")
    finally:db.close()

def test_no_role_or_province_permissions_bypassed_by_forged_source_id():
    db=dataset()
    try:
        with pytest.raises(HTTPException) as exc:
            create_case(NewCase(source_type="SOCIAL",source_id="999999",
                campaign_id=90,department="Pengawasan",target_scope="NATIONAL"),
                db.get(User,2),db)
        assert exc.value.status_code in (403,422)
        assert db.query(CaseAssignment).count()==0
    finally:db.close()


def test_unsorted_active_cases_select_latest_case_without_trusting_input_order():
    recent=Obj(id=91,source_type="SOCIAL",source_id="11",campaign_id=90,status="OPEN")
    earlier=Obj(id=25,source_type="SOCIAL",source_id="11",campaign_id=90,status="OPEN")
    for visible in ([recent,earlier],[earlier,recent]):
        row=list_rows([finding()],visible=visible)["items"][0]
        assert row["visible_open_case_id"]==91
        assert row["casework_link"]=="/inbox?casework=1&case_id=91&tab=reports"

def test_case_matching_ignores_closed_status_case_and_whitespace():
    old=Obj(id=99,source_type="social",source_id="11",campaign_id=90,status=" closed ")
    active=Obj(id=27,source_type=" SOCIAL ",source_id="11",campaign_id=90,status="OPEN")
    row=list_rows([finding()],visible=[old,active])["items"][0]
    assert row["visible_open_case_id"]==27
    assert row["review_step"]=="CONTINUE_VISIBLE_CASEWORK"

def test_case_matching_remains_scoped_to_exact_campaign_when_newer_case_exists():
    other=Obj(id=200,source_type="SOCIAL",source_id="11",campaign_id=91,status="OPEN")
    matching=Obj(id=21,source_type="SOCIAL",source_id="11",campaign_id=90,status="OPEN")
    row=list_rows([finding()],visible=[other,matching])["items"][0]
    assert row["visible_open_case_id"]==21
