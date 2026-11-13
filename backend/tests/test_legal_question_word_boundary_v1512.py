"""v151.2: standalone legal-word detection and false-positive boundaries."""
from app.assistant_grounding import audit_assistant_answer

def audit(question):
    _,_,meta=audit_assistant_answer(
        question,[],"Review the available evidence.",profile="SOCIAL_ANALYSIS",
        language="en")
    return meta

def test_standalone_law_requires_source_readiness_review():
    for question in ["Explain the applicable law",
                     "What law applies to this incident?",
                     "What are the relevant laws?",
                     "Does election law apply?",
                     "Jelaskan hukum yang berlaku"]:
        result=audit(question)
        assert result["legal_question"] is True
        assert result["evidence_citation_coverage"]=="LEGAL_REFERENCE_NOT_CITED"
        assert result["human_review_required"] is True
        assert result["officer_review_steps"][0]["code"]=="LOCATE_AUTHORIZED_LEGAL_REFERENCE"

def test_nonlegal_workflow_questions_do_not_generate_legal_tasks():
    for question in ["Explain the workflow",
                     "Show the social posts",
                     "Summarize candidate mentions",
                     "Review the dashboard",
                     "How many captured posts?"]:
        result=audit(question)
        assert result["legal_question"] is False
        assert result["human_review_required"] is False
        assert result["officer_review_steps"]==[]
