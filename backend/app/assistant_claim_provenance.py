"""Narrow provenance triage for *formal outcome* claims citing social posts.

A social listening post can document what someone said, but cannot by itself
certify that BAWASLU formally adjudicated or confirmed a violation. This
warning is only about evidence type, not the existence of a real decision.
"""
import re

_REF=re.compile(r"\[((?:INT|SOCIAL)-[A-Za-z0-9:_-]+|DOC-[0-9]+-P[0-9]+)\]")
_SPANS=re.compile(r"(?<=[.!?;])\s+|\n+")
_FORMAL_EN=re.compile(
    r"\bBAWASLU\s+(?:(?:has|had)\s+)?(?:(?:officially|formally)\s+)?"
    r"(?:confirmed|validated|determined|established|verified)\s+"
    r"(?:an?\s+|the\s+)?(?:electoral\s+|election\s+|legal\s+)?"
    r"(?:violation|offen[sc]e)\b",re.I)
_FORMAL_ID=re.compile(
    r"\bBAWASLU\s+(?:telah\s+)?(?:secara\s+resmi\s+)?"
    r"(?:menetapkan|memastikan|mengonfirmasi|menyatakan)\s+"
    r"(?:adanya\s+|suatu\s+)?pelanggaran\b",re.I)
_HEDGE=re.compile(r"\b(?:alleged|reportedly|claims?|possibly|potential(?:ly)?|"
    r"may|might|could|diduga|dugaan|berpotensi|menurut|diklaim|"
    r"belum\s+terverifikasi)\b",re.I)
_REPORTED=re.compile(r"^(?:according\s+to|reported(?:ly)?|menurut\s+sumber|"
    r"mengutip|dilaporkan|[\"'“‘])",re.I)

def evaluate_claim_provenance(evidence,answer,cited_ids):
    base={"id":"formal_outcome_source_provenance",
          "method":"EXPLICIT_FORMAL_DECISION_PHRASE_AND_LOCAL_SOURCE_TYPE",
          "status":"NOT_APPLICABLE","review_required_count":0,"review_items":[],
          "formal_decision_verified":False,
          "social_source_truth_verified":False,
          "semantic_entailment_verified":False,
          "no_paid_provider_called":True}
    records={str(row.get("record_id")):row for row in evidence or []
             if isinstance(row,dict) and row.get("record_id")}
    authorized=set(str(x) for x in cited_ids or [] if str(x) in records)
    spans=_SPANS.split(str(answer or ""))
    flagged=[]
    for i,span in enumerate(spans):
        plain=_REF.sub("",span).strip()
        if not plain or plain.endswith("?") or _HEDGE.search(plain) or _REPORTED.search(plain):
            continue
        if not (_FORMAL_EN.search(plain) or _FORMAL_ID.search(plain)):
            continue
        refs=list(dict.fromkeys(r for r in _REF.findall(span) if r in authorized))
        if not refs and i+1<len(spans):
            next_text=spans[i+1].strip()
            next_refs=_REF.findall(next_text)
            if next_refs and not _REF.sub("",next_text).strip():
                refs=list(dict.fromkeys(r for r in next_refs if r in authorized))
        # A definitive formal decision requires a claim-local formal record.
        # Neither an uncited assertion, a social post, nor a general legal PDF
        # can establish an actual completed adjudication. Even formal records
        # are only candidate sources until an officer checks their contents.
        source_kinds={records[ref].get("record_type") for ref in refs}
        formal_refs=[ref for ref in refs
                     if records[ref].get("record_type")=="FORMAL_INTELLIGENCE"]
        if not refs:
            flagged.append({"claim_index":i+1,"cited_social_ids":[],
                            "reason":"FORMAL_DECISION_NO_LOCAL_AUTHORIZED_CITATION"})
        elif not formal_refs:
            flagged.append({"claim_index":i+1,
                            "cited_social_ids":[ref for ref in refs
                                if records[ref].get("record_type")=="SOCIAL_LISTENING"][:12],
                            "reason":("FORMAL_DECISION_CITED_ONLY_TO_SOCIAL_POSTS"
                                      if source_kinds=={"SOCIAL_LISTENING"}
                                      else "FORMAL_DECISION_MISSING_FORMAL_RECORD")})
    return {**base,"status":"REVIEW_REQUIRED" if flagged else "NOT_APPLICABLE",
            "review_required_count":len(flagged),"review_items":flagged[:12]}
