"""Objective-specific discovery and evidence diagnostics. No benchmark answer data."""
import re
from urllib.parse import urlsplit

FOCUS = {
    "national statistics": "Satu Data Bawaslu downloadable dataset; Renstra and LKjIP original tables; separate election, year, case status and unit",
    "provincial breakdown": "provincial Bawaslu annual reports, ASN neutrality regional tables, original dataset download links; seek documented partial comparisons if national table inaccessible",
    "candidate cases": "individual MK, DKPP and Bawaslu published decisions, decision number, date, disposition and election; search official decision indexes independently",
    "party accountability": "KPU official nomination or sponsorship decisions, and separate adjudicated organizational liability; do not infer party liability from association",
    "subjects and institutions": "official subject categories, institutional mandate, documented referral outcomes and responsible authority",
    "legal instruments": "JDIH BPK, JDIH KPU, JDIH Bawaslu, official court decisions; retrieve full controlling text and amendments, not commentary",
    "prevention and implementation": "official evaluation, implementation outcomes, institutional weaknesses and practical prevention evidence",
}

def alternate_focus(objective):
    return FOCUS.get(objective, "alternative authoritative institutions, original documents, accessible HTML and independent sources")

def evidence_profile(rows):
    readable = [r for r in rows if r.get("read_status") == "READ"]
    official = [r for r in readable if r.get("kind") == "OFFICIAL"]
    return {
        "read_count": len(readable),
        "official_read_count": len(official),
        "document_read_count": sum(r.get("document_type") in ("PDF","CSV","XLSX") for r in readable),
        "distinct_hosts": len({urlsplit(r.get("resolved_url") or r.get("url") or "").hostname for r in readable if r.get("url")}),
        "failed_read_count": sum(r.get("read_status") != "READ" for r in rows),
    }

def article_numbers(text):
    return set(re.findall(r"\b(?:pasal|article)\s+(\d+[a-z]?)\b", str(text or ""), re.I))

def matching_article(reference, quote):
    requested = {x.casefold() for x in article_numbers(reference)}
    found = {x.casefold() for x in article_numbers(quote)}
    return bool(requested) and requested <= found

def narrative_citation_audit(answer, sources):
    """Coverage signal only: citation presence does not establish entailment."""
    known = {s["id"] for s in sources if s.get("read_status") in ("READ","SAVED_SNAPSHOT")}
    paragraphs = []
    for chunk in re.split(r"\n\s*\n", str(answer or "")):
        chunk = chunk.strip()
        if not chunk or len(chunk) < 100 or chunk.startswith("#") and "\n" not in chunk:
            continue
        refs = set(re.findall(r"\[((?:P|R)-\d+)\]", chunk))
        paragraphs.append(bool(refs & known))
    return {"substantive_blocks": len(paragraphs), "blocks_with_read_source_links": sum(paragraphs),
            "semantic_claim_verification": False}
