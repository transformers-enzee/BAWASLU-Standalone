"""Local, redacted preflight for explicitly authorized saved-answer officer review.

This is a readiness checklist, not an accuracy test, legal verdict, or approval.
It never fetches answer text, accesses the DB, or emits saved-answer identifiers.
"""
import argparse
import json
from collections import Counter
from pathlib import Path

from .assistant_human_review_cli import _read_json
from .assistant_human_review_template import prepare

KNOWN_KINDS = {"PDF_KNOWLEDGE", "SOCIAL_LISTENING", "FORMAL_INTELLIGENCE"}


def preflight(packet):
    prepared = prepare(packet)
    tasks = packet["items"]
    if len(tasks) != len(prepared):
        raise ValueError("Packet and authorized selection mismatch")
    source_counts = Counter()
    blocked = Counter()
    for task in tasks:
        kinds = task.get("authorized_source_kinds")
        if not isinstance(kinds, list) or any(
            not isinstance(kind, str) or kind not in KNOWN_KINDS for kind in kinds
        ) or len(kinds) != len(set(kinds)):
            raise ValueError("Invalid source kinds in packet")
        source_counts.update(kinds)
        if not kinds:
            blocked["RECHECK_SOURCE_TYPE_AND_AUTHORIZATION"] += 1
        if task.get("diagnostics_complete") is not True:
            blocked["COMPLETE_DETERMINISTIC_DIAGNOSTICS"] += 1
        if "PDF_KNOWLEDGE" in kinds:
            blocked["VERIFY_PDF_VERSION_AND_EXACT_PAGE_MANUALLY"] += 1
        if len(kinds) > 1:
            blocked["VERIFY_CROSS_SOURCE_CLAIMS_MANUALLY"] += 1
        blocked["VERIFY_ORIGINAL_ANSWER_AND_CURRENT_SOURCE_ACCESS"] += 1
    return {
        "schema": "BAWASLU_LOCAL_OFFICER_PREFLIGHT_V1",
        "review_tasks": len(tasks),
        "authorized_source_kind_counts": dict(sorted(source_counts.items())),
        "manual_verification_requirements": dict(sorted(blocked.items())),
        "all_review_ratings_blank": True,
        "real_answer_accuracy_measured": False,
        "reviewer_independence_verified": False,
        "formal_legal_signoff": False,
        "officer_acceptance_completed": False,
        "release_approved": False,
        "paid_model_calls": 0,
        "database_writes": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    if args.packet.resolve() == args.output.resolve():
        raise ValueError("Cannot overwrite private review input")
    result = preflight(_read_json(args.packet))
    args.output.write_text(json.dumps(result, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
