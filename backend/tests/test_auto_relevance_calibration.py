"""Offline regression checks for contextual relevance guardrails."""
from app.auto_relevance import normalize_relevance_label, RELEVANCE_SCREENING_INSTRUCTIONS

def test_unknown_labels_are_uncertain_not_auto_relevant():
    assert normalize_relevance_label({'relevance_label':'UNASSESSED'})=='UNCERTAIN'
    assert normalize_relevance_label({})=='UNCERTAIN'
    assert normalize_relevance_label({'relevance_label':' relevant '})=='RELEVANT'

def test_relevance_and_violation_are_independent():
    assert 'No flagged category does NOT make a post irrelevant' in RELEVANCE_SCREENING_INSTRUCTIONS
    assert 'Foreign elections unrelated to the campaign are IRRELEVANT' in RELEVANCE_SCREENING_INSTRUCTIONS

def test_insufficient_context_guidance():
    assert 'hashtags-only' in RELEVANCE_SCREENING_INSTRUCTIONS
    assert 'use UNCERTAIN' in RELEVANCE_SCREENING_INSTRUCTIONS
