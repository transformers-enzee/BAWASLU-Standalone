"""Local-only human review score compiler for authorized saved Assistant replies.

This command never retrieves evidence, contacts a provider, or verifies the reviewer.
Keep input JSON files on an approved officer workstation, not in CI artifacts.
"""
import argparse
import json
from pathlib import Path
from .assistant_human_review_scoring import compile_human_review_scores

_MAX_INPUT_BYTES = 1024 * 1024

def _read_json(path):
    if path.stat().st_size > _MAX_INPUT_BYTES:
        raise ValueError("Review input exceeds the local size limit")
    return json.loads(path.read_text(encoding="utf-8"))

def run(packet_path, submissions_path, output_path):
    packet = _read_json(Path(packet_path))
    submissions = _read_json(Path(submissions_path))
    result = compile_human_review_scores(packet, submissions)
    output = Path(output_path)
    if output.resolve() in {Path(packet_path).resolve(), Path(submissions_path).resolve()}:
        raise ValueError("Output must not overwrite private review inputs")
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result

def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packet", type=Path, required=True)
    parser.add_argument("--submissions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    run(args.packet, args.submissions, args.output)
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
