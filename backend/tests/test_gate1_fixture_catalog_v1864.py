"""v186.4: acceptance checks for the strictly disposable Gate 1 scenario catalog."""
from pathlib import Path
import ast
from scripts.gate1_fixture_catalog_v1864 import QA_SCENARIOS
from scripts.seed_gate1_ci_v1862 import assert_local_postgres
from app.inbox_human_gate import gate1_pilot_readiness
from app.inbox_human_queue import CATEGORIES


def test_fictional_catalog_covers_gate1_quality_categories():
    keys = [item[0] for item in QA_SCENARIOS]
    assert len(keys) == 5 and len(set(keys)) == len(keys)
    assert {item[1] for item in QA_SCENARIOS} == {
        "UNCERTAIN", "IRRELEVANT", "RELEVANT", "HIGHLY_RELEVANT", None
    }
    assert all("Fictional" in item[3] or "fictional" in item[3]
               for item in QA_SCENARIOS)
    assert {"all", "unassessed", "uncertain", "excluded", "relevant"} <= CATEGORIES


def test_fixture_seeding_refuses_shared_database(monkeypatch):
    monkeypatch.setenv("BAWASLU_GATE1_ISOLATED_E2E", "YES")
    monkeypatch.setenv("BAWASLU_ALLOW_ISOLATED_DB_TEST", "YES")
    for url in (
        "postgresql://gate1qa:dummy@db.example.supabase.co:5432/bawaslu_gate1_pilot_ci",
        "postgresql://gate1qa:dummy@127.0.0.1:5432/postgres",
        "postgresql://other:dummy@127.0.0.1:5432/bawaslu_gate1_pilot_ci",
        "sqlite:///bawaslu.db",
    ):
        try:
            assert_local_postgres(url)
        except SystemExit as e:
            assert "REFUSED" in str(e)
        else:
            raise AssertionError("Unsafe seed target accepted: " + url)


def test_read_only_admin_preflight_diagnoses_empty_pilot():
    import inspect
    source = inspect.getsource(gate1_pilot_readiness)
    assert "pilot_empty_reason" in source
    assert "isolated_qa_fixture_required" in source
    assert "fixture_seeding_on_shared_db_supported" in source
    assert "linked_count == 0" in source


def test_ui_explains_empty_campaign_without_mutations():
    root = Path(__file__).resolve().parents[2]
    source = (root / "frontend/src/components/intel/InboxHumanReview.jsx").read_text()
    assert 'gate1-empty-campaign-diagnosis' in source
    assert 'pilotStatus.linked_source_count===0' in source
    assert 'Changing filters cannot reveal posts' in source


def test_fixture_generator_only_references_local_guard():
    source = (Path(__file__).resolve().parents[1] /
              "scripts/seed_gate1_ci_v1862.py").read_text()
    tree = ast.parse(source)
    funcs = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    assert "assert_local_postgres" in funcs
    assert "seed" in funcs
    assert "assert_local_postgres(url)" in ast.get_source_segment(source, funcs["seed"])
    assert 'CampaignEvidence(campaign_id=pilot.id, result_id=row.id' in source
    assert 'match_method="QA_SYNTHETIC"' in source
