"""v158.8 export read-only, permission-scoped, with no acceptance inference."""
import csv
import io
import pytest
from fastapi import HTTPException
from app.assistant_acceptance_evidence import (
    build_evidence_register,render_evidence_register_csv,TRACK_REQUIREMENTS)
from app.assistant_acceptance_readiness import build_acceptance_readiness
from app.assistant_human_review import build_human_review_packet
from app.assistant_eval_sampling import (
    build_evaluation_question_plan,acceptance_evidence_csv)
from app.assistant_legal_benchmark import run_legal_signal_benchmark
from test_assistant_eval_sampling_v1488 import findings
from test_management_briefings_v1468 import dataset
from app.models import User

def ready(n=30):
    plan=build_evaluation_question_plan(findings(n),24)
    return build_acceptance_readiness(build_human_review_packet(plan),
                                      run_legal_signal_benchmark())

def test_register_preserves_pending_statuses_and_synthetic_separation():
    a=ready()
    reg=build_evidence_register(a)
    assert reg["pending_tracks"]==len(a["readiness_gaps"])==5
    assert {r["track"] for r in reg["register_rows"]}==set(TRACK_REQUIREMENTS)-{"EVALUATION_SAMPLE_SHORTFALL"}
    assert reg["recorded_approvals"]==0
    assert reg["human_reviews_completed"]==0
    assert reg["synthetic_checks_are_human_approval"] is False
    assert reg["legal_signoff_complete"] is False
    assert reg["client_acceptance_complete"] is False
    assert reg["database_writes"]==0
    out=render_evidence_register_csv(reg)
    rows=list(csv.DictReader(io.StringIO(out)))
    assert len(rows)==5
    assert all(r["status"]=="PENDING_EXTERNAL_HUMAN_EVIDENCE" for r in rows)
    assert "SOCIAL-" not in out and "https://" not in out

def test_shortfall_is_a_distinct_required_evidence_row():
    reg=build_evidence_register(ready(1))
    assert reg["pending_tracks"]==6
    assert reg["register_rows"][0]["track"]=="EVALUATION_SAMPLE_SHORTFALL"
    assert reg["register_rows"][0]["status"]=="INCOMPLETE_SAMPLE"

def test_rejects_unrecognized_register_tracks():
    with pytest.raises(ValueError):
        build_evidence_register({"readiness_gaps":[{"track":"UNKNOWN"}]})
    with pytest.raises(ValueError):
        render_evidence_register_csv({})

def test_csv_formula_escape():
    reg=build_evidence_register(ready())
    reg["register_rows"][0]["readiness_note"]="=HYPERLINK(1)"
    out=render_evidence_register_csv(reg)
    assert "'=HYPERLINK(1)" in out
    assert "\r\n" in out

def test_admin_only_csv_and_no_store(monkeypatch):
    from app import assistant_eval_sampling,inbox_radar
    db=dataset()
    try:
        monkeypatch.setattr(inbox_radar,"live_inbox_findings",
            lambda connection,principal:(findings(4),{}))
        monkeypatch.setattr(assistant_eval_sampling,"profile",
            lambda conn,user:{"role":"National Administrator","status":"Active",
                              "permissions":{"administration":True,"view_intelligence":True}})
        response=acceptance_evidence_csv(target=24,user=db.get(User,1),db=db)
        assert response.status_code==200
        assert response.headers["Cache-Control"]=="private, no-store"
        assert response.headers["X-Acceptance-Status"]=="PENDING_HUMAN_REVIEW"
        assert b"EVALUATION_SAMPLE_SHORTFALL" in response.body
        assert b"PRIVATE_RAW_MESSAGE" not in response.body
        monkeypatch.setattr(assistant_eval_sampling,"profile",
            lambda conn,user:{"role":"Viewer","status":"Active",
                              "permissions":{"administration":False,"view_intelligence":True}})
        with pytest.raises(HTTPException) as error:
            acceptance_evidence_csv(target=24,user=db.get(User,2),db=db)
        assert error.value.status_code==403
    finally:
        db.close()
