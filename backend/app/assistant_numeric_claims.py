"""Offline warning-only check for dates and numeric quantities in legal claims.

Only actually displayed authorized citations to eligible PDF legal pages count.
Literal text presence is not entailment, completeness, or legal currentness.
No DB, network, embeddings, model calls, or side effects.
"""
import re

_REF=re.compile(r"\[(DOC-[0-9]+-P[0-9]+)\]")
_SPAN=re.compile(r"(?<=[.!?;])\s+|\n+")
_DATE_ISO=re.compile(r"(?<![\w-])(?:19|20)\d{2}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])(?![\w-])")
_MONTHS="january february march april may june july august september october november december januari februari maret april mei juni juli agustus september oktober november desember".split()
_DATE_LONG=re.compile(r"(?<!\w)(?:[0-3]?\d)\s+(?:"+"|".join(_MONTHS)+r")\s+(?:19|20)\d{2}(?!\w)",re.I)
# Explicitly bounded units; do not treat article numbers, years, DOC IDs,
# page numbers or ordinary counts as legal claims without clear units.
_QUANTITY=re.compile(
    r"(?<![\w-])(?P<value>\d{1,6}(?:[.,]\d{1,2})?)\s*"
    r"(?P<unit>days?|hari|hours?|jam|months?|bulan|years?|tahun|%|percent|persen)\b",re.I)
_UNIT={
    "day":"day","days":"day","hari":"day",
    "hour":"hour","hours":"hour","jam":"hour",
    "month":"month","months":"month","bulan":"month",
    "year":"year","years":"year","tahun":"year",
    "%":"percent","percent":"percent","persen":"percent",
}
# For percent, \b after '%' fails at punctuation; support it explicitly.
_PERCENT=re.compile(r"(?<![\w-])(?P<value>\d{1,6}(?:[.,]\d{1,2})?)\s*%(?!\w)")
_DATE_INTENT=re.compile(
    r"\b(?:effective|effective date|deadline|due date|expires?|valid from|"
    r"berlaku|tanggal|batas waktu|kedaluwarsa|berakhir|jatuh tempo|"
    r"must|shall|wajib|dilarang|harus|may not|tidak boleh)\b",re.I)
_REPORTED=re.compile(r"^(?:according to|reported(?:ly)?|menurut sumber|mengutip)\b",re.I)

def _facts(value):
    raw=str(value or "")
    dates={re.sub(r"\s+"," ",m.group()).casefold() for m in _DATE_ISO.finditer(raw)}
    dates.update(re.sub(r"\s+"," ",m.group()).casefold() for m in _DATE_LONG.finditer(raw))
    quantities=set()
    for m in _QUANTITY.finditer(raw):
        unit=_UNIT[m.group("unit").casefold()]
        val=m.group("value").replace(",",".")
        quantities.add((str(float(val)).rstrip("0").rstrip(".") if "." in val else str(int(val)),unit))
    for m in _PERCENT.finditer(raw):
        val=m.group("value").replace(",",".")
        quantities.add((str(float(val)).rstrip("0").rstrip(".") if "." in val else str(int(val)),"percent"))
    return dates,quantities

def evaluate_legal_numeric_claims(question,evidence,answer,cited_ids,grounding):
    base={"id":"legal_numeric_claim_source_alignment",
          "method":"EXPLICIT_DATE_AND_QUANTITY_TEXT_PRESENCE_ONLY",
          "semantic_entailment_verified":False,
          "legal_applicability_verified":False,"legal_currentness_verified":False,
          "no_paid_provider_called":True}
    if not (grounding or {}).get("legal_question"):
        return {**base,"status":"NOT_APPLICABLE","checked_claim_spans":0,
                "unsupported_details":[],"unsupported_detail_count":0}
    rows={str(r.get("record_id")):r for r in evidence or []
          if isinstance(r,dict) and r.get("record_id")}
    authorized=set(str(x) for x in cited_ids or [])
    checked=0
    flagged=[]
    spans=_SPAN.split(str(answer or ""))
    for i,span in enumerate(spans):
        plain=_REF.sub("",span).strip()
        if not plain or plain.endswith("?") or _REPORTED.search(plain):
            continue
        claim_dates,claim_quantities=_facts(plain)
        if not claim_dates and not claim_quantities:
            continue
        refs=[r for r in dict.fromkeys(_REF.findall(span)) if r in authorized]
        if not refs and i+1<len(spans):
            next_span=spans[i+1].strip()
            next_refs=_REF.findall(next_span)
            if next_refs and not _REF.sub("",next_span).strip():
                refs=[r for r in dict.fromkeys(next_refs) if r in authorized]
        legal_refs=[r for r in refs if r in rows
                    and rows[r].get("record_type")=="PDF_KNOWLEDGE"
                    and rows[r].get("document_type") in {"REGULATION","SOP","GUIDANCE"}]
        if not legal_refs:
            continue # handled by existing claim-local citation safeguards
        checked+=1
        source_dates=set()
        source_quantities=set()
        for r in legal_refs:
            dates,quantities=_facts(rows[r].get("source_excerpt"))
            source_dates.update(dates)
            source_quantities.update(quantities)
        # Check explicit dates only in a sentence with normative/time intent.
        if _DATE_INTENT.search(plain):
            for date in sorted(claim_dates-source_dates):
                flagged.append({"claim_index":checked,"kind":"DATE",
                                "detail":date,"cited_page_ids":legal_refs,
                                "reason":"DATE_NOT_PRESENT_IN_LOCAL_CITED_EXCERPT"})
        for value,unit in sorted(claim_quantities-source_quantities):
            flagged.append({"claim_index":checked,"kind":"QUANTITY",
                            "detail":value+" "+unit,"cited_page_ids":legal_refs,
                            "reason":"QUANTITY_NOT_PRESENT_IN_LOCAL_CITED_EXCERPT"})
    return {**base,"status":"REVIEW_REQUIRED" if flagged else "NOT_APPLICABLE",
            "checked_claim_spans":checked,"unsupported_details":flagged[:12],
            "unsupported_detail_count":len(flagged)}
