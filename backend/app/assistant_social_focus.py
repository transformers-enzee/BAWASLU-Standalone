"""Keep assistant social summaries focused on the actual user question.

These are display filters over already permission-scoped, evidence-checked
signals. They do not alter assessments or make legal determinations.
"""
import re
from .processing_hints import CANDIDATE_ALIASES

_GEO=re.compile(r"\b(?:provinsi|province|provincial|daerah|wilayah|"
                r"locus|lokasi kejadian|geographic|geografi|jurisdiction|yurisdiksi|"
                r"where|di mana|riau|sumatera|jakarta|jawa|kalimantan|sulawesi|bali)\b",re.I)
_LEGAL=re.compile(r"\b(?:pelanggaran|violation|violations|investigasi|"
                  r"kasus|case|sengketa|legal|hukum|dugaan|"
                  r"investigation|illegal|offense)\b",re.I)
_DOCUMENT=re.compile(r"\b(?:pdf|dokumen|document|sop|pedoman|manual|"
                     r"rujukan|reference|panduan|aturan)\b",re.I)
_GENERIC_LABELS={"institutional issues","electoral operations",
                 "requires review","screening needed","potential violation review",
                 "indikasi awal","isu kelembagaan"}
_TYPES=("CANDIDATE","SUSPECTED_VIOLATION","ELECTORAL_ISSUE",
        "BAWASLU_ISSUE","PROVINCE")


def query_candidates(question):
    q=str(question or "").casefold()
    names=set()
    for canonical,aliases in CANDIDATE_ALIASES.items():
        for alias in set(aliases)|{canonical}:
            a=str(alias).casefold().strip()
            if len(a)>=4 and re.search(r"(?<!\w)"+re.escape(a)+r"(?!\w)",q):
                names.add(canonical.casefold())
                break
    return names


def question_mentions_pdf(question):
    return bool(_DOCUMENT.search(str(question or "")))


def focus_social_tags(tags,question,allowed_ids=(),limit=4):
    """No unrequested co-mentioned candidates, provinces or generic flags."""
    question=str(question or "")
    focus_candidates=query_candidates(question)
    geo=bool(_GEO.search(question))
    legal=bool(_LEGAL.search(question))
    allowed=set(allowed_ids or [])
    accepted=[]
    for tag in tags or []:
        if not isinstance(tag,dict) or tag.get("type") not in _TYPES:
            continue
        kind=tag["type"]
        name=str(tag.get("label") or "").strip()
        if not name or name.casefold() in _GENERIC_LABELS:
            continue
        ids=[str(rid) for rid in tag.get("source_ids") or [] if str(rid) in allowed]
        if not ids:
            continue
        if kind=="CANDIDATE" and focus_candidates and name.casefold() not in focus_candidates:
            continue
        if kind=="PROVINCE" and not geo:
            continue
        if kind=="SUSPECTED_VIOLATION" and not legal:
            continue
        if kind in ("BAWASLU_ISSUE","ELECTORAL_ISSUE") and name.casefold() in {
                "institutional issues","electoral operations","electoral issue",
                "bawaslu reputation","public concern"}:
            continue
        accepted.append({**tag,"source_ids":ids[:3]})
    # Favour directly named actors and cited evidence; do not fill the UI with
    # every co-mentioned name and the generic rule-based labels.
    accepted.sort(key=lambda item: (
        0 if item["type"]=="CANDIDATE" and focus_candidates else 1,
        0 if item.get("confidence")=="HIGH" else 1,
        _TYPES.index(item["type"])))
    result=[]
    seen=set()
    per_type={}
    for item in accepted:
        key=(item["type"],item["label"].casefold())
        if key in seen or per_type.get(item["type"],0)>=(2 if item["type"]=="CANDIDATE" and not focus_candidates else 1):
            continue
        seen.add(key)
        per_type[item["type"]]=per_type.get(item["type"],0)+1
        result.append(item)
        if len(result)>=limit:
            break
    return result


def source_cards_for_question(chosen_social,cited,view,limit=4,distinct_content=False):
    """Choose source cards among the same records the model actually read."""
    cited_set={str(x) for x in cited or []}
    matching=[row for row in chosen_social if "SOCIAL-"+str(row.get("id")) in cited_set]
    remainder=[row for row in chosen_social if "SOCIAL-"+str(row.get("id")) not in cited_set]
    if not distinct_content:
        return [view(row) for row in (matching+remainder)[:max(0,limit)]]
    # Case reviews prefer distinct story text over syndicated cross-platform copies.
    cards=[]
    seen=set()
    for row in matching+remainder:
        body=re.sub(r"\W+"," ",str(row.get("text_content") or "").casefold()).strip()
        fingerprint=body[:140] if len(body)>=50 else "source:"+str(row.get("id"))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        cards.append(view(row))
        if len(cards)>=max(0,limit):
            break
    return cards
