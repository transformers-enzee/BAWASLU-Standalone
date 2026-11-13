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
    r"legal|laws?|electoral law|election law|statutory|statute|regulation|"
    r"legislation|criminal liability)\b",re.I)
_LEGAL_DOC_TYPES={"REGULATION","SOP","GUIDANCE"}

# These words are routing hints, not a determination that a particular law applies.
_ELECTION_TYPE_HINTS={
    "PEMILU":re.compile(r"\\b(?:pemilu|general elections?|legislative elections?|presidential elections?)\\b",re.I),
    "PILKADA":re.compile(r"\\b(?:pilkada|pemilihan kepala daerah|regional head elections?|local head elections?)\\b",re.I),
}

def _election_types(text):
    value=str(text or "")
    return sorted(kind for kind,pattern in _ELECTION_TYPE_HINTS.items()
                  if pattern.search(value))

def _legal_election_scope(question,legal_docs):
    """Compare explicit question terms with document titles only.
    Unknown/ambiguous wording does not establish incompatibility or applicability.
    """
    requested=_election_types(question)
    details=[]
    for doc in legal_docs:
        title_types=_election_types(doc.get("title"))
        details.append({"record_id":str(doc.get("record_id") or ""),
                        "title_scope":title_types,
                        "scope_unambiguous":len(title_types)==1})
    conflicts=[item["record_id"] for item in details
               if len(requested)==1 and item["scope_unambiguous"]
               and requested[0] not in item["title_scope"]]
    unknown=[item["record_id"] for item in details
             if not item["scope_unambiguous"]]
    return requested,details,conflicts,unknown

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
                   records[ref].get("record_type")=="PDF_KNOWLEDGE" and
                   records[ref].get("document_type") in _LEGAL_DOC_TYPES]
        if not citations:
            continue  # no local PDF claim citation, handled by global check
        available=set()
        for ref in citations:
            available.update(_article_ids(records[ref].get("source_excerpt")))
        for article in articles:
            if article not in available:
                failures.append({"article":article,"cited_page_ids":citations})
    return failures


def _uncited_article_claims(answer,records):
    """Spot article statements without attributable, authorized PDF pages.

    A citation on the immediately next line/sentence is accepted only when
    that entire next span consists of actual authorized PDF references.
    Other narrative text between claim and citation is not treated as local
    attribution. This reduces false flags without trusting arbitrary cards.
    """
    results=[]
    spans=re.split(r"(?<=[.!?;])\s+|\n+",str(answer or ""))
    for i,span in enumerate(spans):
        articles=_article_ids(span)
        if not articles or span.strip().endswith("?"):
            continue
        pdf_ids=[ref for ref in _SOURCE_REF.findall(span)
                 if ref.startswith("DOC-") and ref in records and
                 records[ref].get("record_type")=="PDF_KNOWLEDGE" and
                 records[ref].get("document_type") in _LEGAL_DOC_TYPES]
        if not pdf_ids and i+1<len(spans):
            next_span=spans[i+1].strip()
            refs=_SOURCE_REF.findall(next_span)
            if refs and _SOURCE_REF.sub("",next_span).strip()=="":
                pdf_ids=[ref for ref in refs
                         if ref.startswith("DOC-") and ref in records and
                         records[ref].get("record_type")=="PDF_KNOWLEDGE" and
                 records[ref].get("document_type") in _LEGAL_DOC_TYPES]
        if not pdf_ids:
            results.extend(articles)
    return list(dict.fromkeys(results))


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
_QUOTED_ATTRIBUTION=re.compile(
    r"^\s*(?:[\"'“‘]|(?:according\s+to|reported(?:ly)?|mengutip|menurut\s+sumber)\b)",re.I)
# Split independent clauses so negation or quotation in one statement does
# not suppress a new enforcement instruction after "but"/"namun"/"tetapi".
_CLAUSE_BOUNDARY=re.compile(r"(?<=[.!?;])\s+|\n+|\s*[;:]\s*|\s+\b(?:but|however|namun|tetapi)\b\s+",re.I)
_ENFORCEMENT_EN_INFIX=re.compile(r"\b(?:must|shall|should)\s+(?:immediately\s+|now\s+)?(?:be\s+)?",re.I)
_ENFORCEMENT_ID_INFIX=re.compile(r"\b(?:harus|wajib|segera|langsung)\s+(?:segera\s+|langsung\s+)?",re.I)

def _assertive_enforcement_recommendations(answer):
    """Flag narrow coercive directives, respecting each separate clause.

    Explicit quoted-source clauses and negated directives are excluded,
    but an unrelated negation cannot hide a later positive instruction.
    """
    flags=[]
    for clause in _CLAUSE_BOUNDARY.split(str(answer or "")):
        clause=clause.strip()
        if not clause or clause.endswith("?") or _QUOTED_ATTRIBUTION.search(clause):
            continue
        matches=list(_ENFORCEMENT_EN.finditer(clause))+list(_ENFORCEMENT_ID.finditer(clause))
        # Some natural phrasings put the urgency adverb between the modality
        # and the enforcement verb; normalize only these limited patterns.
        normalized=_ENFORCEMENT_EN_INFIX.sub(lambda m:m.group().split()[0]+" ",clause)
        normalized=_ENFORCEMENT_ID_INFIX.sub(lambda m:m.group().split()[0]+" ",normalized)
        if not matches:
            matches=list(_ENFORCEMENT_EN.finditer(normalized))+list(_ENFORCEMENT_ID.finditer(normalized))
        if not matches:
            continue
        # Negation must apply locally to the directive, not to another clause.
        if _NEGATED_RECOMMENDATION.search(clause):
            continue
        flags.append("ASSERTIVE_ENFORCEMENT_DIRECTIVE")
    return list(dict.fromkeys(flags))


# A deterministic review-only detector of definite legal outcomes. Unlike
# article citations, these claims can be phrased without "pasal" or "article".
# These patterns flag apparent unsupported certainty, NOT actual guilt or law.
_CONFIRMED_VIOLATION_EN=re.compile(
    r"\b(?:(?:the|this)\s+(?:electoral\s+|election\s+|legal\s+)?"
    r"(?:violation|offen[sc]e)\s+(?:is|was|has\s+been)\s+(?:confirmed|proven)|"
    r"(?:evidence|records?)\s+(?:confirms?|proves?)\s+(?:an?\s+)?"
    r"(?:electoral\s+|election\s+|legal\s+)?(?:violation|offen[sc]e)|"
    r"(?:candidate|official|officer|suspect|person)\s+"
    r"(?:has\s+|have\s+|had\s+)?(?:violated|committed\s+(?:an?\s+)?(?:electoral\s+)?(?:violation|offen[sc]e))"
    r"(?:\s+(?:election|electoral)\s+law)?)\b",re.I)
_CONFIRMED_GUILT_EN=re.compile(
    r"\b(?:is|was|are|were|has\s+been|have\s+been)\s+"
    r"(?:legally\s+|criminally\s+)?(?:guilty|convicted|liable)\b",re.I)
_CONFIRMED_OUTCOME_EN=re.compile(
    r"\b(?:is|was|has\s+been|have\s+been)\s+"
    r"(?:already\s+)?(?:disqualified|banned|sentenced|fined|penalized|penalised)\b",re.I)
_CONFIRMED_VIOLATION_ID=re.compile(
    r"\b(?:terbukti\s+melanggar|telah\s+melanggar\s+(?:hukum|undang.undang|"
    r"peraturan\s+pemilu)|pelanggaran\s+(?:ini\s+)?(?:telah\s+)?terbukti|"
    r"telah\s+terjadi\s+pelanggaran\s+(?:hukum|pemilu))\b",re.I)
_CONFIRMED_GUILT_ID=re.compile(
    r"\b(?:dinyatakan\s+bersalah|telah\s+bersalah|terbukti\s+bersalah)\b",re.I)
_CONFIRMED_OUTCOME_ID=re.compile(
    r"\b(?:telah\s+(?:didiskualifikasi|dipidana|dihukum|didenda)|"
    r"sanksi\s+(?:telah\s+)?dijatuhkan|hak\s+(?:dipilih|politik)\s+(?:telah\s+)?dicabut)\b",re.I)
_CONCESSION_OPEN=re.compile(r"^\s*(?:although|even\s+though|while|meskipun|walaupun)\b",re.I)

def _legal_claim_clauses(answer):
    """Split a concessive lead-in from the independent legal assertion.

    A single sentence may say 'Although the allegation is unverified,
    the candidate is guilty.' Uncertainty about the allegation must not
    suppress the independent assertion. Do not split reported speech
    ('According to reports, ...') into a false affirmative claim.
    """
    for clause in _CLAUSE_BOUNDARY.split(str(answer or "")):
        if _CONCESSION_OPEN.search(clause) and "," in clause:
            lead,main=clause.split(",",1)
            yield lead
            if main.strip():
                yield main
        else:
            yield clause


_UNCERTAIN_OUTCOME=re.compile(
    r"\b(?:alleged(?:ly)?|allegation|suspected|potential(?:ly)?|"
    r"may|might|could|unverified|unconfirmed|reportedly|"
    r"appears\s+to|claims?\s+that|"
    r"diduga|dugaan|terduga|berpotensi|mungkin|"
    r"belum\s+(?:terbukti|diverifikasi|dikonfirmasi)|"
    r"masih\s+(?:perlu|dalam)\s+(?:verifikasi|pemeriksaan)|"
    r"perlu\s+(?:diverifikasi|diperiksa))\b",re.I)

def _asserted_legal_outcomes(answer):
    """Review categorical verdict/outcome language absent legal article IDs.

    Scan independent clauses; quoted, explicitly negated or hedged clauses
    cannot certify wrongdoing. Result categories are *detection labels* only.
    """
    flags=[]
    for clause in _legal_claim_clauses(answer):
        clause=clause.strip()
        if not clause or clause.endswith("?") or _QUOTED_ATTRIBUTION.search(clause):
            continue
        if _NEGATED_RECOMMENDATION.search(clause) or _UNCERTAIN_OUTCOME.search(clause):
            continue
        if _CONFIRMED_VIOLATION_EN.search(clause) or _CONFIRMED_VIOLATION_ID.search(clause):
            flags.append("ASSERTED_CONFIRMED_VIOLATION")
        if _CONFIRMED_GUILT_EN.search(clause) or _CONFIRMED_GUILT_ID.search(clause):
            flags.append("ASSERTED_LEGAL_GUILT")
        if _CONFIRMED_OUTCOME_EN.search(clause) or _CONFIRMED_OUTCOME_ID.search(clause):
            flags.append("ASSERTED_ENFORCEMENT_OUTCOME")
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
        "article_unattributed":{
            "id":"Peringatan rujukan: Ada pernyataan pasal hukum tanpa kutipan halaman PDF di kalimat yang sama. Petugas harus menelusuri rujukan sebelum mengandalkannya.",
            "en":"Legal source caution: An article-level statement lacks a PDF page citation in the same sentence. An officer must trace its source before relying on it."},
        "article_mismatch":{
            "id":"Peringatan rujukan pasal: Nomor pasal yang disebut dalam jawaban tidak ditemukan dalam kutipan halaman PDF hukum yang benar-benar dirujuk. Periksa naskah resmi sebelum mengandalkan rekomendasi ini.",
            "en":"Legal article caution: An article number stated in the answer was not found in the actually cited PDF page excerpts. Check the official legal text before relying on this recommendation."},
        "enforcement":{
            "id":"Peringatan tindakan hukum: Jawaban ini memuat arahan penegakan atau sanksi yang bersifat tegas. Kutipan PDF tidak memverifikasi kewenangan, fakta kasus, atau dasar hukumnya. Jangan laksanakan tanpa penilaian petugas berwenang.",
            "en":"Enforcement caution: This answer contains an assertive enforcement or penalty recommendation. PDF citations do not verify legal authority, case facts, or applicable law. Do not act without an authorized officer's review."},
        "categorical_verdict":{
            "id":"Peringatan kepastian hukum: Jawaban ini menyampaikan pelanggaran, kesalahan, atau sanksi sebagai hal yang sudah pasti. Bukti tersimpan dan kutipan PDF saja tidak membuktikan putusan atau status hukum. Petugas berwenang harus memverifikasi sumber dan status resmi.",
            "en":"Legal certainty caution: The answer presents a violation, guilt, or penalty as an established outcome. Saved evidence and PDF references alone do not confirm a legal ruling or status. An authorized officer must verify official records."},
        "citation_overflow":{
            "id":"Catatan kutipan: Sebagian rujukan melebihi batas 12 ID unik dan dihilangkan. Jawaban ini tidak boleh dianggap telah didukung sepenuhnya oleh sumber. Periksa kembali rujukan yang ditampilkan.",
            "en":"Citation limit caution: References beyond the first 12 unique IDs were removed. Do not treat this answer as fully source-supported; inspect the remaining citations."},
    }
    return choices[key].get(language,choices[key]["en"])


def _officer_review_steps(cited, records, reasons, legal_question, has_legal_flags):
    """Advisory steps only. Uses only IDs in the displayed, authorized citations.

    Never issues a casework action, records an approval or infers a legal
    finding. No uncited or excess source is exposed through the steps.
    """
    social=[ref for ref in cited if records[ref].get("record_type")=="SOCIAL_LISTENING"]
    formal=[ref for ref in cited if records[ref].get("record_type")=="FORMAL_INTELLIGENCE"]
    pdf=[ref for ref in cited if records[ref].get("record_type")=="PDF_KNOWLEDGE"]
    legal_pdf=[ref for ref in pdf
               if records[ref].get("document_type") in _LEGAL_DOC_TYPES]
    steps=[]
    def add(code,refs):
        steps.append({"code":code,"source_ids":refs[:12],"status":"NOT_STARTED",
                      "officer_action_only":True})
    if social:
        add("VERIFY_ORIGINAL_POST_CONTEXT",social)
    if formal:
        add("TRACE_FORMAL_EVIDENCE_CHAIN",formal)
    if "CITATION_INTEGRITY" in reasons:
        add("RECHECK_MISSING_OR_OMITTED_REFERENCES",cited)
    if "LEGAL_ARTICLE_ATTRIBUTION" in reasons:
        add("MATCH_CITED_LEGAL_PASSAGES",legal_pdf)
    if "CITED_UNREVIEWED_PDF" in reasons:
        add("REQUEST_DOCUMENT_REVIEW",[
            ref for ref in pdf if records[ref].get("review_status")!="OFFICER_REVIEWED"])
    if (legal_question or has_legal_flags) and not legal_pdf:
        add("LOCATE_AUTHORIZED_LEGAL_REFERENCE",[])
    if "LEGAL_ELECTION_SCOPE" in reasons:
        add("VERIFY_ELECTION_TYPE_APPLICABILITY",legal_pdf)
    if "CATEGORICAL_LEGAL_OUTCOME" in reasons:
        add("VERIFY_OFFICIAL_LEGAL_OUTCOME",formal+legal_pdf)
    if "ENFORCEMENT_RECOMMENDATION" in reasons:
        add("CONFIRM_AUTHORITY_BEFORE_ANY_ACTION",formal+legal_pdf)
    return steps


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
    excess=[]
    citation_limit=12
    def valid_ref(match):
        ref=match.group(1)
        if ref not in allowed:
            rejected.append(ref)
            return ""
        if ref in displayed:
            return match.group(0)
        if len(displayed)>=citation_limit:
            excess.append(ref)
            return ""
        displayed.append(ref)
        return match.group(0)
    text=_SOURCE_REF.sub(valid_ref,raw)
    # Remove spaces before punctuation left by rejected references only.
    if rejected or excess:
        text=re.sub(r"[ \t]+([,.;:!?])",r"\1",text)
        text=re.sub(r"[ \t]{2,}"," ",text)
    cited=displayed
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
    legal_doc_refs=[doc for doc in doc_refs
                    if doc.get("document_type") in _LEGAL_DOC_TYPES]
    requested_election_types,election_scope_rows,election_scope_conflicts,election_scope_unknown=_legal_election_scope(question,legal_doc_refs)
    legally_reviewed=[doc for doc in legal_doc_refs
                      if doc.get("review_status")=="OFFICER_REVIEWED"]
    legal_unreviewed=[doc for doc in legal_doc_refs
                      if doc.get("review_status")!="OFFICER_REVIEWED"]
    # The page may be context or an internal report, not a legal authority.
    # Never count articles in a nonlegal PDF as legal-reference coverage.
    article_ids,missing_article_ids=_legal_article_presence(raw,legal_doc_refs)
    local_article_mismatches=_claim_level_article_mismatches(raw,records)
    unattributed_articles=_uncited_article_claims(raw,records)
    enforcement_flags=_assertive_enforcement_recommendations(raw)
    categorical_outcome_flags=_asserted_legal_outcomes(raw)
    needs_legal_warning=bool(_LEGAL_QUESTION.search(str(question or "")) or article_ids
                             or enforcement_flags or categorical_outcome_flags)
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
    if unattributed_articles:
        notes.append(_message(language,"article_unattributed"))
    if enforcement_flags:
        notes.append(_message(language,"enforcement"))
    if categorical_outcome_flags:
        notes.append(_message(language,"categorical_verdict"))
    if excess:
        notes.append(_message(language,"citation_overflow"))
    if records and not cited and not pdf_guidance:
        notes.append(_message(language,"uncited"))
    for note in notes:
        if note not in text:
            text=text.rstrip()+"\n\n"+note
    review_reasons=[]
    if categorical_outcome_flags:
        review_reasons.append("CATEGORICAL_LEGAL_OUTCOME")
    if enforcement_flags:
        review_reasons.append("ENFORCEMENT_RECOMMENDATION")
    if missing_article_ids or local_article_mismatches or unattributed_articles:
        review_reasons.append("LEGAL_ARTICLE_ATTRIBUTION")
    if unreviewed:
        review_reasons.append("CITED_UNREVIEWED_PDF")
    if len(requested_election_types)==1 and (election_scope_conflicts or election_scope_unknown):
        review_reasons.append("LEGAL_ELECTION_SCOPE")
    if excess or rejected:
        review_reasons.append("CITATION_INTEGRITY")
    review_steps=_officer_review_steps(
        cited,records,review_reasons,needs_legal_warning,
        bool(enforcement_flags or categorical_outcome_flags))
    # Readiness refers only to citation availability, never factual or legal
    # correctness. Legal questions without cited PDF text must not be treated
    # as ready simply because a neutral AI answer omitted an enforcement verb.
    if needs_legal_warning and not doc_refs:
        citation_coverage="LEGAL_REFERENCE_NOT_CITED"
    elif needs_legal_warning and not legal_doc_refs:
        citation_coverage="LEGAL_REFERENCE_NONLEGAL_PDF_ONLY"
    elif needs_legal_warning and legal_doc_refs:
        citation_coverage="LEGAL_REFERENCE_CITED_UNVERIFIED"
    elif records and not cited:
        citation_coverage="SELECTED_EVIDENCE_NOT_CITED"
    elif cited:
        citation_coverage="CITED_EVIDENCE_UNVERIFIED"
    else:
        citation_coverage="NO_CITED_EVIDENCE"
    metadata={
        "audit_version":"ASSISTANT_GROUNDING_V1483",
        "scope":"ONLY_CURRENTLY_AUTHORIZED_SELECTED_RECORDS",
        "selected_records":len(records),
        "displayed_citation_count":len(cited),
        "displayed_citation_ids":cited,
        "model_cited_but_not_displayed":len(structured-set(cited)),
        "rejected_unavailable_citations":len(rejected),
        "omitted_excess_citation_count":len(excess),
        "omitted_excess_citation_ids":list(dict.fromkeys(excess)),
        "citation_reference_limit":citation_limit,
        "citation_ids_valid":True,  # only after deterministic filtering
        "cited_pdf_pages":len(doc_refs),
        "cited_legal_reference_pages":len(legal_doc_refs),
        "cited_nonlegal_pdf_pages":len(doc_refs)-len(legal_doc_refs),
        "cited_unreviewed_legal_pages":len(legal_unreviewed),
        "cited_reviewed_legal_pages":len(legally_reviewed),
        "legal_source_review_state":("NO_ELIGIBLE_LEGAL_REFERENCE" if not legal_doc_refs
                                      else "REVIEW_PENDING" if legal_unreviewed
                                      else "OFFICER_REVIEWED_NOT_LEGALLY_VERIFIED"),
        "legal_source_review_is_approval":False,
        "legal_document_type_eligibility_verified":False,
        "legal_document_version_metadata_available":False,
        "legal_document_version_verified":False,
        "legal_document_effective_date_verified":False,
        "legal_question_election_type_hints":requested_election_types,
        "legal_cited_title_election_type_hints":election_scope_rows,
        "legal_election_type_title_conflict_ids":election_scope_conflicts,
        "legal_election_type_title_unknown_ids":election_scope_unknown,
        "legal_election_type_applicability_verified":False,
        "cited_unreviewed_pdf_pages":len(unreviewed),
        "mixed_review_status_cited_pdf_pages":bool(unreviewed and legally_reviewed),
        "selected_unreviewed_pdf_pages":len(selected_unreviewed),
        "cited_officer_reviewed_legal_pages":len(legally_reviewed),
        "selected_pdf_pages":len(all_doc_refs),
        "legal_question":needs_legal_warning,
        "legal_article_numbers_mentioned":article_ids,
        "legal_article_numbers_not_found_in_cited_pdf":missing_article_ids,
        "legal_article_claim_citation_mismatches":local_article_mismatches,
        "legal_article_claim_citation_mismatch_count":len(local_article_mismatches),
        "legal_article_claims_without_local_pdf_citation":unattributed_articles,
        "legal_article_claims_without_local_pdf_citation_count":len(unattributed_articles),
        "legal_article_excerpt_text_check":"LEXICAL_ONLY_NOT_LEGAL_VALIDATION",
        "legal_article_reference_needs_review":bool(
            missing_article_ids or local_article_mismatches or unattributed_articles),
        "legal_article_semantic_support_verified":False,
        "legal_enforcement_directive_flags":enforcement_flags,
        "legal_enforcement_recommendation_needs_officer_review":bool(enforcement_flags),
        "legal_enforcement_classification_basis":"CONSERVATIVE_LANGUAGE_HEURISTIC_ONLY",
        "legal_categorical_outcome_flags":categorical_outcome_flags,
        "legal_categorical_outcome_needs_officer_review":bool(categorical_outcome_flags),
        "legal_categorical_outcome_classification_basis":"HEURISTIC_ONLY_NOT_LEGAL_VERDICT",
        "legal_currentness_verified":False,
        "legal_verdict_confirmed":False,
        "legal_review_reason_codes":review_reasons,
        "legal_review_reason_count":len(review_reasons),
        "officer_review_steps":review_steps,
        "officer_review_steps_are_advisory":True,
        "officer_review_steps_auto_completed":False,
        "evidence_citation_coverage":citation_coverage,
        "evidence_citation_coverage_is_truth_verification":False,
        "legal_action_ready":False,
        "source_truth_verified":False,
        "source_cards_are_citations":False,
        "claims_semantically_verified":False,
        "unreviewed_pdf_warning_added":bool(selected_unreviewed) and pdf_guidance,
        "legal_reference_limit_added":bool(pdf_guidance and needs_legal_warning
                                           and not legally_reviewed),
        "audit_used_paid_provider":False,
        "human_review_required":bool(records or review_steps or categorical_outcome_flags or enforcement_flags or excess),
    }
    return text,cited,metadata
