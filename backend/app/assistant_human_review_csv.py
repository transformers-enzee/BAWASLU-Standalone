"""Local CSV officer-review worksheet, bound to saved-answer revision tokens.

CSV files are sensitive operational metadata; never upload to GitHub.
No network, model calls, database writes, or automatic approval.
"""
import argparse
import csv
import io
import json
from pathlib import Path

from .assistant_human_review_template import prepare
from .assistant_human_review_cli import _read_json
from .assistant_human_review_scoring import compile_human_review_scores
from .assistant_saved_reply_human_packet import DIMENSIONS

IDENTITY = ("thread_id", "answer_message_index", "answer_revision_token")
ATTESTATIONS = (
    "source_access_rechecked",
    "source_material_reviewed",
    "original_answer_reviewed",
    "independent_review_attested",
)
COLUMNS = IDENTITY + DIMENSIONS + ATTESTATIONS
MAX_CSV_BYTES = 128 * 1024


def blank_csv(packet):
    rows = prepare(packet)
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for item in rows:
        row = {key: item[key] for key in IDENTITY}
        row.update({dimension: "" for dimension in DIMENSIONS})
        row.update({attestation: "" for attestation in ATTESTATIONS})
        writer.writerow(row)
    return output.getvalue()


def compile_csv(packet, content):
    if not isinstance(content, str) or len(content.encode("utf-8")) > MAX_CSV_BYTES:
        raise ValueError("CSV exceeds allowed size")
    allowed = prepare(packet)
    reader = csv.DictReader(io.StringIO(content, newline=""))
    if reader.fieldnames != list(COLUMNS):
        raise ValueError("Unexpected or duplicate CSV columns")
    rows = list(reader)
    if not 1 <= len(rows) <= 5 or len(rows) != len(allowed):
        raise ValueError("CSV must preserve the authorized selection count")
    submissions = []
    for row, expected in zip(rows, allowed):
        if None in row or any(not isinstance(v, str) for v in row.values()):
            raise ValueError("Malformed CSV fields")
        if (row["thread_id"] != expected["thread_id"] or
            row["answer_message_index"] != str(expected["answer_message_index"]) or
            row["answer_revision_token"] != expected["answer_revision_token"]):
            raise ValueError("CSV source selection or revision changed")
        ratings = {}
        for dimension in DIMENSIONS:
            rating = row[dimension].strip()
            if rating not in ("", "PASS", "FAIL", "NOT_ASSESSABLE"):
                raise ValueError("Invalid officer rating")
            ratings[dimension] = rating or None
        entry = {key: expected[key] for key in IDENTITY}
        entry["ratings"] = ratings
        for field in ATTESTATIONS:
            value = row[field].strip()
            if value not in ("", "YES", "NO"):
                raise ValueError("Attestation values must be YES, NO or blank")
            entry[field] = value == "YES"
        submissions.append(entry)
    return compile_human_review_scores(packet, submissions)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", required=True, type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--blank-csv", type=Path)
    mode.add_argument("--completed-csv", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    packet = _read_json(args.packet)
    if args.blank_csv:
        if args.output:
            parser.error("--output is only for completed CSV scoring")
        if args.blank_csv.resolve() == args.packet.resolve():
            raise ValueError("Cannot overwrite the review packet")
        args.blank_csv.write_text(blank_csv(packet), encoding="utf-8")
        return 0
    if args.output is None:
        parser.error("--output required when scoring completed CSV")
    protected = {args.packet.resolve(), args.completed_csv.resolve()}
    if args.output.resolve() in protected:
        raise ValueError("Cannot overwrite a private review input")
    if args.completed_csv.stat().st_size > MAX_CSV_BYTES:
        raise ValueError("CSV exceeds allowed size")
    report = compile_csv(packet, args.completed_csv.read_text(encoding="utf-8"))
    args.output.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
