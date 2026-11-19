"""Safe offline acceptance snapshot: evidence inventory, never an accuracy score.

Consumes only local JUnit XML and redacted deterministic triage JSON. It never
loads answer/source text, connects to a database, or performs model calls.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def summarize(junit_path: Path, triage_path: Path) -> dict:
    root = ET.parse(junit_path).getroot()
    if root.tag not in ("testsuite", "testsuites"):
        raise ValueError("Not a JUnit test suite")
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    if not suites:
        raise ValueError("No JUnit suites found")
    count = sum(int(s.get("tests", "0")) for s in suites)
    failed = sum(int(s.get("failures", "0")) + int(s.get("errors", "0")) for s in suites)
    skipped = sum(int(s.get("skipped", "0")) for s in suites)
    if count <= 0 or failed < 0 or skipped < 0 or failed + skipped > count:
        raise ValueError("Invalid JUnit test counters")
    triage = json.loads(triage_path.read_text(encoding="utf-8"))
    if triage.get("schema") != "BAWASLU_OFFLINE_ANSWER_TRIAGE_V1":
        raise ValueError("Unexpected triage schema")
    if triage.get("model_calls") != 0 or triage.get("accuracy_score") is not None:
        raise ValueError("Triage cannot claim model or accuracy evaluation")
    if triage.get("human_gold_scoring_completed") is not False:
        raise ValueError("Triage cannot assert human scoring")
    case_count = triage.get("case_count")
    if not isinstance(case_count, int) or isinstance(case_count, bool) or not 1 <= case_count <= 500:
        raise ValueError("Invalid triage case count")
    counts = triage.get("status_counts")
    if not isinstance(counts, dict) or any(
        not isinstance(v, int) or isinstance(v, bool) or v < 0 for v in counts.values()
    ) or sum(counts.values()) != case_count:
        raise ValueError("Triage counts do not reconcile")
    return {
        "schema": "BAWASLU_ASSISTANT_ACCEPTANCE_SNAPSHOT_V1",
        "scope": "OFFLINE_DETERMINISTIC_CI_ONLY",
        "automated_tests": {
            "total": count, "passed": count - failed - skipped, "failed": failed,
            "skipped": skipped, "result": "PASS" if failed == 0 and skipped == 0 else "NOT_PASSED",
        },
        "synthetic_triage": {
            "case_count": case_count, "status_counts": dict(sorted(counts.items())),
            "not_an_accuracy_score": True,
        },
        "real_model_answers_scored": 0,
        "human_gold_scoring_completed": False,
        "real_pdf_source_validation_completed": False,
        "officer_acceptance_completed": False,
        "legal_signoff_completed": False,
        "staging_verified": False,
        "release_approved": False,
        "overall_completion_percentage": None,
        "paid_ai_calls": 0,
        "database_writes": 0,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--triage", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    snapshot = summarize(args.junit, args.triage)
    args.output.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
