"""CSV review is easy to complete but cannot imply verified legal approval."""
import csv
import io
import json
import pytest

from app.assistant_saved_reply_human_packet import (
    build_authorized_saved_reply_review_packet, DIMENSIONS,
)
from app.assistant_human_review_csv import blank_csv, compile_csv, main


def packet():
    return build_authorized_saved_reply_review_packet({
        "selection_method": "EXPLICIT_USER_SELECTED_REPLIES", "requested": 1,
        "results": [{
            "thread_id": "123e4567-e89b-12d3-a456-426614174000",
            "answer_message_index": 3, "answer_revision_token": "a"*64,
            "status": "AUDITED", "answer_text": "PRIVATE ANSWER",
            "response_quality_triage": {
                "status": "NO_DETERMINISTIC_FLAGS", "diagnostics_complete": True,
            },
        }],
    })


def completed(**overrides):
    raw = blank_csv(packet())
    rows = list(csv.DictReader(io.StringIO(raw)))
    row = rows[0]
    row.update({key: "PASS" for key in DIMENSIONS})
    row.update({key: "YES" for key in (
        "source_access_rechecked", "source_material_reviewed",
        "original_answer_reviewed", "independent_review_attested",
    )})
    row.update(overrides)
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=list(row), lineterminator="\n")
    writer.writeheader()
    writer.writerow(row)
    return out.getvalue()


def test_blank_csv_never_contains_answer_or_prepopulated_scores():
    csv_text = blank_csv(packet())
    assert "PRIVATE ANSWER" not in csv_text
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    assert rows[0]["SOURCE_ID_ACCURACY"] == ""
    assert rows[0]["independent_review_attested"] == ""


def test_complete_self_attestation_does_not_approve_release():
    report = compile_csv(packet(), completed())
    assert report["complete_self_attested_reviews"] == 1
    assert report["release_approved"] is False
    assert report["formal_legal_signoff"] is False
    assert report["human_attestation_is_independently_verified"] is False


def test_blank_and_partial_ratings_are_not_complete():
    report = compile_csv(packet(), blank_csv(packet()))
    assert report["complete_self_attested_reviews"] == 0
    report = compile_csv(packet(), completed(CLAIM_EVIDENCE_SUPPORT=""))
    assert report["complete_self_attested_reviews"] == 0


@pytest.mark.parametrize("override", [
    {"answer_revision_token": "b"*64},
    {"thread_id": "00000000-0000-0000-0000-000000000000"},
    {"answer_message_index": "4"},
])
def test_forged_selection_or_revision_rejected(override):
    with pytest.raises(ValueError, match="selection or revision"):
        compile_csv(packet(), completed(**override))


@pytest.mark.parametrize("override", [
    {"SOURCE_ID_ACCURACY": "=HYPERLINK(1)"},
    {"independent_review_attested": "TRUE"},
    {"LEGAL_AND_POLICY_BOUNDARY": "APPROVED"},
])
def test_invalid_rating_and_unexpected_boolean_rejected(override):
    with pytest.raises(ValueError):
        compile_csv(packet(), completed(**override))


def test_extra_columns_or_rows_are_rejected():
    with pytest.raises(ValueError):
        compile_csv(packet(), completed() + "extra,row\n")
    with pytest.raises(ValueError):
        compile_csv(packet(), completed().replace("SOURCE_ID_ACCURACY", "INVALID_FIELD"))


def test_cli_keeps_sensitive_inputs_and_counts_separate(tmp_path):
    p = tmp_path/"packet.json"
    c = tmp_path/"review.csv"
    out = tmp_path/"counts.json"
    p.write_text(json.dumps(packet()), encoding="utf-8")
    assert main(["--packet", str(p), "--blank-csv", str(c)]) == 0
    c.write_text(completed(), encoding="utf-8")
    assert main(["--packet", str(p), "--completed-csv", str(c), "--output", str(out)]) == 0
    assert json.loads(out.read_text(encoding="utf-8"))["release_approved"] is False
    with pytest.raises(ValueError, match="overwrite"):
        main(["--packet", str(p), "--completed-csv", str(c), "--output", str(p)])
