"""Deterministic output boundaries for source-grounded social answers.

This is not translation, truth verification or semantic claim attribution.
No web, LLM calls, file reads or persistent changes.
"""
import re

_SOCIAL_ID = re.compile(r"(?<![\[A-Za-z0-9_-])(SOCIAL-[0-9]+)(?![\]A-Za-z0-9_-])")
_URL = re.compile(r"https?://[^\s<>]+", re.I)
_PUBLIC = re.compile(r"^\s*(?:Sumber publik|Public sources?|Sources publiques)\s*:", re.I)
_JAVANESE_AMBIGUITY = re.compile(r"\bbawaslune\s+akeh\s+dipateni\b", re.I)
_OVERCONFIDENT = re.compile(
    r"\bBAWASLU\s+(?:banyak\s+)?(?:dibungkam(?:\s+atau\s+menjadi\s+korban)?|menjadi\s+korban|dibunuh)\b",
    re.I,
)
_CAUTION = {
    "id": "Catatan bahasa: Frasa berbahasa Jawa pada unggahan terpilih ambigu dan belum ditafsirkan secara pasti. Petugas perlu memeriksa makna, konteks lengkap, dan unggahan asli sebelum menyimpulkan tuduhan atau sasaran kritik.",
    "en": "Language caution: A Javanese phrase in the selected post is ambiguous. An authorized reviewer must check its meaning, full context and original post before attributing a specific allegation.",
}

def prepare_social_answer(answer, evidence, language="id"):
    """Annotate explicitly named selected IDs and remove unsupported links.

    Never infer citations from topical similarity; only bracket an ID that
    already appears in the answer and is present in authorized evidence.
    Source links remain accessible on their separately rendered source cards.
    """
    selected = {str(r.get("record_id")) for r in evidence or []
                if isinstance(r, dict) and r.get("record_type") == "SOCIAL_LISTENING"}
    allowed_urls = {str(r.get("source_url") or "").strip() for r in evidence or []
                    if isinstance(r, dict) and r.get("source_url")}
    result = []
    removed = 0
    inserted = 0
    for line in str(answer or "").splitlines():
        if _PUBLIC.match(line):
            # Public sources may not be substituted for selected social evidence.
            removed += 1
            continue
        def filter_url(m):
            nonlocal removed
            original = m.group(0)
            token = original.rstrip(".,;)")
            if token in allowed_urls:
                return original
            removed += 1
            return ""
        line = _URL.sub(filter_url, line)
        if not line.strip():
            result.append("")
            continue
        def source_id(m):
            nonlocal inserted
            ident = m.group(1)
            if ident in selected:
                inserted += 1
                return "[" + ident + "]"
            return ident
        result.append(_SOCIAL_ID.sub(source_id, line).rstrip())
    text = "\n".join(result).strip()
    ambiguous = any(_JAVANESE_AMBIGUITY.search(str(r.get("source_excerpt") or ""))
                    for r in evidence or [] if isinstance(r, dict))
    if ambiguous:
        text = _OVERCONFIDENT.sub("disebut dalam frasa Jawa yang belum dapat dipastikan maknanya", text)
        caution = _CAUTION.get(language, _CAUTION["en"])
        if caution not in text:
            text += "\n\n" + caution
    return text, {"inline_id_citations_added": inserted,
                  "unsupported_public_links_removed": removed,
                  "regional_language_review_required": ambiguous}
