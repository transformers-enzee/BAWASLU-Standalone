"""Unambiguous acceptance readiness: preparatory evidence is not sign-off.

Pure, deterministic summary of the existing authorized review packet and
developer-only synthetic legal benchmark. No model runs or database writes.
"""
REQUIRED_TRACKS=(
    ("SOURCE_LINKED_AI_REVIEW","Independent reviewers must score actual generated answers against original authorized sources."),
    ("LEGAL_REFERENCE_SIGNOFF","A designated legal authority must verify current applicable regulations, versions and article references."),
    ("LEGAL_SOURCE_ELECTION_SCOPE","Legal authority must confirm applicable Pemilu/Pemilihan jurisdiction and procedure for reviewed advice."),
    ("NEGATIVE_CONTROL_REVIEW","A human reviewer must verify the Assistant abstains on a missing source."),
    ("FORMAL_CLIENT_ACCEPTANCE","BAWASLU must formally accept the reviewed end-to-end system and outstanding limitations."),
)

def build_acceptance_readiness(packet,synthetic):
    """Expose only counts, evidence gaps and status, never saved post text."""
    if not isinstance(packet,dict) or not isinstance(packet.get("review_items"),list):
        raise ValueError("A valid prepared review packet is required")
    if not isinstance(synthetic,dict) or "number_of_cases" not in synthetic:
        raise ValueError("A synthetic benchmark summary is required")
    count=len(packet["review_items"])
    categories=sorted({str(r.get("category","")) for r in packet["review_items"]
                       if isinstance(r,dict) and r.get("category")})
    all_gaps=[
        {"track":code,"status":"PENDING_EXTERNAL_HUMAN_EVIDENCE","required_action":action}
        for code,action in REQUIRED_TRACKS
    ]
    if packet.get("shortfall",0):
        all_gaps.insert(0,{
            "track":"EVALUATION_SAMPLE_SHORTFALL",
            "status":"INCOMPLETE_SAMPLE",
            "required_action":"Obtain additional eligible authorized source links or document the sampling limitations.",
        })
    return {
        "schema":"BAWASLU_ASSISTANT_ACCEPTANCE_READINESS_V1587",
        "status":"PREPARATION_ONLY_NOT_FORMAL_ACCEPTANCE",
        "human_review_packet_ready":True,
        "prepared_questions":count,
        "target_questions":packet.get("target_questions"),
        "sample_shortfall":packet.get("shortfall"),
        "covered_categories":categories,
        "negative_control_prepared":bool(packet.get("negative_control")),
        "synthetic_benchmark_scenarios":synthetic["number_of_cases"],
        "synthetic_case_checks_failed":synthetic.get("case_checks_failed"),
        "synthetic_benchmark_is_real_model_accuracy":False,
        "real_model_answers_reviewed":0,
        "human_accuracy_measured":False,
        "legal_reference_signoff_complete":False,
        "formal_client_acceptance_complete":False,
        "readiness_gaps":all_gaps,
        "gaps_remaining":len(all_gaps),
        "no_case_or_report_text":True,
        "automatic_legal_outcomes":False,
        "database_writes":0,
        "paid_ai_calls":0,
    }
