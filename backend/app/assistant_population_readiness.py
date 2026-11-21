"""Deterministic, no-credit diagnostic for population sentiment claims.

This is not a semantic/factual-verification model. It only checks explicit
sentiment percentages and obvious completion claims against a previously
computed authorized population snapshot. Never use it as legal approval.
"""
import re

_LABELS={
    "NEGATIVE":r"(?:negatif|negative)",
    "NEUTRAL":r"(?:netral|neutral)",
    "POSITIVE":r"(?:positif|positive)",
    "UNKNOWN":r"(?:tidak\s+terklasifikasi|belum\s+diklasifikasi|unclassified|unknown)",
}
_PERCENT=r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%"
_HYPOTHETICAL=re.compile(r"\b(?:contoh|misalnya|andaikan|hipotetis|skenario|hypothetical|example|scenario)\b",re.I)
_FALSE_COMPLETE=re.compile(
    r"\b(?:seluruh\s+(?:data|rekaman|unggahan)|semua\s+rekaman|"
    r"complete\s+dataset|entire\s+dataset|all\s+saved\s+posts)\b",re.I)

def evaluate_population_statistics_answer(answer,snapshot):
    if not isinstance(snapshot,dict) or not isinstance(snapshot.get("sentiment_percentages"),dict):
        return {"status":"NOT_APPLICABLE","checked_shares":0,
                "mismatches":[],"population_complete":None,
                "factual_truth_verified":False,"paid_provider_called":False}
    expected=snapshot["sentiment_percentages"]
    matched=int(snapshot.get("statistics_post_count") or snapshot.get("social_posts") or 0)
    complete=snapshot.get("population_complete") is True
    checked=[]
    problems=[]
    lines=str(answer or "").splitlines()[:180]
    for line in lines:
        if _HYPOTHETICAL.search(line):
            continue
        for label,alias in _LABELS.items():
            if label not in expected:continue
            # Label: 145 (47.2%) OR 47,2% negatif.
            candidates=[
                re.search(r"\b"+alias+r"\b[^\n%]{0,65}?"+_PERCENT,line,re.I),
                re.search(_PERCENT+r"[^\n%]{0,40}?\b"+alias+r"\b",line,re.I),
            ]
            for found in candidates:
                if not found:continue
                stated=float(found.group(1).replace(",","."))
                checked.append({"label":label,"stated":stated})
                if matched>0 and abs(stated-float(expected[label]))>0.55:
                    problems.append({"label":label,"stated":stated,
                                     "computed":expected[label]})
                break
    if not complete and _FALSE_COMPLETE.search(str(answer or "")):
        problems.append({"scope":"partial_scan_claimed_complete"})
    return {
        "status":"REVIEW_REQUIRED" if problems else "PASS_LEXICAL_ONLY" if checked else "NOT_APPLICABLE",
        "checked_shares":len(checked),
        "mismatches":problems[:10],
        "population_complete":complete,
        "statistics_post_count":matched,
        "factual_truth_verified":False,
        "paid_provider_called":False,
    }
