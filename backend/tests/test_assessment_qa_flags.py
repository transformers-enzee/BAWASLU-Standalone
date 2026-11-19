from app.assessment_qa_flags import relevance_explanation_flags


def test_false_election_absence_rationale_is_flagged_for_review():
    flags = relevance_explanation_flags(
        "Wapres untuk calon yang kalah pilpres",
        "IRRELEVANT",
        "The content does not discuss electoral processes or candidates.",
    )
    assert "EXPLANATION_CONTRADICTS_ELECTION_MENTION" in flags
    assert "ELECTION_MENTION_DISMISSED" in flags


def test_election_mention_alone_is_not_automatic_relevance():
    assert relevance_explanation_flags(
        "A historical discussion of pilpres",
        "IRRELEVANT",
        "Historical discussion does not match this monitoring campaign's present scope.",
    ) == ["ELECTION_MENTION_DISMISSED"]


def test_clear_non_election_item_has_no_flag():
    assert relevance_explanation_flags(
        "An environmental haze discussion",
        "IRRELEVANT",
        "No matching election-monitoring subject.",
    ) == []


def test_uncertain_but_election_absence_claim_needs_review():
    assert "UNCERTAIN_EXPLANATION_OMITS_ELECTION_MENTION" in relevance_explanation_flags(
        "Debat Pilpres 2024",
        "UNCERTAIN",
        "Lacks explicit electoral relevance or context.",
    )


def test_missing_explanation_is_reviewed_without_overriding():
    assert relevance_explanation_flags("Gibran", "RELEVANT", "") == ["MISSING_EXPLANATION"]
