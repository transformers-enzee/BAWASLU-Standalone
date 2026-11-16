"""Read-only metadata-only evidence register for formal acceptance preparation.

The register is NOT an approval or record of human review. External sign-off
cannot be inferred from runtime QA or synthetic benchmark scores.
"""
from datetime import datetime,timezone
import csv
import io

TRACK_REQUIREMENTS={
 "SOURCE_LINKED_AI_REVIEW":("Independent AI quality reviewer","Reviewer-rated real Assistant answers and verified original sources","AI answer and source verification"),
 "LEGAL_REFERENCE_SIGNOFF":("BAWASLU authorized legal reviewer","Approved reference register with document identity, version and effective dates","Legal approval"),
 "LEGAL_SOURCE_ELECTION_SCOPE":("BAWASLU authorized legal reviewer","Validated Pemilu/Pemilihan applicability and relevant procedural scope","Election-scope approval"),
 "NEGATIVE_CONTROL_REVIEW":("Independent AI quality reviewer","Observed actual response to missing-source control with reviewer decision","Negative control outcome"),
 "FORMAL_CLIENT_ACCEPTANCE":("Authorized BAWASLU client signatory","Signed acceptance decision and documented exceptions","Client acceptance"),
 "EVALUATION_SAMPLE_SHORTFALL":("Evaluation coordinator","Documented sample limitation or additional authorized source coverage","Sampling completeness"),
}
FIELDS=("track","status","responsible_role","required_evidence","required_review","readiness_note")

def build_evidence_register(readiness):
    """Derive a safe handoff register from permission-scoped readiness metadata."""
    if not isinstance(readiness,dict) or not isinstance(readiness.get("readiness_gaps"),list):
        raise ValueError("Valid readiness inventory required")
    rows=[]
    for gap in readiness["readiness_gaps"]:
        if not isinstance(gap,dict) or gap.get("track") not in TRACK_REQUIREMENTS:
            raise ValueError("Unexpected acceptance track")
        name=gap["track"]
        role,evidence,review=TRACK_REQUIREMENTS[name]
        rows.append({"track":name,"status":gap["status"],"responsible_role":role,
                     "required_evidence":evidence,"required_review":review,
                     "readiness_note":gap["required_action"]})
    return {"schema":"BAWASLU_ASSISTANT_ACCEPTANCE_EVIDENCE_REGISTER_V1588",
            "readiness_status":"PREPARATION_ONLY_NOT_FORMAL_ACCEPTANCE",
            "prepared_questions":readiness["prepared_questions"],
            "sample_shortfall":readiness["sample_shortfall"],
            "synthetic_cases":readiness["synthetic_benchmark_scenarios"],
            "synthetic_checks_are_human_approval":False,
            "human_reviews_completed":0,
            "legal_signoff_complete":False,
            "client_acceptance_complete":False,
            "register_rows":rows,"pending_tracks":len(rows),
            "recorded_approvals":0,"database_writes":0,
            "includes_original_posts_or_answer_text":False}

def render_evidence_register_csv(register):
    """CSV export of safe static metadata, guarded against spreadsheet formula injection."""
    if not isinstance(register,dict) or register.get("schema")!="BAWASLU_ASSISTANT_ACCEPTANCE_EVIDENCE_REGISTER_V1588":
        raise ValueError("Invalid acceptance evidence register")
    stream=io.StringIO(newline="")
    writer=csv.DictWriter(stream,fieldnames=FIELDS,extrasaction="ignore",lineterminator="\r\n")
    writer.writeheader()
    for row in register["register_rows"]:
        writer.writerow({k:("'"+v if str(v).lstrip().startswith(("=","+","-","@")) else v)
                         for k,v in row.items() if k in FIELDS})
    return stream.getvalue()
