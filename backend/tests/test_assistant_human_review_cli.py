"""Local review CLI must compile counts safely without automated approval."""
import json
import pytest
from app.assistant_saved_reply_human_packet import build_authorized_saved_reply_review_packet, DIMENSIONS
from app.assistant_human_review_cli import run, main

def fixture(tmp_path):
    packet = build_authorized_saved_reply_review_packet({
        "selection_method": "EXPLICIT_USER_SELECTED_REPLIES",
        "requested": 1,
        "results": [{
            "thread_id": "123e4567-e89b-12d3-a456-426614174000",
            "answer_message_index": 3, "answer_revision_token": "a"*64,
            "status": "AUDITED",
            "response_quality_triage": {
                "status": "NO_DETERMINISTIC_FLAGS", "diagnostics_complete": True,
            },
        }],
    })
    p = tmp_path/"packet.json"
    s = tmp_path/"submissions.json"
    p.write_text(json.dumps(packet), encoding="utf-8")
    s.write_text("[]", encoding="utf-8")
    return p, s

def test_empty_submissions_remain_unapproved(tmp_path):
    packet, submissions = fixture(tmp_path)
    output = tmp_path/"report.json"
    assert main(["--packet", str(packet), "--submissions", str(submissions), "--output", str(output)]) == 0
    result = json.loads(output.read_text(encoding="utf-8"))
    assert result["complete_self_attested_reviews"] == 0
    assert result["release_approved"] is False

def test_self_attested_pass_is_not_independent_validation(tmp_path):
    packet, submissions = fixture(tmp_path)
    submission = {
        "thread_id": "123e4567-e89b-12d3-a456-426614174000",
        "answer_message_index": 3, "answer_revision_token": "a"*64,
        "ratings": {name: "PASS" for name in DIMENSIONS},
        "source_access_rechecked": True, "source_material_reviewed": True,
        "original_answer_reviewed": True, "independent_review_attested": True,
        "private_answer": "SECRET ANSWER",
    }
    submissions.write_text(json.dumps([submission]), encoding="utf-8")
    out = tmp_path/"report.json"
    result = run(packet, submissions, out)
    assert result["complete_self_attested_reviews"] == 1
    assert result["release_approved"] is False
    assert result["formal_legal_signoff"] is False
    assert result["human_attestation_is_independently_verified"] is False
    assert "SECRET ANSWER" not in out.read_text(encoding="utf-8")

def test_stale_revision_cannot_count(tmp_path):
    packet, submissions = fixture(tmp_path)
    submissions.write_text(json.dumps([{
        "thread_id": "123e4567-e89b-12d3-a456-426614174000",
        "answer_message_index": 3, "answer_revision_token": "b"*64,
    }]), encoding="utf-8")
    result = run(packet, submissions, tmp_path/"report.json")
    assert result["complete_self_attested_reviews"] == 0
    assert result["release_approved"] is False

def test_reject_overwriting_review_input(tmp_path):
    packet, submissions = fixture(tmp_path)
    with pytest.raises(ValueError, match="overwrite"):
        run(packet, submissions, packet)

def test_reject_oversized_private_input(tmp_path):
    packet, submissions = fixture(tmp_path)
    submissions.write_text("x"*(1024*1024+1), encoding="utf-8")
    with pytest.raises(ValueError, match="size limit"):
        run(packet, submissions, tmp_path/"report.json")
