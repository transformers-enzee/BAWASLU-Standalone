"""Conservative citation assembly across the actual visible Assistant response.

Observations and review steps live in a second UI component. They are still
visible response text and must be included in identifier accounting. This is
not semantic claim verification; no model calls, database I/O or mutations.
"""
from .assistant_grounding import audit_assistant_answer

_SEPARATOR="\n\n__ASSISTANT_VISIBLE_FINDINGS_SEPARATOR_17556__\n"

def visible_assistant_text(answer, findings):
    """Exactly the visible answer sections for zero-credit citation-quality QA.

    Findings are visible even when collapsed in the UI; never silently omit
    their cited identifiers from the post-audit quality evaluator.
    """
    parts=[str(answer or "")]
    for key in ("observations", "review_steps"):
        parts.extend(x for x in ((findings or {}).get(key) or [])
                     if isinstance(x,str) and x.strip())
    return "\n\n".join(parts)

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
    # The grounding layer reports every warning it actually appended. Move
    # ALL such notices to the main visible answer; the final review step may
    # otherwise hide legal, enforcement, or citation warnings in a <details>.
    notes=list(audit.get("appended_safety_notices") or [])
    for note in reversed(notes):
        suffix="\n\n"+note
        if not parts[-1].endswith(suffix):
            raise ValueError("assistant safety-notice integrity mismatch")
        parts[-1]=parts[-1][:-len(suffix)]
    clean_answer=parts[0]
    if notes:
        clean_answer=clean_answer.rstrip()+"\n\n"+"\n\n".join(notes)
    count=len(observations)
    clean_findings={**findings,"observations":parts[1:1+count],
                    "review_steps":parts[1+count:]}
    audit["citation_scope"]="VISIBLE_ANSWER_AND_FINDINGS"
    audit["visible_findings_included"]=len(observations)
    return clean_answer,cited,audit,clean_findings
