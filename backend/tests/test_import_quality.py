from app.import_quality import social_quality, radar_quality

def test_social_complete_source():
    result=social_quality({"id":101,"canonical_url":"https://example.org/source",
        "platform":"threads","published_at":"2026-10-28T00:00:00Z",
        "text_content":"Recorded content","observed_handle":"@public"})
    assert result.source_id=="social:101"
    assert not result.requires_manual_review
    assert result.missing_fields==()

def test_missing_publication_not_filled_with_collection_date():
    result=social_quality({"id":154,"canonical_url":"https://example.org/source",
        "platform":"instagram","published_at":"","collected_at":"2026-10-28T00:00:00Z",
        "text_content":"Recorded content","author_name":"A public account"})
    assert result.missing_fields==("published_at",)
    assert result.requires_manual_review

def test_missing_provider_id_does_not_invalidate_canonical_row_id():
    result=social_quality({"id":9,"canonical_url":"https://example.org/source",
        "platform":"x","published_at":"2026-10-28","text_content":"Recorded",
        "author_name":"Public","provider_result_id":""})
    assert result.source_id=="social:9"
    assert not result.requires_manual_review

def test_radar_source_completeness_and_namespace():
    row={"pilot_post_id":"P-109","source_url":"https://example.org/radar",
        "platform":"Instagram","published_at_raw":"2026-10-27",
        "message_original":"Original message","account_raw":"@public"}
    assert radar_quality(row).source_id=="radar:P-109"
    assert radar_quality(row).missing_fields==()
    row["message_original"]=""
    assert radar_quality(row).missing_fields==("content",)

def test_social_result_api_marks_missing_publication_without_inference():
    from types import SimpleNamespace
    from datetime import datetime
    from app.socialcrawl import serialize_result
    row=SimpleNamespace(id=101,run_id=1,provider="stored",provider_result_id="",
      platform="threads",content_type="post",canonical_url="https://example.org/p",
      author_name="Public account",observed_handle="",published_at="",
      text_content="Original",language="id",relevance_score=0,
      engagement_json="{}",geography_json="{}",source_identity_json="{}",
      watchlist_matches_json="[]",review_state="MONITOR",review_notes="",
      promoted_intelligence_id=None,collected_at=datetime(2026,10,28))
    record=serialize_result(row)
    assert record["canonical_source_id"]=="social:101"
    assert record["provenance_quality"]["missing_fields"]==["published_at"]
    assert record["provenance_quality"]["publication_time_verified"] is False
    assert record["provenance_quality"]["provider_id_available"] is False
    assert record["published_at"]==""
    assert record["collected_at"].startswith("2026-10-28")
