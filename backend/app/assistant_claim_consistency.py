"""Conservative claim-to-passage polarity review.

This is a narrow lexical check, not full semantic entailment, legal truth,
or a substitute for officer evaluation. Only displayed, authorized,
eligible legal-PDF page citations are considered. No provider calls or IO.
"""
import re

_SOURCE=re.compile(r"\[(DOC-[0-9]+-P[0-9]+)\]")
_SPANS=re.compile(r"(?<=[.!?;])\s+|\n+")
_EN=re.compile(r"\b(?P<modal>must not|shall not|may not|must|shall|may)\s+(?P<action>report|submit|register|disclose|publish|vote|campaign)\b",re.I)
_ID=re.compile(r"\b(?P<modal>tidak wajib|wajib|dilarang|diperbolehkan)\s+(?P<action>melapor|mengunggah|mendaftar|mengumumkan|berkampanye|memilih)\b",re.I)
# May/shall have distinct meanings; only same-action strong positive vs
# explicit negative is triaged. "May" is never treated as mandatory.
_POSITIVE={"must","shall","wajib","diperbolehkan"}
_NEGATIVE={"must not","shall not","may not","tidak wajib","dilarang"}
_EXACT_VERBS={"report":"melapor","register":"mendaftar","campaign":"berkampanye","vote":"memilih"}

def _patterns(value):
    found={}
    for pattern in (_EN,_ID):
        for match in pattern.finditer(str(value or "")):
            modal=" ".join(match.group("modal").casefold().split())
            action=match.group("action").casefold()
            # Do not equate permission with a duty or suggest equivalence of
            # translated concepts. English 'may' has no assertive polarity.
            if modal=="may":
                continue
            polarity="POSITIVE" if modal in _POSITIVE else "NEGATIVE"
            if modal=="diperbolehkan": polarity="PERMITTED"
            if modal=="tidak wajib": polarity="NOT_REQUIRED"
            if polarity not in {"POSITIVE","NEGATIVE","NOT_REQUIRED","PERMITTED"}:
                continue
            key=(action,polarity)
            found[key]=True
    return found

def evaluate_legal_claim_consistency(question,evidence,answer,cited_ids,grounding):
    base={"id":"legal_claim_passage_consistency",
          "method":"NARROW_LEXICAL_POLARITY_NOT_SEMANTIC_ENTAILMENT",
          "semantic_entailment_verified":False,
          "legal_applicability_verified":False,
          "model_calls":0}
    if not (grounding or {}).get("legal_question"):
        return {**base,"status":"NOT_APPLICABLE","checked_claim_spans":0,
                "possible_reversals":[]}
    rows={str(row.get("record_id")):row for row in evidence or []
          if isinstance(row,dict) and row.get("record_id")}
    authorized=set(cited_ids or ())
    flagged=[]
    checked=0
    spans=_SPANS.split(str(answer or ""))
    for i,span in enumerate(spans):
        plain=_SOURCE.sub("",span).strip()
        if not plain or plain.endswith("?"):
            continue
        # Reported speech is not an assistant legal assertion.
        if re.match(r"^(according to|reported(?:ly)?|menurut sumber|mengutip)\b",plain,re.I):
            continue
        claims=_patterns(plain)
        if not claims:
            continue
        refs=[r for r in dict.fromkeys(_SOURCE.findall(span)) if r in authorized]
        if not refs and i+1<len(spans):
            following=spans[i+1].strip()
            next_refs=_SOURCE.findall(following)
            if next_refs and not _SOURCE.sub("",following).strip():
                refs=[r for r in dict.fromkeys(next_refs) if r in authorized]
        eligible=[r for r in refs if r in rows
                  and rows[r].get("record_type")=="PDF_KNOWLEDGE"
                  and rows[r].get("document_type") in {"REGULATION","SOP","GUIDANCE"}]
        if not eligible:
            continue # local-citation check already handles this gap
        checked+=1
        for ref in eligible:
            source=_patterns(rows[ref].get("source_excerpt"))
            for action,claim_polarity in claims:
                source_polarities={pol for act,pol in source if act==action}
                if len(source_polarities)!=1:
                    continue # mixed or absent source wording is uncertain
                source_polarity=next(iter(source_polarities))
                opposite=(claim_polarity=="POSITIVE" and source_polarity in {"NEGATIVE","NOT_REQUIRED"}) or (
                    claim_polarity=="NEGATIVE" and source_polarity in {"POSITIVE","PERMITTED"}) or (
                    claim_polarity=="NOT_REQUIRED" and source_polarity=="POSITIVE") or (
                    claim_polarity=="PERMITTED" and source_polarity=="NEGATIVE")
                if opposite:
                    flagged.append({"claim_index":checked,"cited_page_id":ref,
                                    "action":action,
                                    "claim_polarity":claim_polarity,
                                    "source_polarity":source_polarity,
                                    "reason":"POSSIBLE_MODALITY_REVERSAL_REQUIRES_OFFICER_REVIEW"})
    return {**base,"status":"REVIEW_REQUIRED" if flagged else "NOT_APPLICABLE",
            "checked_claim_spans":checked,"possible_reversals":flagged[:12],
            "possible_reversal_count":len(flagged)}
