"""Hybrid assistant retrieval, source citation and no-data regression QA."""
from app.assistant_orchestration import (
    _social_select, social_evidence, social_record_view,
    is_conceptual, _safe_output, evidence_fallback, answer_text
)

def _row(i, text, relevance="RELEVANT"):
    return {"id":str(i),"text_content":text,"relevance_label":relevance,
            "campaign_name":"BAWASLU","platform":"TikTok",
            "canonical_url":"https://example.org/post/" + str(i),
            "author_name":"Example", "topic_labels":["Electoral Operations"]}

def test_social_retrieval_respects_relevance_and_query():
    rows=[_row(1,"Gibran election campaign finance"),
          _row(2,"Gibran other claim","IRRELEVANT"),
          _row(3,"unrelated culinary post")]
    selected,count=_social_select(rows,"Gibran campaign")
    assert count==1 and [x["id"] for x in selected]==["1"]

def test_source_card_retains_original_link():
    item=_row(42,"BAWASLU oversight report")
    evidence=social_evidence(item)
    card=social_record_view(item)
    assert evidence["record_id"]=="SOCIAL-42"
    assert evidence["verification_status"]=="UNVERIFIED_SOCIAL_SOURCE"
    assert card["record_type"]=="SOCIAL_LISTENING"
    assert card["source_url"].endswith("/42")

def test_general_vs_evidence_intent():
    assert is_conceptual("Apa tugas Bawaslu?")
    assert is_conceptual("What is an election?")
    assert not is_conceptual("Apa isu utama tentang Gibran minggu ini?")

def test_model_may_not_cite_unknown_record_ids():
    parsed=_safe_output({
      "direct_answer":"Supported [SOCIAL-1], unsupported [SOCIAL-999]",
      "interpretation":"",
      "observations":["See [SOCIAL-1]","Bad [INT-FAKE]"],
      "next_checks":[],"limitations":[],
      "cited_ids":["SOCIAL-1","SOCIAL-999"]
    },{"SOCIAL-1"})
    assert parsed["cited_ids"]==["SOCIAL-1"]
    assert "[SOCIAL-999]" not in parsed["direct_answer"]
    assert "[INT-FAKE]" not in parsed["observations"][1]

def test_fallback_never_invents_findings():
    answer,ids=evidence_fallback([social_evidence(_row(9,"Candidate statement"))],"timeout")
    assert ids==[]
    assert "analysis could not be completed" in answer.lower()
    assert "retry" in answer.lower()
    assert "SOCIAL-9" not in answer

def test_structured_answer_is_readable():
    text=answer_text({"direct_answer":"Ringkasan","observations":["Bukti [SOCIAL-1]"],
        "interpretation":"Pola belum terverifikasi","next_checks":["Periksa sumber"],
        "limitations":["Sampel terbatas"]},True)
    assert "[SOCIAL-1]" in text and "TEMUAN UTAMA" not in text


def test_broad_narrative_question_retrieves_recent_sample_when_no_literal_keywords():
    rows=[_row(11,"Prabowo gives speech at election rally"),
          _row(12,"Local polling administration discussed")]
    selected,count=_social_select(rows,"What are the main emerging narratives?")
    assert count==2 and len(selected)==2


def test_cross_module_formal_count_recognizes_source_identifiers_and_types():
    from app.assistant_orchestration import formal_evidence_count
    records=[
        {"record_id":"INT-2026-000099","title":"Saved case"},
        {"record_id":"SOCIAL-42","record_type":"SOCIAL_LISTENING"},
        {"record_id":"DOC-1-P6","record_type":"PDF_KNOWLEDGE"},
        {"record_id":"INT-2026-000100","record_type":"FORMAL_INTELLIGENCE"},
    ]
    assert formal_evidence_count(records)==2
    assert formal_evidence_count(records[1:3])==0


def test_pdf_multisection_reply_completes_missing_moderation_from_actual_page_only():
    from app.assistant_orchestration import complete_pdf_moderation_comparison
    prompt=("Berdasarkan PDF, jelaskan penanganan dugaan pelanggaran hukum "
            "dan bedakan dengan moderasi konten berdasarkan aturan platform.")
    excerpts=[
        {"record_id":"DOC-1-P6","record_type":"PDF_KNOWLEDGE",
         "source_excerpt":"Tindak lanjut dugaan pelanggaran hukum membutuhkan pengamanan bukti."},
        {"record_id":"DOC-1-P7","record_type":"PDF_KNOWLEDGE",
         "source_excerpt":("Aturan platform dan moderasi: Pelanggaran hukum dan "
                           "pelanggaran ketentuan platform adalah dua pertanyaan "
                           "berbeda. Tentukan platform, kebijakan resmi, dan kanal peninjauan.")},
    ]
    answer,citations=complete_pdf_moderation_comparison(
        prompt,excerpts,"Registrasi bukti dan periksa kewenangan [DOC-1-P6]",
        ["DOC-1-P6"],"id")
    assert "Moderasi platform berbeda" in answer
    assert "DOC-1-P7" in answer
    assert "\n\n**Moderasi platform" in answer
    assert "\\\\n" not in answer
    assert citations==["DOC-1-P6","DOC-1-P7"]
    assert "Social Listening" not in answer
    # Never fill a legal question from an unrelated PDF page.
    short,refs=complete_pdf_moderation_comparison(
        prompt,excerpts[:1],"Langkah awal [DOC-1-P6]",["DOC-1-P6"],"id")
    assert "tidak dapat dijawab" in short
    assert refs==["DOC-1-P6"]
    # No duplication if the model already answered both requested topics.
    complete=("**Moderasi platform:** berbeda dari penanganan hukum yang "
              "memerlukan bukti dan pemeriksaan kewenangan. Untuk moderasi "
              "konten platform, periksa kebijakan platform yang berlaku, "
              "bandingkan unggahan dengan aturan tersebut, dan gunakan "
              "kanal peninjauan resmi jika diperlukan. [DOC-1-P7]")
    untouched,refs=complete_pdf_moderation_comparison(
        prompt,excerpts,complete,["DOC-1-P7"],"id")
    assert untouched==complete and refs==["DOC-1-P7"]
    # A bare mention of a platform rule does not explain the requested distinction.
    shallow=("Penanganan hukum memerlukan bukti; moderasi menilai aturan "
             "platform menurut kebijakan platform. [DOC-1-P7]")
    expanded,refs=complete_pdf_moderation_comparison(
        prompt,excerpts,shallow,["DOC-1-P7"],"id")
    assert expanded!=shallow
    assert "Moderasi platform berbeda" in expanded
    # A PDF answer not asking about moderation is left exactly as generated.
    plain,refs=complete_pdf_moderation_comparison(
        "Jelaskan proses registrasi informasi awal.",excerpts,
        "Registrasikan informasi [DOC-1-P6]",["DOC-1-P6"],"id")
    assert plain=="Registrasikan informasi [DOC-1-P6]"
    assert refs==["DOC-1-P6"
    ]


def test_pdf_moderation_complete_realworld_retest_has_no_duplicate_appendix():
    from app.assistant_orchestration import (
        complete_pdf_moderation_comparison,pdf_moderation_section_is_complete)
    question=("Berdasarkan dokumen PDF, jelaskan penanganan dugaan pelanggaran "
              "hukum dan bedakan proses itu dari moderasi konten berdasarkan "
              "kebijakan platform media sosial.")
    excerpts=[{"record_type":"PDF_KNOWLEDGE","record_id":"DOC-1-P6",
               "source_excerpt":"Langkah penanganan dugaan pelanggaran hukum."},
              {"record_type":"PDF_KNOWLEDGE","record_id":"DOC-1-P7",
               "source_excerpt":"Moderasi dan aturan platform berbeda dari "
                                "pelanggaran hukum; kaji ketentuan platform."}]
    original=(
        "Dokumen tersebut secara eksplisit berstatus simulasi untuk uji AI, "
        "bukan SOP resmi Bawaslu. [DOC-1-P6]\\n\\n"
        "**Penanganan awal dugaan pelanggaran hukum:** Registrasikan informasi "
        "awal, amankan teks, media dan URL, verifikasi aktor dan lokasi, lalu "
        "petugas berwenang memeriksa aturan pemilu relevan. [DOC-1-P6]\\n\\n"
        "**Moderasi konten platform:** ini merupakan proses yang berbeda dari "
        "penanganan hukum. Platform harus diidentifikasi, kebijakan resminya "
        "yang terbaru diperoleh dari sumber primer, kategori pelanggaran "
        "dibandingkan dengan konten asli, dan bukti atau konteks yang masih "
        "kurang dicatat. Bila diperlukan, permintaan peninjauan diajukan "
        "melalui kanal resmi platform, sementara pengamanan bukti dan kajian "
        "hukum tetap dipisahkan. [DOC-1-P7]"
    )
    assert pdf_moderation_section_is_complete(original)
    final,refs=complete_pdf_moderation_comparison(
        question,excerpts,original,["DOC-1-P6","DOC-1-P7"],"id")
    assert final==original
    assert refs==["DOC-1-P6","DOC-1-P7"]
    assert final.count("**Moderasi") == 1
    # Mere mention of 'moderasi platform' does not pass a detailed comparison.
    partial="Moderasi platform perlu ditinjau. [DOC-1-P7]"
    assert not pdf_moderation_section_is_complete(partial)
    completed,refs=complete_pdf_moderation_comparison(
        question,excerpts,partial,["DOC-1-P7"],"id")
    assert completed!=partial
    assert "Moderasi platform berbeda" in completed
    assert refs==["DOC-1-P7"]
    # A concise English discussion with evidence-backed contrast is enough.
    english=("Platform moderation is a separate process from handling an "
             "election-law allegation. Check the platform's current policy "
             "against the original content, review supporting context, and "
             "use the official appeal channel if necessary. [DOC-1-P7]")
    assert pdf_moderation_section_is_complete(english)
