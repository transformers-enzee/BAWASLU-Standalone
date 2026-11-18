"""Static sanity checks for Social Listening campaign action dispatch."""
import ast
from pathlib import Path

def test_campaign_action_dispatch_python_syntax():
    path=Path(__file__).resolve().parents[1]/'app'/'socialcrawl.py'
    tree=ast.parse(path.read_text(),filename=str(path))
    assert tree is not None

def test_ai_worker_readiness_action_registered():
    path=Path(__file__).resolve().parents[1]/'app'/'socialcrawl.py'
    text=path.read_text()
    # Dispatch includes newer read-only diagnostics between the two actions.
    assert "'campaignAssessmentJobReconcile'" in text
    assert "'campaignAIWorkerReadiness'" in text
    assert "'campaignAssessmentOperationsOverview'" in text
    assert "from .campaigns import campaign_action" in text
