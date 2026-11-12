"""v148.3 deterministic answer-quality QA: no model credits, no DB mutations.

This suite checks *reference integrity*, not the substantive accuracy of a
large language model or whether allegations are legally true.
"""
from app.assistant_grounding import audit_assistant_answer


def social(identifier="SOCIAL-11",sentiment="NEGATIVE"):
    return {"record_id":identifier,"record_type":"SOCIAL_LISTENING",
            "verification_status":"UNVERIFIED_SOCIAL_SOURCE",
            "sentiment":sentiment,"source_url":"https://example.invalid/source/11"}


def legal_page(identifier="DOC-1-P3",status="UNREVIEWED",kind="REGULATION"):
    return {"record_id":identifier,"record_type":"PDF_KNOWLEDGE",
            "document_id":1,"page":3,"review_status":status,
            "document_type":kind,"legal_currentness_verified":False,
            "source_excerpt":"Simulasi penanganan laporan dugaan pelanggaran."}


def test_only_exact_authorized_visible_citations_are_reported():
    evidence=[social(),social("SOCIAL-22"),legal_page()]
    answer="Saved allegation [SOCIAL-11] and unknown [SOCIAL-999]. An unreviewed page [DOC-1-P3]."
    updated,refs,audit=audit_assistant_answer(
        "Discuss the saved evidence",evidence,answer,
        ["SOCIAL-22","SOCIAL-11","SOCIAL-999"],profile="CASE_REVIEW",language="en")
    assert refs==["SOCIAL-11","DOC-1-P3"]
    assert "[SOCIAL-999]" not in updated
    assert "[SOCIAL-11]" in updated and "[DOC-1-P3]" in updated
    assert audit["displayed_citation_count"]==2
    assert audit["model_cited_but_not_displayed"]==1
    assert audit["rejected_unavailable_citations"]==1
    assert audit["citation_ids_valid"]
    assert audit["claims_semantically_verified"] is False
    assert audit["source_truth_verified"] is False
    assert audit["audit_used_paid_provider"] is False


def test_citations_printed_but_omitted_from_model_metadata_are_recovered():
    answer,ids,audit=audit_assistant_answer(
        "What do the selected posts report?",[social()],
        "The saved post reports an allegation. [SOCIAL-11]",[],
        profile="SOCIAL_ANALYSIS",language="en")
    assert ids==["SOCIAL-11"]
    assert audit["model_cited_but_not_displayed"]==0
    assert audit["displayed_citation_ids"]==ids
    assert "Evidence caution" not in answer


def test_uncited_source_cards_are_contextual_not_validated_claims():
    text,cited,audit=audit_assistant_answer(
        "What concerns are circulating?",[social()],
        "No source citations were included in this answer.",
        ["SOCIAL-11"],profile="SOCIAL_ANALYSIS",language="en")
    assert cited==[]
    assert "Source cards below provide context" in text
    assert audit["displayed_citation_count"]==0
    assert audit["model_cited_but_not_displayed"]==1
    assert audit["source_cards_are_citations"] is False


def test_pdf_guidance_unreviewed_reference_never_becomes_approved_law():
    text,refs,audit=audit_assistant_answer(
        "Apa ketentuan hukum dan sanksi dalam peraturan ini?",
        [legal_page()],
        "Dokumen simulasi mencantumkan tata cara, belum ada putusan. [DOC-1-P3]",
        ["DOC-1-P3"],profile="PDF_GUIDANCE",language="id")
    assert refs==["DOC-1-P3"]
    assert "belum ditelaah petugas" in text
    assert "Belum ada kutipan PDF hukum yang ditelaah petugas" in text
    assert "belum diverifikasi secara independen" in text
    assert audit["legal_reference_limit_added"] is True
    assert audit["cited_unreviewed_pdf_pages"]==1
    assert audit["cited_officer_reviewed_legal_pages"]==0
    assert audit["legal_currentness_verified"] is False
    assert audit["legal_verdict_confirmed"] is False


def test_officer_reviewed_legal_pdf_still_never_proves_current_force():
    text,ids,audit=audit_assistant_answer(
        "Which election law applies?",
        [legal_page("DOC-6-P8",status="OFFICER_REVIEWED")],
        "The approved reference is a cited document, not a legal ruling. [DOC-6-P8]",
        ["DOC-6-P8"],profile="PDF_GUIDANCE",language="en")
    assert ids==["DOC-6-P8"]
    assert "Legal caution" in text
    assert "Reference limit" not in text
    assert "Source caution" not in text
    assert audit["cited_officer_reviewed_legal_pages"]==1
    assert audit["legal_currentness_verified"] is False


def test_unreviewed_training_pdf_can_be_summarized_with_source_warning():
    text,ids,audit=audit_assistant_answer(
        "Summarize my PDF",
        [legal_page()],
        "The PDF is a simulated officer handbook. [DOC-1-P3]",
        ["DOC-1-P3"],profile="PDF_GUIDANCE",language="en")
    assert ids==["DOC-1-P3"]
    assert "Source caution" in text
    assert "Legal caution" not in text
    assert "Reference limit" not in text
    assert audit["selected_pdf_pages"]==1


def test_no_pdf_or_no_evidence_never_invents_a_citation():
    text,ids,audit=audit_assistant_answer(
        "Menurut PDF, pasal apa berlaku?",
        [],"Tidak ada dokumen dengan halaman yang cocok.",[],
        profile="PDF_GUIDANCE",language="id")
    assert ids==[]
    assert "Belum ada kutipan PDF hukum" in text
    assert audit["selected_records"]==0
    assert audit["legal_currentness_verified"] is False


def test_social_source_cannot_substitute_for_legal_authority_in_pdf_answer():
    text,ids,audit=audit_assistant_answer(
        "What legal sanction follows?",
        [social(),legal_page()],
        "A user alleges wrongdoing. [SOCIAL-11]",
        ["SOCIAL-11"],profile="PDF_GUIDANCE",language="en")
    assert ids==["SOCIAL-11"]
    assert audit["cited_pdf_pages"]==0
    assert audit["cited_officer_reviewed_legal_pages"]==0
    assert "No officer-reviewed legal PDF passage" in text
    assert "Legal caution" in text


def test_duplicate_citations_are_counted_once_and_not_guessed():
    text,ids,audit=audit_assistant_answer(
        "Summarize report",
        [social()], "Evidence [SOCIAL-11] and again [SOCIAL-11].",
        ["SOCIAL-11","SOCIAL-11"],profile="CASE_REVIEW",language="en")
    assert ids==["SOCIAL-11"]
    assert audit["displayed_citation_count"]==1
    assert text.count("[SOCIAL-11]")==2


def test_unsupported_pdf_page_reference_is_removed_before_display():
    text,ids,audit=audit_assistant_answer(
        "Summarize PDF",
        [legal_page("DOC-1-P3")],
        "Claims [DOC-1-P999] but actual page [DOC-1-P3]",
        ["DOC-1-P999","DOC-1-P3"],profile="PDF_GUIDANCE",language="en")
    assert "[DOC-1-P999]" not in text
    assert ids==["DOC-1-P3"]
    assert audit["rejected_unavailable_citations"]==1
    assert audit["cited_unreviewed_pdf_pages"]==1


def test_uncited_pdf_still_discloses_unreviewed_source_status():
    text,refs,audit=audit_assistant_answer(
        "Summarize the uploaded PDF handbook",
        [legal_page()],
        "The uploaded handbook describes a proposed review procedure.",
        ["DOC-1-P3"],profile="PDF_GUIDANCE",language="en")
    assert refs==[]
    assert "Source caution" in text
    assert audit["selected_unreviewed_pdf_pages"]==1
    assert audit["cited_unreviewed_pdf_pages"]==0
    assert audit["unreviewed_pdf_warning_added"] is True
