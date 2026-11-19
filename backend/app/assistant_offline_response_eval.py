"""Offline Assistant reply-evaluation harness; never generates model responses.

Accepts source-scoped synthetic fixtures or an explicitly supplied, local JSON
response batch. No DB/network access. Results are deterministic warning-detection
metrics only, not BAWASLU legal correctness or real-model answer accuracy.
"""
import json
from collections import Counter
from pathlib import Path

from .assistant_source_claim_requirements import check_source_claim_requirements

_FIXTURE_ROOT=Path(__file__).resolve().parents[1]/"tests"/"fixtures"
_BENCHMARK_FILES=(
    "assistant_multipage_answer_cases.json",
    "assistant_cross_source_reasoning_cases.json",
)
_PASS="PASS_NARROW_LEXICAL_ONLY"
_REVIEW="REVIEW_REQUIRED"


def _normalized_case(case):
    evidence=case.get("authorized_evidence",case.get("documents"))
    requirements=case.get("requirements")
    if not isinstance(case,dict) or not isinstance(evidence,list) or not isinstance(requirements,list):
        raise ValueError("Each case must contain authorized evidence and explicit requirements")
    if not requirements or len(requirements)>12 or len(evidence)>20:
        raise ValueError("Requirement or evidence size outside bounded evaluation limits")
    if not isinstance(case.get("candidate_answer"),str) or len(case["candidate_answer"])>30000:
        raise ValueError("Answer must be bounded text")
    if not isinstance(case.get("candidate_citation_ids"),list):
        raise ValueError("Selected citation IDs must be a list")
    if any(not isinstance(row,dict) or not isinstance(row.get("record_id"),str)
           or len(row.get("source_excerpt") or "")>16000 for row in evidence):
        raise ValueError("Source evidence must be a bounded record list")
    if any(not isinstance(item,dict) for item in requirements):
        raise ValueError("Requirements must be explicit objects")
    return evidence,requirements


def evaluate_record(case):
    evidence,requirements=_normalized_case(case)
    diagnosis=check_source_claim_requirements(
        case["candidate_answer"],requirements,evidence,
        case["candidate_citation_ids"])
    return {
        "case_id":str(case.get("id") or "")[:100],
        "status":diagnosis["status"],
        "review_reasons":sorted({item["reason"] for item in diagnosis["review_items"]}),
        "requirement_count":diagnosis["requirement_count"],
        "not_an_accuracy_score":True,
        "human_review_required":True,
        "source_truth_verified":False,
        "model_answer_accuracy":None,
        "paid_model_calls":0,
    }


def evaluate_batch(cases):
    if not isinstance(cases,list) or not 1<=len(cases)<=500:
        raise ValueError("Batch must contain 1 to 500 records")
    ids=[str(case.get("id") or "") for case in cases if isinstance(case,dict)]
    if len(ids)!=len(cases) or not all(ids) or len(set(ids))!=len(ids):
        raise ValueError("Cases need unique nonempty IDs")
    rows=[evaluate_record(case) for case in cases]
    status=Counter(row["status"] for row in rows)
    reasons=Counter(reason for row in rows for reason in row["review_reasons"])
    # Do not return answer text or source excerpts in reports.
    return {
        "schema":"BAWASLU_OFFLINE_ANSWER_TRIAGE_V1",
        "scope":"DETERMINISTIC_SYNTHETIC_OR_USER_SUPPLIED_RECORDS",
        "case_count":len(rows),
        "status_counts":dict(sorted(status.items())),
        "review_reason_counts":dict(sorted(reasons.items())),
        "results":rows,
        "accuracy_score":None,
        "source_truth_verified":False,
        "semantic_entailment_verified":False,
        "legal_currentness_verified":False,
        "human_gold_scoring_completed":False,
        "model_calls":0,
        "no_network_or_database_access":True,
    }


def load_bundled():
    cases=[]
    for name in _BENCHMARK_FILES:
        data=json.loads((_FIXTURE_ROOT/name).read_text(encoding="utf-8"))
        cases.extend(data["cases"])
    return cases


def main(argv=None):
    import argparse
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input",type=Path,default=None,
                        help="Explicit local JSON file containing a cases array")
    parser.add_argument("--output",type=Path,default=None,
                        help="Optional local JSON report path")
    args=parser.parse_args(argv)
    if args.input is None:
        cases=load_bundled()
    else:
        payload=json.loads(args.input.read_text(encoding="utf-8"))
        cases=payload["cases"] if isinstance(payload,dict) else payload
    report=evaluate_batch(cases)
    text=json.dumps(report,indent=2,sort_keys=True,ensure_ascii=False)+"\n"
    if args.output:
        args.output.write_text(text,encoding="utf-8")
    else:
        print(text,end="")
    return 0


if __name__=="__main__":
    raise SystemExit(main())
