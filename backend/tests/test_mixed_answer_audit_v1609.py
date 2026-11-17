"""Mixed evidence auditing: all-or-nothing exact permissions and zero model calls."""
import json
import pytest
from fastapi import HTTPException,Response
from app.assistant_eval_sampling import (
    MixedAnswerAuditRequest,build_mixed_answer_audit,resolve_mixed_audit_sources,
    mixed_answer_audit)
from app.models import User
from test_management_briefings_v1468 import dataset

def request(ids=None,answer=None):
    return MixedAnswerAuditRequest(
        source_ids=ids or ["SOCIAL-7","INT-2026-000001","DOC-1-P2"],
        question="Compare saved evidence and applicable law",
        answer=answer or "Public allegations [SOCIAL-7]. Inbox review [INT-2026-000001]. Pasal 21 [DOC-1-P2].")

def evidence():
    return [
      {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING",
       "source_excerpt":"Unverified public allegations about BAWASLU."},
      {"record_id":"INT-2026-000001","record_type":"FORMAL_INTELLIGENCE",
       "source_excerpt":"Inbox evidence record; review status pending."},
      {"record_id":"DOC-1-P2","record_type":"PDF_KNOWLEDGE",
       "source_excerpt":"Pasal 21 describes procedure.",
       "document_type":"REGULATION","review_status":"UNREVIEWED"}]

def test_mixed_audit_includes_source_types_and_no_sensitive_text():
    r=build_mixed_answer_audit(evidence(),request())
    assert r["schema"]=="BAWASLU_MIXED_ANSWER_AUDIT_V1609"
    assert r["profile"]=="CROSS_MODULE_REVIEW"
    assert r["selected_source_kinds"]=={
      "SOCIAL_LISTENING":1,"FORMAL_INTELLIGENCE":1,"PDF_KNOWLEDGE":1}
    assert r["cited_authorized_ids"]==["SOCIAL-7","INT-2026-000001","DOC-1-P2"]
    assert r["missing_cited_source_kinds"]==[]
    assert r["human_accuracy"] is None and not r["source_truth_verified"]
    assert r["database_writes"]==0 and r["paid_ai_calls"]==0
    assert not r["legal_applicability_verified"]
    serialized=json.dumps(r)
    assert "Unverified public allegations about" not in serialized
    assert "Inbox evidence record; review status" not in serialized
    assert "Public allegations [SOCIAL-7]" not in serialized

def test_missing_formal_citation_cannot_pass_source_completeness():
    r=build_mixed_answer_audit(evidence(),request(answer="Discussion [SOCIAL-7]. Law [DOC-1-P2]."))
    assert r["missing_cited_source_kinds"]==["FORMAL_INTELLIGENCE"]
    assert r["review_required_checks"]>=1

def test_formal_only_not_cross_module_profile():
    rows=[evidence()[1]]
    r=build_mixed_answer_audit(rows,request(ids=["INT-2026-000001"],
                                            answer="Saved review [INT-2026-000001]."))
    assert r["profile"]=="SOCIAL_ANALYSIS"

def test_wrong_or_reordered_evidence_rejected():
    with pytest.raises(HTTPException) as err:
        build_mixed_answer_audit(evidence()[:2],request())
    assert err.value.status_code==404

def test_forged_citation_disallowed():
    r=build_mixed_answer_audit(evidence(),request(
        answer="Claims [SOCIAL-999]. Source [DOC-1-P2]."))
    assert r["rejected_unavailable_citation_count"]==1
    assert "SOCIAL-999" not in r["cited_authorized_ids"]

@pytest.mark.parametrize("ids",[
 ["SOCIAL-7","SOCIAL-7"],["SOCIAL-0"],["DOC-0-P1"],
 ["DOC-1-P0"],["INT-abc!"],["SOCIAL-7","SOCIAL-999"],
])
def test_exact_id_validation_and_hidden_denial(monkeypatch,ids):
    from app import assistant_eval_sampling
    from app import inbox_radar
    from app.domain import list_intelligence
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
                            lambda db,p:([{"posts":[{
                              "result_id":"7","canonical_source_id":"social:7",
                              "message_original":"Public report"}]}],{}))
        if ids==["SOCIAL-7","SOCIAL-999"]:
            expected=404
        elif ids==["INT-abc!"]:
            expected=422
        else:
            expected=422
        with pytest.raises(HTTPException) as exc:
            resolve_mixed_audit_sources(db,{"status":"Active","permissions":{"view_intelligence":True}},request(
                ids=ids,answer="Check evidence"))
        assert exc.value.status_code==expected
    finally:db.close()

def test_inaccessible_pdf_page_aborts_entire_request(monkeypatch):
    from app import assistant_eval_sampling
    from app import inbox_radar
    from app import assistant_knowledge
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
            lambda db,p:([{"posts":[{"result_id":"7","canonical_source_id":"social:7",
                                      "message_original":"Public report"}]}],{}))
        monkeypatch.setattr(assistant_knowledge,"retrieve_exact_pdf_pages",lambda *a,**kw:[])
        with pytest.raises(HTTPException) as exc:
            resolve_mixed_audit_sources(db,{"status":"Active","permissions":{"view_intelligence":True}},
                request(ids=["SOCIAL-7","DOC-1-P2"]))
        assert exc.value.status_code==404
    finally:db.close()

def test_endpoint_requires_intelligence_permission(monkeypatch):
    from app import assistant_eval_sampling
    db=dataset()
    try:
        monkeypatch.setattr(assistant_eval_sampling,"profile",
            lambda db,u:{"status":"Active","permissions":{"view_intelligence":False}})
        with pytest.raises(HTTPException) as exc:
            mixed_answer_audit(request(),Response(),db.get(User,2),db)
        assert exc.value.status_code==403
    finally:db.close()

def test_end_to_end_endpoint_authorization_and_cache_headers(monkeypatch):
    from app import assistant_eval_sampling,inbox_radar,assistant_knowledge,domain
    db=dataset()
    try:
        monkeypatch.setattr(assistant_eval_sampling,"profile",
            lambda db,u:{"status":"Active","permissions":{"view_intelligence":True}})
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
            lambda db,p:([{"posts":[{"result_id":"7","canonical_source_id":"social:7",
                                     "message_original":"Public source"}]}],{}))
        monkeypatch.setattr(domain,"list_intelligence",lambda db,p:[])
        monkeypatch.setattr(assistant_knowledge,"retrieve_exact_pdf_pages",lambda *a,**kw:[])
        resp=Response()
        result=mixed_answer_audit(request(ids=["SOCIAL-7"],answer="Public source [SOCIAL-7]"),
                                  resp,db.get(User,2),db)
        assert result["selected_source_count"]==1
        assert resp.headers["Cache-Control"]=="private, no-store"
        assert resp.headers["X-Evaluation-Generation"]=="NONE"
        assert resp.headers["X-Acceptance-Status"]=="PENDING_HUMAN_REVIEW"
    finally:db.close()
