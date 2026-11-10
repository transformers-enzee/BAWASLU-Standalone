"""Choose the smallest useful assistant answer layout without consuming AI tokens.

Only source-authorized PDF passages may drive PDF_GUIDANCE. An attached PDF
does not turn an unrelated social-intelligence request into a document answer.
"""
import re

PDF_GUIDANCE="PDF_GUIDANCE"
SOCIAL_ANALYSIS="SOCIAL_ANALYSIS"
CASE_REVIEW="CASE_REVIEW"
ACTION_REQUEST="ACTION_REQUEST"
GENERAL="GENERAL"

_PDF=re.compile(
    r"\b(?:pdf|dokumen|document|reference|referensi|rujukan|lampiran|"
    r"uploaded|diunggah|terunggah|manual|sop|pedoman)\b",re.I)
_PROCEDURE=re.compile(
    r"\b(?:prosedur|procedure|process|workflow|alur|langkah|steps?|"
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
    if social:
        return SOCIAL_ANALYSIS
    if specific_case:
        return CASE_REVIEW
    if cited and (document_question or procedural or continuing_document):
        return PDF_GUIDANCE
    return SOCIAL_ANALYSIS if q else GENERAL


def evidence_for_profile(profile,formal, social, pdf):
    """Only include sources the user needs for this question."""
    if profile==PDF_GUIDANCE:
        return list(pdf or [])
    return list(formal or [])+list(social or [])+list(pdf or [])
