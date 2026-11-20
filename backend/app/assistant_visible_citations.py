"""Conservative citation assembly across the actual visible Assistant response.

Observations and review steps live in a second UI component. They are still
visible response text and must be included in identifier accounting. This is
not semantic claim verification; no model calls, database I/O or mutations.
"""
from .assistant_grounding import audit_assistant_answer

_SEPARATOR="\n\n__ASSISTANT_VISIBLE_FINDINGS_SEPARATOR_17556__\n"

def audit_visible_assistant_parts(question, evidence, answer, model_cited_ids,
                                  findings, profile="SOCIAL_ANALYSIS", language="id"):
    observations=[x for x in ((findings or {}).get("observations") or [])
                  if isinstance(x,str) and x.strip()]
    steps=[x for x in ((findings or {}).get("review_steps") or [])
           if isinstance(x,str) and x.strip()]
    if not observations and not steps:
        text,cited,audit=audit_assistant_answer(
            question,evidence,answer,model_cited_ids,profile=profile,language=language)
        return text,cited,audit,findings
    # Serialize as visible sections and audit once against the same authorized
    # evidence. Source references never acquire permission through this helper.
    pieces=[str(answer or ""),*observations,*steps]
    combined=_SEPARATOR.join(pieces)
    checked,cited,audit=audit_assistant_answer(
        question,evidence,combined,model_cited_ids,profile=profile,language=language)
    parts=checked.split(_SEPARATOR)
    if len(parts)!=len(pieces):
        raise ValueError("assistant visible-section integrity mismatch")
    # Audit cautions appended to the final section should appear in the answer
    # (before it), not be hidden inside the verification checklist.
    last=parts[-1]
    notes=[]
    for message in ("Catatan bukti:","Evidence note:"):
        offset=last.find("\n\n"+message)
        if offset>=0:
            notes.append(last[offset+2:])
            parts[-1]=last[:offset]
            break
    clean_answer=parts[0]
    if notes:
        clean_answer=clean_answer.rstrip()+"\n\n"+"\n\n".join(notes)
    count=len(observations)
    clean_findings={**findings,"observations":parts[1:1+count],
                    "review_steps":parts[1+count:]}
    audit["citation_scope"]="VISIBLE_ANSWER_AND_FINDINGS"
    audit["visible_findings_included"]=len(observations)
    return clean_answer,cited,audit,clean_findings
