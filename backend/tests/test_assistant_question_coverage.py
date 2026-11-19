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
