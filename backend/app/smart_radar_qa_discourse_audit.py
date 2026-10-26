"""Deterministic, offline discourse-feature audit for Indonesian QA posts.

These features describe *what the post discusses* and its communicative
framing. They are NOT classification rules and are never used to override
Shahrin labels or infer a target's gold category. No provider calls.
"""
import html
import re

# Patterns are interpretable audit signals, not learned categories.
FEATURE_PATTERNS = {
    "court_proceeding": (r"\b(?:mahkamah konstitusi|sidang|persidangan|hakim|phpu|gugatan|perkara|putusan)\b",),
    "explicit_accusation": (r"\b(?:dugaan pelanggaran|kecurangan|konspirasi|rekayasa|terstruktur|manipulasi|pelanggaran|tuduhan)\b",),
    "institutional_process": (r"\b(?:verifikasi|rekrutmen|seleksi|pelantikan|tps|pemungutan suara|tata kelola|penyelenggara pemilu)\b",),
    "inclusive_access": (r"\b(?:disabilitas|lansia|inklusif|aksesibilitas|kelompok rentan)\b",),
    "oversight_action": (r"\b(?:pengawasan bersama|pengawasan partisipatif|pengawas partisipatif|pendampingan|edukasi masyarakat)\b",),
    "information_environment": (r"\b(?:hoaks|disinformasi|ruang digital|percakapan publik|mention|sentimen|media sosial|bermedia)\b",),
    "voter_register": (r"\b(?:pemutakhiran data pemilih|pdpb|daftar pemilih|dpt|dps)\b",),
}
def discourse_features(message):
    text = html.unescape(message or "").lower()
    return tuple(sorted(key for key, patterns in FEATURE_PATTERNS.items()
                        if any(re.search(pattern,text) for pattern in patterns)))

def feature_overlap(target, reference):
    """Diagnostic only: Jaccard feature overlap; empty signatures yield 0."""
    a,b=set(discourse_features(target)),set(discourse_features(reference))
    return round(len(a&b)/len(a|b),4) if a|b else 0.0

def lexical_vs_discourse_audit(targets, exemplars, lexical_scores):
    """Score exemplar ranking without accessing sealed holdout records.

    The target's human label is read *only after* a best reference is chosen.
    Return diagnostics, not a new live selector.
    """
    rows=[]
    for target in targets:
        scored=[]
        for ref in exemplars:
            if ref["qa_id"]==target["qa_id"] or ref.get("source_hash")==target.get("source_hash") or ref.get("source_url")==target.get("source_url"):
                continue
            pair=(target["qa_id"],ref["qa_id"])
            lexical=float(lexical_scores.get(pair,0))
            semantic=feature_overlap(target["message_original"],ref["message_original"])
            scored.append((lexical,semantic,ref["qa_id"],ref["shahrin_category"]))
        if not scored: continue
        lexical_best=max(scored,key=lambda x:(x[0],x[1],x[2]))
        # Use lexical score to break feature ties, NOT the target's label.
        discourse_best=max(scored,key=lambda x:(x[1],x[0],x[2]))
        rows.append({"qa_id":target["qa_id"],
            "lexical_category":lexical_best[3],
            "discourse_category":discourse_best[3],
            "lexical_match":lexical_best[3]==target["shahrin_category"],
            "discourse_match":discourse_best[3]==target["shahrin_category"],
            "discourse_features":discourse_features(target["message_original"])})
    return {"n":len(rows),
        "lexical_hits":sum(x["lexical_match"] for x in rows),
        "discourse_hits":sum(x["discourse_match"] for x in rows),
        "rows":rows,
        "warning":"Exploratory development-cohort diagnostic, NOT holdout accuracy or a deployed classifier"}
