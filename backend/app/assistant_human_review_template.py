"""Generate a blank, redacted officer rating form from an authorized review packet.

Local-only. No generation, DB access, model scoring, or authenticity claims.
Each answer must be opened by an authorized reviewer against its original sources.
"""
import argparse
import json
import re
from pathlib import Path

from .assistant_saved_reply_human_packet import DIMENSIONS
from .assistant_human_review_cli import _read_json

_UUID = re.compile(r"^[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$")
_REVISION = re.compile(r"^[0-9a-f]{64}$")


def prepare(packet):
    if not isinstance(packet, dict) or packet.get("schema") != "BAWASLU_AUTHORIZED_SAVED_REPLY_REVIEW_PACKET_V17488":
        raise ValueError("An authorized saved-reply review packet is required")
    if packet.get("selection_method") != "EXPLICIT_USER_SELECTED_REPLIES":
        raise ValueError("Review packets must use explicit saved-reply selection")
    items = packet.get("items")
    if not isinstance(items, list) or not 1 <= len(items) <= 5:
        raise ValueError("Expected one to five authorized review tasks")
    submissions = []
    seen = set()
    for task in items:
        if not isinstance(task, dict):
            raise ValueError("Invalid review task")
        thread_id, index, token = (
            task.get("thread_id"), task.get("answer_message_index"),
            task.get("answer_revision_token"),
        )
        if (not isinstance(thread_id, str) or not _UUID.fullmatch(thread_id)
            or not isinstance(index, int) or isinstance(index, bool) or not 1 <= index <= 59):
            raise ValueError("Invalid saved-answer identifier")
        if not isinstance(token, str) or not _REVISION.fullmatch(token):
            raise ValueError("Unbound revision; refresh the authorized review packet")
        key = thread_id.lower(), index
        if key in seen:
            raise ValueError("Duplicate saved-answer selection")
        seen.add(key)
        submissions.append({
            "thread_id": thread_id,
            "answer_message_index": index,
            "answer_revision_token": token,
            "ratings": {dimension: None for dimension in DIMENSIONS},
            "source_access_rechecked": False,
            "source_material_reviewed": False,
            "original_answer_reviewed": False,
            "independent_review_attested": False,
        })
    return submissions


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.packet.resolve() == args.output.resolve():
        raise ValueError("Do not overwrite the original review packet")
    submission = prepare(_read_json(args.packet))
    args.output.write_text(
        json.dumps(submission, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
