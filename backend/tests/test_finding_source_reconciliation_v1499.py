"""v149.9: conservative source-linked legal/platform assessment reconciliation."""
from app.finding_assessments import assess_finding

def post(id,text,platform="tiktok",url=None,campaign="11"):
    return {"canonical_source_id":f"social:{id}","result_id":str(id),
            "campaign_id":campaign,"platform":platform,
            "source_url":url if url is not None else f"https://example.invalid/{id}",
            "message_original":text}

def run(monkeypatch,rows):
    import app.finding_assessments as module
    retrieved=[]
    def fake_retrieve(db,permission,question,limit,semantic,reviewed_legal_only):
        retrieved.append((limit,semantic,reviewed_legal_only))
        return []
    monkeypatch.setattr(module,"retrieve_knowledge",fake_retrieve)
    result=assess_finding(None,{},{"id":"finding:19","players":["violations"],
                                  "supporting_posts":1,"posts":rows})
    return result,retrieved

def test_same_canonical_post_multiple_campaign_urls_counts_once(monkeypatch):
    a=post(101,"Ordinary public criticism",url="https://example.invalid/a")
    b=post(101,"Ordinary public criticism",url="https://example.invalid/b",campaign="12")
    result,retrieved=run(monkeypatch,[a,b])
    assert result["source_count_assessed"]==1
    assert result["source_provenance"]["duplicate_links_removed"]==1
    assert result["source_provenance"]["source_url_conflicts"]==1
    assert result["source_provenance"]["source_count_matches_finding"] is True
    assert result["platform_policy"]["status_counts"]=={"NO_DIRECT_SIGNAL_IDENTIFIED":1}
    assert retrieved==[(8,False,True)]
    assert result["legal"]["official_legal_verdict"] is False

def test_all_saved_variants_screened_without_multiplying_source_counts(monkeypatch):
    a=post(102,"Ordinary public criticism")
    b=post(102,"I will attack you",campaign="12")
    for order in ([a,b],[b,a]):
        result,_=run(monkeypatch,order)
        assert result["source_count_assessed"]==1
        assert result["source_provenance"]["source_text_conflicts"]==1
        assert result["platform_policy"]["status_counts"]=={"REVIEW_INDICATED":1}
        queue=result["platform_policy"]["potential_review_queue"]
        assert len(queue)==1
        assert queue[0]["source_text_conflict"] is True
        assert queue[0]["linked_source_variants"]==2
        assert "DIRECT_THREAT" in queue[0]["categories"]
        assert result["paid_provider_called"] is False

def test_reported_quote_variant_requires_context_review(monkeypatch):
    a=post(103,"I will attack you")
    b=post(103,"News reported: I will attack you")
    result,_=run(monkeypatch,[a,b])
    assert result["platform_policy"]["status_counts"]=={"CONTEXT_REVIEW_REQUIRED":1}
    assert result["platform_policy"]["platform_violation_confirmed"] is False

def test_non_http_original_urls_not_returned_as_actionable_source(monkeypatch):
    row=post(104,"I will attack you",url="javascript:alert(1)")
    result,_=run(monkeypatch,[row])
    assert result["source_provenance"]["missing_original_url"]==1
    assert result["platform_policy"]["potential_review_queue"][0]["source_url"]==""
    assert result["source_provenance"]["original_source_url_validation"]=="HTTP_OR_HTTPS_ONLY"
    assert result["follow_up"]["takedown_requested"] is False
