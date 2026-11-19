"""Lexical coverage probe for multi-part assistant questions.

The probe does not establish factual correctness, semantic entailment, or legal
authority. It only flags likely unanswered user-requested topics for review.
"""
import re

TOPICS = {
    "evidence_preservation": (
        r"\b(?:pengamanan\s+bukti|amank(?:an)?\s+bukti|evidence\s+(?:preservation|handling)|chain\s+of\s+custody)\b",
        r"\b(?:bukti|evidence|arsip|archive|preserv|simpan)\b",
    ),
    "fact_verification": (
        r"\b(?:verifikasi\s+fakta|memverifikasi\s+fakta|fact\s+verification|verify\s+facts)\b",
        r"\b(?:verifik|fakta|verify|verification|confirmed|dikonfirmasi)\w*\b",
    ),
    "legal_followup": (
        r"\b(?:tindak\s+lanjut\s+hukum|penanganan\s+hukum|legal\s+follow.up|legal\s+handling)\b",
        r"\b(?:hukum|legal|peraturan|regulasi|statute|otoritas)\b",
    ),
    "platform_moderation": (
        r"\b(?:takedown|take.down|moderasi\s+platform|platform\s+moderation)\b",
        r"\b(?:takedown|take.down|moderasi|platform|penghapusan)\b",
    ),
    "assignment": (
        r"\b(?:penugasan|assignment|routing|penempatan\s+petugas)\b",
        r"\b(?:penugasan|tugas|assign|routing|penanganan\s+provinsi)\w*\b",
    ),
    "role_restrictions": (
        r"\b(?:pembatasan\s+kewenangan|akses\s+pengguna|viewer|role\s+restrictions|access\s+restrictions)\b",
        r"\b(?:viewer|peran|akses|kewenangan|izin|role|permission|otorisasi)\b",
    ),
    "duplicate_prevention": (
        r"\b(?:duplikasi\s+kasus|duplikat|duplicate\s+(?:case|record)|pencegahan\s+duplikasi)\b",
        r"\b(?:duplikat|duplikasi|duplicate|berulang)\b",
    ),
}


# A repeated question or bare citation is not a substantive answer.
_QUESTION_ECHO = re.compile(
    r"^\s*(?:pertanyaan\s+(?:anda|ini)\s*[:：]|you\s+asked\s*[:：])[^\n]*\n?", re.I)
_CITATION_ONLY = re.compile(
    r"^\s*(?:\[(?:DOC-\d+-P\d+|INT-[A-Za-z0-9:_-]+|SOCIAL-[A-Za-z0-9:_-]+)\]\s*)+$")


def _answer_body(answer):
    text = _QUESTION_ECHO.sub("", str(answer or ""), count=1)
    return "\n".join(line for line in text.splitlines()
                     if not _CITATION_ONLY.fullmatch(line))


def requested_topic_coverage(question, answer, profile="PDF_GUIDANCE"):
    """Mark possible omissions; never assert a claim was actually supported."""
    if profile not in ("PDF_GUIDANCE", "CASE_REVIEW", "CROSS_MODULE_REVIEW"):
        return {"status": "NOT_APPLICABLE", "requested_topics": [],
                "missing_topics": [], "lexical_only": True}
    question = str(question or "")
    answer = _answer_body(answer)
    requested = [topic for topic, (req, _) in TOPICS.items()
                 if re.search(req, question, re.I)]
    if len(requested) < 2:
        return {"status": "NOT_APPLICABLE", "requested_topics": requested,
                "missing_topics": [], "lexical_only": True}
    missing = [topic for topic in requested
               if not re.search(TOPICS[topic][1], answer, re.I)]
    return {"status": "NEEDS_REVIEW" if missing else "PASS_LEXICAL_ONLY",
            "requested_topics": requested, "missing_topics": missing,
            "lexical_only": True,
            "note": "Keyword presence does not prove evidence support, correctness, or complete reasoning."}
