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
