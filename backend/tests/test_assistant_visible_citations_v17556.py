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
