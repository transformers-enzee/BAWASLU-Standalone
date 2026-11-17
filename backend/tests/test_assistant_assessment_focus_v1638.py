"""Officer-focused scope checks are instructions, not legal adjudication."""
import pytest
from app.assistant_assessment_focus import assessment_scope, assessment_instruction, assessment_authority_inventory

@pytest.mark.parametrize("question,expected",[
 ("Does the Instagram post violate platform community guidelines?","PLATFORM_ONLY"),
 ("Apakah konten TikTok melanggar kebijakan platform?","PLATFORM_ONLY"),
 ("Apa tindak lanjut hukum berdasarkan pasal ini?","LEGAL_ONLY"),
 ("What election law and Instagram platform policy might apply?","MIXED_LEGAL_AND_PLATFORM"),
 ("Bagaimana pelanggaran hukum dan aturan komunitas TikTok dinilai?","MIXED_LEGAL_AND_PLATFORM"),
 ("Show Instagram activity by week","GENERAL"),
 ("Summarize TikTok sentiment","GENERAL"),
 ("Who is mentioned?","GENERAL"),
 ("What public concerns about BAWASLU were reported?","GENERAL"),
])
def test_narrow_question_router(question,expected):
 assert assessment_scope(question)==expected

def test_specific_observation_rule_gaps_next_check():
 prompt=assessment_instruction("What election law and Instagram platform policy might apply?","CASE_REVIEW")
 for token in ("OBSERVED RECORD","POSSIBLE RULE","EVIDENCE GAPS","OFFICER NEXT CHECK",
               "An internal legal PDF cannot establish","automatic takedown","direct_answer"):
  assert token in prompt
 assert assessment_instruction("Summarize sentiment","SOCIAL_ANALYSIS")==""

def test_pdf_guidance_keeps_document_only_authority():
 s=assessment_instruction("What legal provision applies?","PDF_GUIDANCE")
 assert "only supplied PDF_KNOWLEDGE excerpts" in s
 assert "text/currentness is unverified" in s

def test_inventory_is_explicitly_unverified():
 x=assessment_authority_inventory([
  {"record_type":"SOCIAL_LISTENING"},
  {"record_type":"FORMAL_INTELLIGENCE"},
  {"record_type":"PDF_KNOWLEDGE","document_type":"REGULATION"},
  {"record_type":"PDF_KNOWLEDGE","document_type":"REPORT"}])
 assert (x["social_post_count"],x["formal_intelligence_count"],x["legal_reference_page_count"],x["contextual_pdf_page_count"])==(1,1,1,1)
 assert x["official_policy_currentness_verified"] is False
 assert x["legal_applicability_verified"] is False
 assert x["source_truth_verified"] is False
