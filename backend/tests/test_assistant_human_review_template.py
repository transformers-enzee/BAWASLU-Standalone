"""Blank human-review forms must never be preapproved or leak answer content."""
import json
import pytest
from app.assistant_saved_reply_human_packet import build_authorized_saved_reply_review_packet, DIMENSIONS
from app.assistant_human_review_template import prepare, main
from app.assistant_human_review_scoring import compile_human_review_scores


def packet():
    data = build_authorized_saved_reply_review_packet({
        "selection_method": "EXPLICIT_USER_SELECTED_REPLIES",
        "requested": 1,
        "results": [{
            "thread_id": "123e4567-e89b-12d3-a456-426614174000",
            "answer_revision_token": "a" * 64,
            "answer_message_index": 3,
            "status": "AUDITED",
            "response_quality_triage": {
                "status": "NO_DETERMINISTIC_FLAGS",
                "diagnostics_complete": True,
            },
            "answer_text": "PRIVATE ANSWER NOT TO EXPORT",
        }],
    })
    data["secret"] = "SECRET SOURCE"
    return data


def test_blank_form_has_no_approval_and_no_raw_content():
    p = packet()
    form = prepare(p)
    assert len(form) == 1
    assert set(form[0]["ratings"]) == set(DIMENSIONS)
    assert all(value is None for value in form[0]["ratings"].values())
    assert not form[0]["source_access_rechecked"]
    assert not form[0]["independent_review_attested"]
    result = compile_human_review_scores(p, form)
    assert result["complete_self_attested_reviews"] == 0
    assert result["release_approved"] is False
    assert "PRIVATE ANSWER" not in json.dumps(form)
    assert "SECRET SOURCE" not in json.dumps(form)


def test_unbound_revision_is_rejected():
    p = packet()
    p["items"][0]["answer_revision_token"] = None
    with pytest.raises(ValueError, match="Unbound revision"):
        prepare(p)


def test_duplicate_task_is_rejected():
    p = packet()
    p["items"].append(dict(p["items"][0]))
    with pytest.raises(ValueError, match="Duplicate"):
        prepare(p)


def test_invalid_packet_scope_is_rejected():
    p = packet()
    p["selection_method"] = "AUTO_SELECTED"
    with pytest.raises(ValueError, match="explicit"):
        prepare(p)


def test_cli_outputs_blank_form_without_overwriting_packet(tmp_path):
    source = tmp_path / "packet.json"
    dest = tmp_path / "submissions.json"
    source.write_text(json.dumps(packet()), encoding="utf-8")
    assert main(["--packet", str(source), "--output", str(dest)]) == 0
    assert json.loads(dest.read_text(encoding="utf-8"))[0]["ratings"]["SOURCE_ID_ACCURACY"] is None
    with pytest.raises(ValueError, match="overwrite"):
        main(["--packet", str(source), "--output", str(source)])
