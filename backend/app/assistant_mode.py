"""SmartRadar assistant analytical mode: workspace mode is separate from output perspective."""
from .assistant_workflows import normalize_workflow_request

MODES={"MANAGEMENT","OPERATIONAL"}
PERSPECTIVES={"AUTO","EXECUTIVE","OPERATIONAL","RESEARCH"}

def mode_contract(payload,grant):
    workspace=str(payload.get("workspaceMode") or "OPERATIONAL").upper()
    # Existing Operations workspace routing uses OPERATIONS, while the analytical
    # mode contract is OPERATIONAL. Normalize only this known legacy alias.
    if workspace=="OPERATIONS":workspace="OPERATIONAL"
    active=str(payload.get("assistantMode") or workspace).upper()
    perspective=str(payload.get("perspective") or "AUTO").upper()
    if workspace not in MODES or active not in MODES or perspective not in PERSPECTIVES:
        raise ValueError("Invalid assistant workspace, active mode or perspective")
    if grant.get("status")!="Active" or grant.get("permissions",{}).get("view_intelligence") is not True:
        raise PermissionError("Assistant intelligence access required")
    role=str(grant.get("role") or "")
    leadership={"National Administrator","National Leadership","Provincial Administrator"}
    if active=="MANAGEMENT" and role not in leadership:
        raise PermissionError("Management mode requires authorized leadership access")
    scope=str(grant.get("geographic_scope") or "")
    return {
        "workspace_mode":workspace,"assistant_mode":active,"perspective":perspective,
        "role":role,"scope":{"geographic_scope":scope,
             "province":str(grant.get("province") or ""),
             "regency_city":str(grant.get("regency_city") or "")},
    }

def mode_directive(config):
    role=config["role"]
    scope=config["scope"]
    prefix=(f"\n\nSMART RADAR OFFICER CONTEXT: access role={role}; "
            f"authorized jurisdiction={scope['geographic_scope']} "
            f"province={scope['province']} regency/city={scope['regency_city']}. "
            "Do not infer rights beyond the retrieved authorized sources. "
            "Answer in the officer's question language. Be politically neutral; apply "
            "the same standards across candidates, offices and parties. "
            "Differentiate allegations, validated source documents, inference and proposals. "
            "Do not claim legal applicability until the election type, location, stage "
            "and controlling official provision have been checked. "
            "Do not fabricate statutory deadlines or decision authority.")
    if config["assistant_mode"]=="MANAGEMENT":
        prefix+=("\nMANAGEMENT WORKFLOW: Lead with the decision or conclusion. "
                 "Explain changes over a known comparison period, their evidentiary basis "
                 "and affected jurisdictions/institutions; never infer trends from a small "
                 "sample. Compare response options and trade-offs, escalation triggers and "
                 "a suggested leadership review date. Recommendations are conditional.")
    else:
        prefix+=("\nOPERATIONAL WORKFLOW: Lead with the first practical officer check. "
                 "Separate evidence, uncertainty, source authenticity and legal-review "
                 "tasks. Identify the office/reviewer role, next handling steps and "
                 "deadlines/authority requiring confirmation; never invent an assignment.")
    perspectives={
        "AUTO":"Choose necessary depth from the question and available evidence.",
        "EXECUTIVE":"Provide a concise leadership-ready conclusion, decisions and risks.",
        "OPERATIONAL":"Emphasize first actions, verification gaps, owner roles and handling checklist.",
        "RESEARCH":"Emphasize traceable sources, contradictory claims, provenance, coverage and gaps."
    }
    return prefix+"\nPERSPECTIVE: "+perspectives[config["perspective"]]


def question_shaped_directive(question):
    """Choose answer presentation, without validating claims or overriding permissions."""
    import re
    q = str(question or "").casefold()
    choices = (
        ("DRAFT", r"\b(draft|memo|email|compose|surat|buatkan|susun memo)\b"),
        ("LEGAL", r"\b(legal|law|regulation|pasal|hukum|pelanggaran|putusan|kewenangan)\b"),
        ("STRATEGY", r"\b(strategy|options|trade.?off|strategi|opsi|taktik|rekomendasi)\b"),
        ("COMPARISON", r"\b(compare|similar|versus|bandingkan|serupa|perbandingan|perbedaan)\b"),
        ("TREND", r"\b(trend|changed|increase|decline|tren|perkembangan|meningkat|menurun)\b"),
    )
    kind = next((name for name, pattern in choices if re.search(pattern, q)), "DIRECT")
    by_kind = {
        "DRAFT": "Lead with the requested memo or email itself. Preserve source citations, caveats and draft-only status through revisions; never claim it was sent.",
        "LEGAL": "Lead with the verified applicable rule or practical first casework step. Identify the election type, stage, jurisdiction, official provision, deadlines and authority only if confirmed; otherwise show what the officer must verify.",
        "STRATEGY": "Compare credible politically neutral options and trade-offs. Recommend a conditional course, owner role, milestone, review point and evidence that would change the decision.",
        "COMPARISON": "Compare relevant sourced examples side by side; cite each example and explain which similarities and differences matter.",
        "TREND": "State what changed, the exact comparison dates, supporting evidence and what to watch. Never infer population trends from saved posts alone.",
        "DIRECT": "Answer plainly and directly, without a compulsory violation-review form or checklist.",
    }
    return (
        "ANSWER-FIRST: In the first two or three sentences give the answer, decision needed, next practical step, or material evidence gap. "
        "Answer in the language of the user's question. Choose the question-specific structure rather than the same casework template for every query. "
        "Cite material factual claims next to the claims using genuinely consulted and authorized sources; never cite a source that was not consulted. "
        "Distinguish independently checked public facts, authorized saved observations, attachments, allegations, interpretations and recommendations. "
        "If current public research was needed but unavailable, state that gap up front rather than presenting model knowledge as verified live news. "
        "Explain implications and choices to leadership, but actionable checks, evidence needs and reviewing roles to officers. "
        "Do not invent deadlines, legal authority, findings, named assignees or jurisdiction. "
        "Keep the main answer concise (approximately 120-260 words unless a long draft or deeper analysis is requested). "
        "Show each finding and recommendation once; avoid boilerplate and repeated action plans. "
        "Keep source consultation, extended charts, methods and full verification inventories in the expandable Research Trail. "
        + by_kind[kind]
    )
