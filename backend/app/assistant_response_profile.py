"""Choose the smallest useful assistant answer layout without consuming AI tokens.

Only source-authorized PDF passages may drive PDF_GUIDANCE. An attached PDF
does not turn an unrelated social-intelligence request into a document answer.
"""
import re

PDF_GUIDANCE="PDF_GUIDANCE"
SOCIAL_ANALYSIS="SOCIAL_ANALYSIS"
CASE_REVIEW="CASE_REVIEW"
CROSS_MODULE_REVIEW="CROSS_MODULE_REVIEW"
ACTION_REQUEST="ACTION_REQUEST"
GENERAL="GENERAL"

_PDF=re.compile(
    r"\b(?:pdf|dokumen|document|reference|referensi|rujukan|lampiran|"
    r"uploaded|diunggah|terunggah|manual|sop|pedoman)\b",re.I)
_PROCEDURE=re.compile(
    r"\b(?:prosedur|proses|procedure|process|workflow|alur|langkah|steps?|"
    r"tindak lanjut|follow.up|takedown|take.down|penghapusan|"
    r"penugasan|assignments?|routing|locus|yurisdiksi|jurisdiction|"
    r"kewenangan|authority|kebijakan|regulations?|peraturan|"
    r"pedoman|mekanisme|formulir|form.sim|pelaporan|"
    r"penanganan|verification|verifikasi)\b",re.I)
_SOCIAL=re.compile(
    r"\b(?:sentimen|sentiment|trends?|tren|narratives?|narasi|"
    r"perbincangan|percakapan|conversation volume|engagement|"
    r"interaksi|popularitas|mentions?|sebutan|"
    r"data sosial|social listening|social media analytics|"
    r"statistik|statistics|analisis audiens|audience analysis|"
    r"pie chart|grafik|charts?|berapa unggahan|"
    r"how many posts?|top posts?|platform distribution)\b",re.I)
_ACTION=re.compile(
    r"(?:\b(?:tugaskan|alihkan|buat(?:kan)?\s+(?:penugasan|tugas|laporan|draf|draft)|"
    r"(?:siapkan|susun|susunkan|buatkan|persiapkan)\s+(?:sebuah\s+)?(?:penugasan|tugas|laporan|draf|draft)|"
    r"assign\s+(?:this|these|a case|the case|to)|"
    r"transfer\s+(?:this|the case|to)|"
    r"(?:draft|prepare|create)\s+(?:a|the|my)?\s*report)\b)",re.I)
_ABOUT_DOCUMENT=re.compile(
    r"(?:menurut|berdasarkan|dalam|dari|according to|from|in)\s+"
    r"(?:the\s+)?(?:pdf|dokumen|document|sop|pedoman|referensi)\b",re.I)
_CASE=re.compile(
    r"\b(?:investigasi|investigate|selidiki|investigation|"
    r"periksa\s+(?:kasus|unggahan|bukti)|review\s+(?:this|the)\s+(?:case|post)|"
    r"dugaan pelanggaran\s+(?:oleh|pada|terhadap)|"
    r"kasus\s*#?\d+|post\s*#?\d+)\b",re.I)
_CROSS_MODULE=re.compile(
    r"\b(?:bandingkan|perbandingan|komparasi|compare|comparison|comparative|"
    r"lintas.modul|cross.module|konsistensi|persamaan|perbedaan|"
    r"similarities|differences)\b",re.I)

_FOLLOWUP=re.compile(
    r"\b(?:itu|tersebut|tadi|sebelumnya|what about|how about|"
    r"bagaimana dengan|lalu|then|and|selanjutnya)\b",re.I)


def choose_response_profile(question, previous="", pdf_evidence=None,
                            analysis_mode="AUTO", history=None):
    q=str(question or "").strip()
    if str(analysis_mode or "").upper()=="GENERAL":
        return GENERAL
    if not q:
        return GENERAL
    # A direct request for actual casework takes priority over a description
    # of a procedure, unless explicitly framed as a document-only question.
    cited=bool(pdf_evidence)
    document_question=bool(_PDF.search(q) or _ABOUT_DOCUMENT.search(q))
    procedural=bool(_PROCEDURE.search(q))
    social=bool(_SOCIAL.search(q))
    specific_case=bool(_CASE.search(q))
    action=bool(_ACTION.search(q))
    prev=str(previous or "")
    if not prev and isinstance(history,list):
        prev=next((str(row.get("text") or "") for row in reversed(history[-8:])
                   if isinstance(row,dict) and row.get("role")=="user"),"")
    continuing_document=(bool(_FOLLOWUP.search(q)) and
                         bool(_PDF.search(prev) or (_PROCEDURE.search(prev) and not _SOCIAL.search(prev))))
    if action and not (document_question and not specific_case):
        return ACTION_REQUEST
    if specific_case:
        return CASE_REVIEW
    modules=bool(re.search(r"\b(?:intelligence inbox|intel inbox|inbox)\b",q,re.I) and
                 re.search(r"\b(?:social listening|social media)\b",q,re.I))
    if modules and _CROSS_MODULE.search(q):
        return CROSS_MODULE_REVIEW
    if social:
        return SOCIAL_ANALYSIS
    if cited and (document_question or procedural or continuing_document):
        return PDF_GUIDANCE
    return SOCIAL_ANALYSIS if q else GENERAL


_CASE_TRAINING_PAGE_HEADINGS=(
    "kasus simulasi","skenario ini sepenuhnya fiktif",
    "pertanyaan uji dan kriteria lulus",
    "simulation case","test questions and acceptance criteria")
_CASE_SAMPLE_REQUEST_PHRASES=(
    "kasus simulasi","skenario fiktif","simulation case",
    "bws-rag-","pertanyaan uji","kriteria lulus","acceptance test")


def select_case_reference_pages(question,pages,limit=3):
    """Keep procedural PDF guidance but omit unrelated demo/QA pages for a live case."""
    visible=[row for row in pages or [] if row.get("record_type")=="PDF_KNOWLEDGE"]
    explicit_sample=any(phrase in str(question or "").casefold()
                        for phrase in _CASE_SAMPLE_REQUEST_PHRASES)
    if explicit_sample:
        return visible[:limit]
    return [row for row in visible
            if not any(heading in str(row.get("source_excerpt") or "").casefold()
                       for heading in _CASE_TRAINING_PAGE_HEADINGS)][:limit]


def cross_module_formal_focus(question,items):
    """Keep only subject-matched, already authorized Inbox records.

    Human-approved relevance is not the same as relevance to this question.
    General cross-module comparisons with no identifiable subject retain the
    existing retrieval behavior; named actor/system queries use strict focus.
    """
    from .assistant_social_focus import query_candidates
    from .processing_hints import CANDIDATE_ALIASES
    q=str(question or "").casefold()
    candidates=query_candidates(q)
    anchors=set()
    for canonical,aliases in CANDIDATE_ALIASES.items():
        if canonical.casefold() in candidates:
            anchors.update(str(a).casefold().strip() for a in set(aliases)|{canonical}
                           if len(str(a).strip())>=4)
    for marker in ("silon","sirekap","pdpb","dpt","dkpp","ptun"):
        if re.search(r"(?<!\w)"+re.escape(marker)+r"(?!\w)",q):
            anchors.add(marker)
    if not anchors:
        return list(items or [])
    accepted=[]
    for item in items or []:
        content=" ".join(str(getattr(item,key,"") or "")
                         for key in ("title","original_content","source_name","source_id")).casefold()
        if any(re.search(r"(?<!\w)"+re.escape(anchor)+r"(?!\w)",content) for anchor in anchors):
            accepted.append(item)
    return accepted


def evidence_for_profile(profile,formal, social, pdf):
    """Only include sources the user needs for this question."""
    if profile==PDF_GUIDANCE:
        return list(pdf or [])
    return list(formal or [])+list(social or [])+list(pdf or [])
