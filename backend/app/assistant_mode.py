"""SmartRadar assistant analytical mode: workspace mode is separate from output perspective."""
from .assistant_workflows import normalize_workflow_request

MODES={"MANAGEMENT","OPERATIONAL"}
PERSPECTIVES={"AUTO","EXECUTIVE","OPERATIONAL","RESEARCH"}

def mode_contract(payload,grant):
    workspace=str(payload.get("workspaceMode") or "OPERATIONAL").upper()
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
