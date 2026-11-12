"""Deterministic, permission-scoped grounding audit for BAWASLU Assistant.

No model call, web request, database read, or legal determination is made here.
The supplied evidence must ALREADY be filtered to the officer's access scope.
This module validates *references*, not the semantic truth of any assertion.
"""
import re

# A displayed bracket reference is meaningful only if that exact ID was
# selected from the currently authorized evidence.
_SOURCE_REF=re.compile(r"\[((?:INT|SOCIAL)-[A-Za-z0-9:_-]+|DOC-[0-9]+-P[0-9]+)\]")
_LEGAL_QUESTION=re.compile(
    r"\b(?:hukum|undang.undang|pidana|pasal|perbawaslu|peraturan|sanksi|"
    r"legal|electoral law|election law|statutory|statute|regulation|"
    r"legislation|criminal liability)\b",re.I)
_LEGAL_DOC_TYPES={"REGULATION","SOP","GUIDANCE"}
# This is an exact text-presence check only. It cannot prove whether an
# article applies, whether amendments exist, or whether an interpretation is
# legally correct. Never extract article numbers from the explanatory caution.
_ARTICLE=re.compile(r"(?<!\w)(?:pasal|article)\s+0*([1-9][0-9]{0,5}[a-z]?)(?!\w)",re.I)


def _article_ids(text):
    return list(dict.fromkeys(value.casefold() for value in
                              _ARTICLE.findall(str(text or ""))))


def _legal_article_presence(answer,doc_refs):
    """Look for named articles in actually cited PDF pages, never source cards."""
    mentioned=_article_ids(answer)
    page_articles=set()
    for row in doc_refs:
        page_articles.update(_article_ids(row.get("source_excerpt")))
    return mentioned,[x for x in mentioned if x not in page_articles]


def _claim_level_article_mismatches(answer,records):
    """Check article numbers against PDF citations in their own sentence.

    An article mentioned near DOC-2-P4 cannot be authenticated by an
    unrelated DOC-1-P1 cited in another sentence. This heuristic is limited
    to explicit bracket IDs and punctuation-bound sentence spans; it does
    NOT infer factual or legal entailment.
    """
    failures=[]
    spans=re.split(r"(?<=[.!?;])\s+|\n+",str(answer or ""))
    for span in spans:
        articles=_article_ids(span)
        if not articles:
            continue
        citations=[ref for ref in dict.fromkeys(_SOURCE_REF.findall(span))
                   if ref.startswith("DOC-") and
                   ref in records and
                   records[ref].get("record_type")=="PDF_KNOWLEDGE"]
        if not citations:
            continue  # no local PDF claim citation, handled by global check
        available=set()
        for ref in citations:
            available.update(_article_ids(records[ref].get("source_excerpt")))
        for article in articles:
            if article not in available:
                failures.append({"article":article,"cited_page_ids":citations})
    return failures




# Constrained safety triage for assertive enforcement prescriptions. This is a
# language-pattern flag only; it cannot verify legal intent or consequences.
_ENFORCEMENT_EN=re.compile(
    r"\b(?:must|shall|immediately|should)\s+(?:(?:be|now)\s+)?"
    r"(?:arrest(?:ed)?|detain(?:ed)?|imprison(?:ed)?|prosecute(?:d)?|"
    r"fine(?:d)?|penali[sz]e(?:d)?|sentence(?:d)?|convict(?:ed)?|"
    r"ban(?:ned)?|disqualif(?:y|ied)|revoke|remove\s+(?:the\s+)?(?:candidate|official))\b",
    re.I)
_ENFORCEMENT_ID=re.compile(
    r"\b(?:harus|wajib|segera|langsung)\s+(?:(?:di|untuk)\s+)?"
    r"(?:ditangkap|tangkap|ditahan|tahan|dipidana|pidanakan|dihukum|"
    r"dipenjara|penjarakan|didenda|denda|didiskualifikasi|diskualifikasi|"
    r"dicabut\s+hak|cabut\s+hak)\b",re.I)
_NEGATED_RECOMMENDATION=re.compile(
    r"\b(?:not|never|should\s+not|must\s+not|tidak|jangan|belum|bukan)\b",re.I)
# Don't classify questions, quoted source text, or explicit negations as a
# positive recommendation merely because a keyword is present.
def _assertive_enforcement_recommendations(answer):
    spans=re.split(r"(?<=[.!?;])\s+|\n+",str(answer or ""))
    flags=[]
    for span in spans:
        if not span.strip() or span.strip().endswith("?"):
            continue
        if _NEGATED_RECOMMENDATION.search(span):
            continue
        if re.search(r"(?:^\s*[\"'“‘]|(?:according to|reported|mengutip|menurut\s+sumber)\b)",span,re.I):
            continue
        if _ENFORCEMENT_EN.search(span) or _ENFORCEMENT_ID.search(span):
            flags.append("ASSERTIVE_ENFORCEMENT_DIRECTIVE")
    return list(dict.fromkeys(flags))

def _message(language, key):
    choices={
        "unreviewed":{
            "id":"Catatan sumber: Dokumen PDF yang dikutip belum ditelaah petugas. Isinya bukan dasar hukum yang telah disahkan.",
            "en":"Source caution: A cited PDF has not been officer-reviewed. Its contents are not an approved legal authority."},
        "currentness":{
            "id":"Catatan hukum: Kewenangan, perubahan peraturan, dan keberlakuan hukum belum diverifikasi secara independen. Petugas berwenang harus memeriksa sumber resmi sebelum kesimpulan hukum.",
            "en":"Legal caution: Issuing authority, amendments and current legal force have not been independently verified. An authorized officer must check official sources before a legal conclusion."},
        "no_authority":{
            "id":"Batas rujukan: Belum ada kutipan PDF hukum yang ditelaah petugas untuk mendukung kesimpulan hukum pada jawaban ini.",
            "en":"Reference limit: No officer-reviewed legal PDF passage supports a legal conclusion in this answer."},
        "uncited":{
            "id":"Catatan bukti: Jawaban ini tidak mencantumkan kutipan ID sumber yang tampil. Kartu sumber di bawah hanya konteks, bukan dukungan terverifikasi untuk setiap klaim.",
            "en":"Evidence caution: This answer does not display supporting source-ID citations. Source cards below provide context, not verified support for every claim."},
        "article_mismatch":{
            "id":"Peringatan rujukan pasal: Nomor pasal yang disebut dalam jawaban tidak ditemukan dalam kutipan halaman PDF hukum yang benar-benar dirujuk. Periksa naskah resmi sebelum mengandalkan rekomendasi ini.",
            "en":"Legal article caution: An article number stated in the answer was not found in the actually cited PDF page excerpts. Check the official legal text before relying on this recommendation."},
        "enforcement":{
            "id":"Peringatan tindakan hukum: Jawaban ini memuat arahan penegakan atau sanksi yang bersifat tegas. Kutipan PDF tidak memverifikasi kewenangan, fakta kasus, atau dasar hukumnya. Jangan laksanakan tanpa penilaian petugas berwenang.",
            "en":"Enforcement caution: This answer contains an assertive enforcement or penalty recommendation. PDF citations do not verify legal authority, case facts, or applicable law. Do not act without an authorized officer's review."},
    }
    return choices[key].get(language,choices[key]["en"])


def audit_assistant_answer(question, evidence, answer, model_cited_ids=None,
                           profile="SOCIAL_ANALYSIS", language="id"):
    """Reconcile cited IDs against the ACTUAL displayed answer.

    - Discard invented bracketed source references in answer text.
    - Structured model citations that never appear in answer are NOT counted.
    - Explicitly flag unsigned PDF pages and unverified legal currency.
    - Never mistake source cards or relevance review for proof of source truth.

    Returns (display_answer, displayed_citation_ids, metadata).
    """
    records={str(row.get("record_id") or ""):row for row in evidence or []
             if isinstance(row,dict) and row.get("record_id")}
    allowed=set(records)
    raw=str(answer or "")
    displayed=[]
    rejected=[]
    def valid_ref(match):
        ref=match.group(1)
        if ref not in allowed:
            rejected.append(ref)
            return ""
        if ref not in displayed:
            displayed.append(ref)
        return match.group(0)
    text=_SOURCE_REF.sub(valid_ref,raw)
    # Remove spaces before punctuation left by rejected references only.
    if rejected:
        text=re.sub(r"[ \t]+([,.;:!?])",r"\1",text)
        text=re.sub(r"[ \t]{2,}"," ",text)
    cited=displayed[:12]
    structured={ref for ref in (model_cited_ids or [])
                if isinstance(ref,str) and ref in allowed}
    doc_refs=[records[ref] for ref in cited if
              records[ref].get("record_type")=="PDF_KNOWLEDGE"]
    all_doc_refs=[row for row in records.values()
                  if row.get("record_type")=="PDF_KNOWLEDGE"]
    unreviewed=[doc for doc in doc_refs
                if doc.get("review_status")!="OFFICER_REVIEWED"]
    selected_unreviewed=[doc for doc in all_doc_refs
                         if doc.get("review_status")!="OFFICER_REVIEWED"]
    legally_reviewed=[doc for doc in doc_refs
                      if doc.get("review_status")=="OFFICER_REVIEWED" and
                      doc.get("document_type") in _LEGAL_DOC_TYPES]
    article_ids,missing_article_ids=_legal_article_presence(raw,doc_refs)
    local_article_mismatches=_claim_level_article_mismatches(raw,records)
    enforcement_flags=_assertive_enforcement_recommendations(raw)
    needs_legal_warning=bool(_LEGAL_QUESTION.search(str(question or "")) or article_ids
                             or enforcement_flags)
    notes=[]
    pdf_guidance=profile=="PDF_GUIDANCE"
    if pdf_guidance:
        if selected_unreviewed:
            notes.append(_message(language,"unreviewed"))
        # Even an officer-reviewed PDF is not proof of current legal force.
        if needs_legal_warning:
            if not legally_reviewed:
                notes.append(_message(language,"no_authority"))
            notes.append(_message(language,"currentness"))
    if article_ids and (missing_article_ids or local_article_mismatches):
        notes.append(_message(language,"article_mismatch"))
    if enforcement_flags:
        notes.append(_message(language,"enforcement"))
    if records and not cited and not pdf_guidance:
        notes.append(_message(language,"uncited"))
    for note in notes:
        if note not in text:
            text=text.rstrip()+"\n\n"+note
    metadata={
        "audit_version":"ASSISTANT_GROUNDING_V1483",
        "scope":"ONLY_CURRENTLY_AUTHORIZED_SELECTED_RECORDS",
        "selected_records":len(records),
        "displayed_citation_count":len(cited),
        "displayed_citation_ids":cited,
        "model_cited_but_not_displayed":len(structured-set(cited)),
        "rejected_unavailable_citations":len(rejected),
        "citation_ids_valid":True,  # only after deterministic filtering
        "cited_pdf_pages":len(doc_refs),
        "cited_unreviewed_pdf_pages":len(unreviewed),
        "selected_unreviewed_pdf_pages":len(selected_unreviewed),
        "cited_officer_reviewed_legal_pages":len(legally_reviewed),
        "selected_pdf_pages":len(all_doc_refs),
        "legal_question":needs_legal_warning,
        "legal_article_numbers_mentioned":article_ids,
        "legal_article_numbers_not_found_in_cited_pdf":missing_article_ids,
        "legal_article_claim_citation_mismatches":local_article_mismatches,
        "legal_article_claim_citation_mismatch_count":len(local_article_mismatches),
        "legal_article_excerpt_text_check":"LEXICAL_ONLY_NOT_LEGAL_VALIDATION",
        "legal_article_reference_needs_review":bool(
            missing_article_ids or local_article_mismatches),
        "legal_article_semantic_support_verified":False,
        "legal_enforcement_directive_flags":enforcement_flags,
        "legal_enforcement_recommendation_needs_officer_review":bool(enforcement_flags),
        "legal_enforcement_classification_basis":"CONSERVATIVE_LANGUAGE_HEURISTIC_ONLY",
        "legal_currentness_verified":False,
        "legal_verdict_confirmed":False,
        "source_truth_verified":False,
        "source_cards_are_citations":False,
        "claims_semantically_verified":False,
        "unreviewed_pdf_warning_added":bool(selected_unreviewed) and pdf_guidance,
        "legal_reference_limit_added":bool(pdf_guidance and needs_legal_warning
                                           and not legally_reviewed),
        "audit_used_paid_provider":False,
        "human_review_required":bool(records),
    }
    return text,cited,metadata
