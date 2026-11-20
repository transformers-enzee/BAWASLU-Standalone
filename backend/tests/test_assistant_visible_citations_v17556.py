from app.assistant_visible_citations import audit_visible_assistant_parts

def evidence(i,kind="SOCIAL_LISTENING"):
    return {"record_id":i,"record_type":kind,"source_excerpt":"sample text"}

def test_findings_citations_are_counted_when_main_summary_has_no_brackets():
    q="Apa kritik terhadap BAWASLU?"
    findings={"observations":["SOCIAL-907 menyebut BAWASLU dalam kritik [SOCIAL-907]."],
              "review_steps":["Periksa konteks unggahan asli."]}
    text,cited,audit,clean=audit_visible_assistant_parts(
        q,[evidence("SOCIAL-907")],"Satu unggahan perlu ditelaah.",["SOCIAL-907"],findings)
    assert cited==["SOCIAL-907"]
    assert audit["displayed_citation_count"]==1
    assert audit["citation_scope"]=="VISIBLE_ANSWER_AND_FINDINGS"
    assert "tidak mencantumkan kutipan" not in text
    assert clean["observations"][0].endswith("[SOCIAL-907].")

def test_unavailable_ids_removed_from_findings_as_well():
    findings={"observations":["Klaim [SOCIAL-999] tanpa dasar [SOCIAL-907]."],
              "review_steps":[]}
    _,cited,audit,clean=audit_visible_assistant_parts(
        "analisis",[evidence("SOCIAL-907")],"Ringkasan.",[],findings)
    assert cited==["SOCIAL-907"]
    assert "SOCIAL-999" not in clean["observations"][0]
    assert audit["rejected_unavailable_citations"]==1

def test_uncited_visible_response_keeps_existing_warning():
    text,cited,audit,clean=audit_visible_assistant_parts(
        "analisis",[evidence("SOCIAL-907")],"Kesimpulan tanpa kutipan.",[],
        {"observations":["Tidak ada ID"],"review_steps":[]})
    assert cited==[]
    assert audit["displayed_citation_count"]==0
    assert "Catatan bukti:" in text
    assert clean["observations"]==["Tidak ada ID"]

def test_without_separate_findings_keeps_pdf_guidance_contract():
    text,cited,audit,findings=audit_visible_assistant_parts(
        "Panduan",[evidence("DOC-1-P1","PDF_KNOWLEDGE")],
        "Rujukan [DOC-1-P1].",["DOC-1-P1"],None,profile="PDF_GUIDANCE")
    assert cited==["DOC-1-P1"]
    assert findings is None

def test_quality_evaluator_counts_citations_in_visible_findings():
    from app.assistant_answer_quality import evaluate_answer_quality
    from app.assistant_visible_citations import visible_assistant_text
    q="Apa kritik terhadap BAWASLU?"
    findings={"observations":["Kritik terhadap BAWASLU [SOCIAL-907]."],
              "review_steps":["Buka unggahan asli."]}
    text,cited,audit,clean=audit_visible_assistant_parts(
        q,[evidence("SOCIAL-907")],"Unggahan perlu verifikasi.",[],findings)
    quality=evaluate_answer_quality(
        q,[evidence("SOCIAL-907")],visible_assistant_text(text,clean),
        cited,grounding=audit)
    checks={x["id"]:x["status"] for x in quality["checks"]}
    supplemental={x["id"]:x["status"] for x in quality["additional_checks"]}
    assert checks["citation_grounding"]=="PASS"
    # Preserve the stable four-core-check API: inventory integrity is an
    # additional diagnostic, never silently merged into the core score.
    assert "citation_inventory_consistency" not in checks
    assert supplemental["citation_inventory_consistency"]=="PASS"
    assert quality["citation_inventory_consistency"]["status"]=="PASS_IDENTIFIERS_ONLY"
    assert quality["supplemental_review_required"] is False or (
        "citation_inventory_consistency" not in quality["additional_needs_review"])


def test_legal_safety_notices_are_not_hidden_in_collapsed_steps():
    findings={"observations":["Catatan belum terverifikasi [SOCIAL-907]."],
              "review_steps":["Periksa sumber sebelum tindakan."]}
    text,cited,audit,clean=audit_visible_assistant_parts(
        "Bagaimana penanganan?",[evidence("SOCIAL-907")],
        "Pelaku wajib ditangkap.",["SOCIAL-907"],findings)
    assert cited==["SOCIAL-907"]
    assert "Peringatan tindakan hukum:" in text
    assert "Peringatan tindakan hukum:" not in " ".join(clean["review_steps"])
    assert audit["appended_safety_notices"]
    assert clean["review_steps"]==["Periksa sumber sebelum tindakan."]


def test_findings_reject_unknown_ids_in_quality_inventory():
    from app.assistant_answer_quality import evaluate_answer_quality
    from app.assistant_visible_citations import visible_assistant_text
    findings={"observations":["Tinjau [SOCIAL-999] dan [SOCIAL-907]."],
              "review_steps":[]}
    text,cited,audit,clean=audit_visible_assistant_parts(
        "Kritik BAWASLU",[evidence("SOCIAL-907")],"Bukti terbatas.",
        ["SOCIAL-999","SOCIAL-907"],findings)
    assert "SOCIAL-999" not in visible_assistant_text(text,clean)
    quality=evaluate_answer_quality(
        "Kritik BAWASLU",[evidence("SOCIAL-907")],
        visible_assistant_text(text,clean),cited,grounding=audit)
    checks={x["id"]:x["status"] for x in quality["checks"]}
    assert checks["citation_grounding"]=="REVIEW_REQUIRED"
    assert audit["rejected_unavailable_citations"]==1
