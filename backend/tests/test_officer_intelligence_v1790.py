"""Offline QA for objective coverage and legal reference integrity."""
from app.officer_action_v3 import intelligence_coverage as coverage, legal, research

def test_objectives_use_independent_repository_targets():
    assert "Satu Data" in coverage.alternate_focus("national statistics")
    assert "JDIH" in coverage.alternate_focus("legal instruments")
    assert "decisions" in coverage.alternate_focus("candidate cases")
    assert "alternative" in coverage.alternate_focus("unrecognized objective")

def test_coverage_profiles_distinguish_readable_official_and_document():
    rows = [{"read_status":"READ","kind":"OFFICIAL","document_type":"PDF","url":"https://bawaslu.go.id/a"},
            {"read_status":"READ","kind":"PUBLIC_REPORT","document_type":"HTML","url":"https://example.com/b"},
            {"read_status":"SNIPPET_ONLY","kind":"OFFICIAL","url":"https://bawaslu.go.id/c"}]
    result=coverage.evidence_profile(rows)
    assert result=={"read_count":2,"official_read_count":1,"document_read_count":1,"distinct_hosts":2,"failed_read_count":1}

def test_wrong_article_cannot_be_matched_even_with_real_excerpt():
    source={"id":"P-1","kind":"OFFICIAL","read_status":"READ","url":"https://jdih.bawaslu.go.id/peraturan/test.pdf",
            "excerpt":"Pasal 99 Synthetic provision only, not real law."}
    row={"legal_reference":"Pasal 100","source_quote":source["excerpt"],"source_ids":["P-1"]}
    assert not legal.review_legal([row],[source])[0]["primary_text_excerpt_matched"]
    assert coverage.matching_article("Article 99","Pasal 99 Synthetic provision")
    assert not coverage.matching_article("Pasal 99 and Pasal 100","Pasal 99 Synthetic provision")

def test_narrative_citation_coverage_does_not_claim_semantic_verification():
    source={"id":"P-1","read_status":"READ"}
    answer=("A synthetic report paragraph with sufficient length to test coverage without asserting a legal or factual result. [P-1]\n\n"
            "A second synthetic report paragraph with an invented reference that must not count as a valid readable source. [P-9]")
    out=coverage.narrative_citation_audit(answer,[source])
    assert out["substantive_blocks"]==2
    assert out["blocks_with_read_source_links"]==1
    assert out["semantic_claim_verification"] is False
