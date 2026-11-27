"""v185.1: Officer-review QA samples must include false negatives and preserve scope."""
from types import SimpleNamespace
from pathlib import Path
from app.governance_information_qa import classify_information, information_qa_sample
import inspect


def row(**kwargs):
    return SimpleNamespace(**kwargs)


def test_unassessed_post_is_reported_without_violation_signal():
    result=classify_information(None)
    assert result["category"]=="unassessed"
    assert result["action"]=="VERIFY_UNASSESSED"
    assert result["review_recorded"] is False


def test_uncertain_and_irrelevant_are_not_silently_excluded():
    uncertain=classify_information(row(relevance_label="UNCERTAIN",sentiment="NEUTRAL",model_version="stable"))
    irrelevant=classify_information(row(relevance_label="IRRELEVANT",sentiment="NEUTRAL",model_version="stable"))
    assert uncertain["action"]=="REVIEW_UNCERTAIN"
    assert irrelevant["action"]=="SPOT_CHECK_EXCLUDED"
    assert uncertain["category"]==irrelevant["category"]=="excluded_or_uncertain"


def test_pending_model_output_is_not_treated_as_final_assessment():
    pending=classify_information(row(relevance_label="RELEVANT",sentiment="POSITIVE",model_version="PRISM_PENDING_OPENAI"))
    assert pending["category"]=="unassessed"


def test_legacy_officer_sentiment_takes_precedence_without_rewriting_ai_value():
    result=classify_information(row(relevance_label="RELEVANT",sentiment="NEGATIVE",model_version="stable",
                                    relevance_confidence="0.82",assessment_version=2),
                                row(sentiment="NEUTRAL"),row(decision="FLAG_DISMISSED"))
    assert result["ai_sentiment"]=="NEGATIVE"
    assert result["effective_sentiment"]=="NEUTRAL"
    assert result["sentiment_basis"]=="OFFICER_CORRECTION"
    assert result["review_recorded"] is True


def test_sampling_query_excludes_watchlist_only_and_requires_source_scope():
    source=inspect.getsource(information_qa_sample)
    assert 'CampaignEvidence.match_method!="WATCHLIST_ACCOUNT"' in source
    assert "_result_in_scope(db,officer_profile,posts[source_id])" in source
    assert "SCAN_LIMIT + 1" in source
    assert "not_population_totals" in source
    assert "balanced_review_sample" in source


def test_gate1_qa_is_exposed_from_scoped_admin_campaign_summary():
    from app.governance_persistence import governance_qa_campaign_summary
    source=inspect.getsource(governance_qa_campaign_summary)
    assert '_grant(db,user,"administration")' in source
    assert '_campaign(db,p,campaign_id)' in source
    assert '"information_qa":information' in source


def test_ui_has_direct_inbox_evidence_link_and_no_mutating_gate1_button():
    frontend=Path(__file__).resolve().parents[2]/"frontend"/"src"/"pages"/"GovernanceReview.jsx"
    source=frontend.read_text()
    assert 'data-testid="governance-information-qa"' in source
    assert "'/inbox?gate1=1&campaign_id='" in source
    assert "encodeURIComponent(item.result_id)" in source
    assert "SPOT_CHECK_EXCLUDED" in source
