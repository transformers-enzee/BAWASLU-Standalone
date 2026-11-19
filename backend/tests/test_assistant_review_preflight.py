"""Officer preflight must identify review needs without leaking saved-reply data."""
import json
import pytest
from app.assistant_saved_reply_human_packet import build_authorized_saved_reply_review_packet
from app.assistant_review_preflight import preflight, main


def packet():
    return build_authorized_saved_reply_review_packet({
        "selection_method": "EXPLICIT_USER_SELECTED_REPLIES", "requested": 2,
        "results": [
            {
                "thread_id": "123e4567-e89b-12d3-a456-426614174000",
                "answer_message_index": 3, "answer_revision_token": "a"*64,
                "status": "AUDITED", "answer_text": "SECRET PDF ANSWER",
                "selected_source_kinds": {"PDF_KNOWLEDGE": 2, "SOCIAL_LISTENING": 1},
                "response_quality_triage": {"status": "NO_DETERMINISTIC_FLAGS", "diagnostics_complete": True},
            },
            {
                "thread_id": "223e4567-e89b-12d3-a456-426614174000",
                "answer_message_index": 4, "answer_revision_token": "b"*64,
                "status": "AUDITED", "response_quality_triage": {
                    "status": "INCOMPLETE_DIAGNOSTICS", "diagnostics_complete": False,
                },
            },
        ],
    })


def test_preflight_lists_manual_obligations_without_approval():
    result = preflight(packet())
    assert result["review_tasks"] == 2
    assert result["authorized_source_kind_counts"] == {"PDF_KNOWLEDGE": 1, "SOCIAL_LISTENING": 1}
    pending = result["manual_verification_requirements"]
    assert pending["VERIFY_PDF_VERSION_AND_EXACT_PAGE_MANUALLY"] == 1
    assert pending["VERIFY_CROSS_SOURCE_CLAIMS_MANUALLY"] == 1
    assert pending["COMPLETE_DETERMINISTIC_DIAGNOSTICS"] == 1
    assert pending["RECHECK_SOURCE_TYPE_AND_AUTHORIZATION"] == 1
    assert pending["VERIFY_ORIGINAL_ANSWER_AND_CURRENT_SOURCE_ACCESS"] == 2
    assert result["release_approved"] is False
    assert result["real_answer_accuracy_measured"] is False
    raw = json.dumps(result)
    assert "SECRET PDF ANSWER" not in raw
    assert "123e4567" not in raw
    assert "a"*64 not in raw


def test_unbound_revision_rejected_before_summary():
    data = packet()
    data["items"][0]["answer_revision_token"] = None
    with pytest.raises(ValueError, match="Unbound revision"):
        preflight(data)


def test_malformed_source_kinds_rejected():
    data = packet()
    data["items"][0]["authorized_source_kinds"] = ["PDF_KNOWLEDGE", "PRIVATE_TITLE"]
    with pytest.raises(ValueError, match="source kinds"):
        preflight(data)


def test_local_cli_emits_redacted_aggregate(tmp_path):
    source, dest = tmp_path/"private.json", tmp_path/"preflight.json"
    source.write_text(json.dumps(packet()), encoding="utf-8")
    assert main(["--packet", str(source), "--output", str(dest)]) == 0
    report = json.loads(dest.read_text(encoding="utf-8"))
    assert report["review_tasks"] == 2 and not report["officer_acceptance_completed"]
    with pytest.raises(ValueError, match="overwrite"):
        main(["--packet", str(source), "--output", str(source)])
