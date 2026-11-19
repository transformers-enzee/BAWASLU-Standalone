from app.assistant_question_coverage import requested_topic_coverage


def test_missing_requested_topics_flagged():
    q = "Jelaskan pengamanan bukti, verifikasi fakta, tindak lanjut hukum, penugasan, dan duplikasi kasus."
    a = "Pengamanan bukti memerlukan URL dan catatan integritas."
    result = requested_topic_coverage(q, a)
    assert result["status"] == "NEEDS_REVIEW"
    assert "fact_verification" in result["missing_topics"]
    assert "legal_followup" in result["missing_topics"]
    assert "assignment" in result["missing_topics"]
    assert "duplicate_prevention" in result["missing_topics"]


def test_all_requested_topics_covered_only_lexically():
    q = "Uraikan penugasan, akses pengguna, dan pencegahan duplikasi kasus."
    a = "Penugasan diputuskan petugas. Viewer memiliki pembatasan akses. Hindari duplikasi kasus."
    result = requested_topic_coverage(q, a)
    assert result["status"] == "PASS_LEXICAL_ONLY"
    assert result["lexical_only"] is True


def test_simple_question_does_not_get_false_incomplete_warning():
    result = requested_topic_coverage("Apa arti penugasan?", "Tugas bagi petugas.")
    assert result["status"] == "NOT_APPLICABLE"


def test_social_analysis_omits_procedural_coverage_probe():
    result = requested_topic_coverage("Jelaskan penugasan dan akses pengguna.",
                                      "Analisis data", profile="SOCIAL_ANALYSIS")
    assert result["status"] == "NOT_APPLICABLE"


def test_question_echo_does_not_count_as_a_substantive_answer():
    question = "Jelaskan penugasan dan tindak lanjut hukum."
    answer = ("Pertanyaan Anda: Jelaskan penugasan dan tindak lanjut hukum.\n"
              "Tidak ada dokumen yang ditemukan.")
    result = requested_topic_coverage(question, answer)
    assert result["status"] == "NEEDS_REVIEW"
    assert set(result["missing_topics"]) == {"assignment", "legal_followup"}


def test_citation_only_answer_does_not_count_as_coverage():
    result = requested_topic_coverage(
        "Jelaskan penugasan dan tindak lanjut hukum.",
        "[DOC-1-P6]\n[DOC-1-P8]",
    )
    assert result["status"] == "NEEDS_REVIEW"


def test_explicit_source_limitation_still_counts_as_handling_topic():
    result = requested_topic_coverage(
        "Jelaskan penugasan dan tindak lanjut hukum.",
        "Penugasan tidak dapat ditentukan. Dasar hukum belum diverifikasi.",
    )
    assert result["status"] == "PASS_LEXICAL_ONLY"
    assert result["lexical_only"] is True


def test_mixed_moderation_and_legal_followup():
    result = requested_topic_coverage(
        "Bandingkan takedown dan tindak lanjut hukum.",
        "Moderasi platform tidak sama dengan dasar hukum pidana.",
    )
    assert result["status"] == "PASS_LEXICAL_ONLY"


def test_evidence_preservation_and_fact_verification():
    result = requested_topic_coverage(
        "Jelaskan pengamanan bukti dan verifikasi fakta.",
        "Simpan bukti. Fakta harus diverifikasi.",
    )
    assert result["status"] == "PASS_LEXICAL_ONLY"
