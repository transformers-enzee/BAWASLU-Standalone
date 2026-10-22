"""No-cost, offline regression checks for the AI assessment prompt contract.

Run: python -m unittest discover -s backend/tests -p 'test_assessment_readiness_contract.py'
This suite does NOT contact an AI service or mutate a database.
"""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCREEN = (ROOT / "app" / "auto_relevance.py").read_text(encoding="utf-8")
APP = (ROOT / "app" / "main.py").read_text(encoding="utf-8")


class AssessmentReadinessContract(unittest.TestCase):
    def test_campaign_context_is_in_payload(self):
        for expression in (
            "'name':campaign.name",
            "'objective':campaign.description",
            "'main_keywords':_arr(campaign.primary_keywords_json)",
            "'secondary_keywords':_arr(campaign.secondary_keywords_json)",
            "'excluded_keywords':_arr(campaign.excluded_keywords_json)",
        ):
            with self.subTest(expression=expression):
                self.assertIn(expression, SCREEN)

    def test_admin_relevance_gates_are_active_and_independent(self):
        for expression in (
            "RelevanceGateQuestion.active==True",
            "'required_answer':q.required_answer",
            "val=by_id.get(gate.id,{})",
            "val.get('answer','UNCERTAIN')",
            "answer!=gate.required_answer",
            "return 'UNCERTAIN' if model_label=='RELEVANT' else model_label",
            "resolve_relevance_gates(label,gate_results)",
        ):
            with self.subTest(expression=expression):
                self.assertIn(expression, SCREEN)

    def test_keyword_match_is_not_enough(self):
        self.assertIn("A generic or unrelated keyword by itself is NOT evidence", SCREEN)
        self.assertIn("FIRST assess topical relevance", SCREEN)
        self.assertIn("actual campaign objective", SCREEN)

    def test_potential_violations_are_evidence_grounded(self):
        self.assertIn("validated_actor_issue_signals(", SCREEN)
        self.assertIn("validated_reported_incident_signals(", SCREEN)
        self.assertIn("No issue signal is a legal finding", SCREEN)

    def test_paid_auto_worker_is_opt_in(self):
        self.assertIn("BAWASLU_AUTO_AI_SCREENING_ENABLED", APP)
        self.assertIn("BAWASLU_AI_WORKER_ENABLED", APP)
        self.assertIn("if not os.getenv('OPENAI_API_KEY','').strip()", SCREEN)

    def test_gate_answers_are_persisted(self):
        self.assertIn("RelevanceGateAnswer(assessment_id=record.id", SCREEN)
        self.assertIn("question_snapshot=gate.question", SCREEN)

if __name__ == "__main__":
    unittest.main()
