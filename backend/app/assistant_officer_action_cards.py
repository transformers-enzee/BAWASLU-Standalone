"""Structured, source-limited officer action proposals for BAWASLU.

No I/O, no AI calls, no case writes, no assignment creation.
Recommendations describe *proposed* roles and verification gates.
"""
import re

ACTION_FIELDS=("reviewing_role","task","evidence_required",
               "expected_output","escalation_condition")
ACTION_ITEM_SCHEMA={
    "type":"object",
    "properties":{
        **{name:{"type":"string"} for name in ACTION_FIELDS},
        "source_ids":{"type":"array","items":{"type":"string"}},
    },
    "required":[*ACTION_FIELDS,"source_ids"],
    "additionalProperties":False,
}
OFFICER_ACTIONS_SCHEMA={"type":"array","items":ACTION_ITEM_SCHEMA}
_SOURCE=re.compile(r"\[([A-Z]+-[A-Za-z0-9:_-]+)\]")
_BARE_SOURCE=re.compile(
    r"(?<![\w-])(?<!\[)(?:SOCIAL-\d+|INT-\d{4}-\d{6}|DOC-\d+-P\d+)(?![\w-])(?!\])",
    re.I,
)

def sanitize_officer_actions(items,permitted,limit=4):
    """Only selected evidence IDs may survive; never manufacture an assignment."""
    allowed={str(x) for x in permitted or []}
    if not isinstance(items,list):
        return []
    final=[]
    for row in items[:max(0,min(int(limit),4))]:
        if not isinstance(row,dict):
            continue
        def clean(v):
            value=v.strip()[:500] if isinstance(v,str) else ""
            value=_SOURCE.sub(
                lambda m:m.group(0) if m.group(1) in allowed else "",
                value)
            # Bracketed and unbracketed official record IDs need identical
            # authorization. Convert permitted bare IDs into visible citations.
            value=_BARE_SOURCE.sub(
                lambda m:"["+m.group(0).upper()+"]"
                if m.group(0).upper() in allowed else "",value)
            # Removing unauthorized IDs can strand commas or joining words.
            # Repair punctuation without inventing replacement evidence.
            value=re.sub(r"\\s*[,;]\\s*[,;](?:\\s*[,;])*",", ",value)
            value=re.sub(r"\\b(?:dan|serta|atau)\\s*(?=[.,;!?](?:\\s|$))","",value,flags=re.I)
            value=re.sub(r"\\b(?:dalam|pada|oleh|dari)\\s*(?=[.,;!?](?:\\s|$))","",value,flags=re.I)
            value=re.sub(r"\\s*[,;]\\s*(?=[.!?])","",value)
            value=re.sub(r"\\s+([,;:.!?])",r"\\1",value)
            value=re.sub(r"\\s{2,}"," ",value)
            return value.strip()
        item={name:clean(row.get(name)) for name in ACTION_FIELDS}
        if not item["task"]:
            continue
        ids=row.get("source_ids")
        if not isinstance(ids,list):
            ids=[]
        item["source_ids"]=list(dict.fromkeys(
            sid for sid in ids if isinstance(sid,str) and sid in allowed))[:3]
        item["draft_only"]=True
        item["assigned_officer"]=None
        item["approved"]=False
        final.append(item)
    return final

def format_officer_action(row,language="id"):
    """Flatten cards into citation-audited visible review steps.

    Format is stable and multilingual, but not a workflow instruction to
    execute an action without officer authorization.
    """
    labels=({
        "reviewing_role":"Tim penelaah (usulan)",
        "task":"Tindakan",
        "evidence_required":"Bukti yang perlu diperiksa",
        "expected_output":"Keluaran",
        "escalation_condition":"Syarat eskalasi / penutupan",
    } if language=="id" else {
        "reviewing_role":"Suggested reviewing team",
        "task":"Review task",
        "evidence_required":"Evidence to obtain",
        "expected_output":"Expected deliverable",
        "escalation_condition":"Escalation / closure gate",
    })
    fallback=("Belum ditentukan; petugas perlu melengkapi."
              if language=="id" else "To be specified by an authorized officer.")
    parts=[]
    for field in ACTION_FIELDS:
        parts.append("**"+labels[field]+":** "+str(row.get(field) or fallback))
    ids=[str(x) for x in row.get("source_ids",[]) if isinstance(x,str)]
    if ids:
        parts.append(" ".join("["+sid+"]" for sid in ids))
    return "\n".join(parts)

def visible_officer_steps(items,language="id"):
    return [format_officer_action(item,language) for item in items or []]

def officer_action_readiness(items, profile, depth, question=""):
    """Structure/readability only, NOT incident truth or legal applicability."""
    from .assistant_officer_action_contract import officer_action_intent
    if (profile in ("PDF_GUIDANCE","EXECUTIVE_REPORT") or
        (not officer_action_intent(question) and
         profile not in ("CASE_REVIEW","ACTION_REQUEST"))):
        return {"status":"NOT_APPLICABLE","actions":0,
                "factually_verified":False,"assignments_created":False}
    minimum=1 if str(depth).upper()=="EXECUTIVE" else 3
    missing=[]
    for index,row in enumerate(items or []):
        for field in ACTION_FIELDS:
            if not str(row.get(field) or "").strip():
                missing.append({"action":index+1,"field":field})
    return {"status":"STRUCTURE_PRESENT_UNVERIFIED"
            if len(items or [])>=minimum and not missing else "REVIEW_REQUIRED",
            "actions":len(items or []),"minimum_actions":minimum,
            "missing_fields":missing,"factually_verified":False,
            "assignments_created":False,"legal_outcome_verified":False,
            "officer_approval":False}
