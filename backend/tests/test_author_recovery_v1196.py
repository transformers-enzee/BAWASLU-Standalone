"""Cross-platform author recovery safety and provenance regression checks."""
from types import SimpleNamespace
import json

from app.author_recovery import (
    clean_name, clean_handle, is_comment, source_candidate, recover_saved_author,
    display_author, _url_handle
)


def row(**kwargs):
    values = dict(author_name="UNKNOWN", observed_handle="", platform="facebook",
                  content_type="COMMENT", canonical_url="https://www.facebook.com/reel/123",
                  raw_payload_json="{}", source_identity_json="{}")
    values.update(kwargs)
    return SimpleNamespace(**values)


def test_missing_placeholders_and_domains_are_never_identities():
    for value in ("UNKNOWN","N/A","-","youtube.com","www.instagram.com","https://x.com/name",""):
        assert not clean_name(value)
        assert not clean_handle(value)


def test_facebook_parent_page_is_not_commenter():
    item = row(raw_payload_json=json.dumps({
        "Account":"UNKNOWN","Post URL":"https://www.facebook.com/123",
        "post":{"author":{"display_name":"Original Page"}},
        "source_items":[{"author":{"name":"Page Owner"}}]}),
        source_identity_json=json.dumps({"author":{"display_name":"Parent Page"}}))
    assert not recover_saved_author(item)[0]
    display, provenance = display_author(item)
    assert display=="Facebook commenter"
    assert provenance=="NOT_PROVIDED"


def test_public_comment_author_is_accepted_with_explicit_role():
    item = row(raw_payload_json=json.dumps({
        "type":"comment",
        "comment":{"author":{"display_name":"Visible commenter","username":"visible_com"}},
        "post":{"author":{"name":"Parent post creator"}}}))
    changed,reason = recover_saved_author(item)
    assert changed and reason=="comment_author_metadata"
    assert item.author_name=="Visible commenter"
    assert item.observed_handle=="@visible_com"
    assert json.loads(item.source_identity_json)["author_attribution"]["subject"]=="comment"
    assert not recover_saved_author(item)[0]


def test_same_text_different_people_is_never_identity_evidence():
    item = row(raw_payload_json=json.dumps({"Message":"Hello","Parent account":"Alice",
                                             "matched_text":"Hello","Account":"UNKNOWN"}))
    assert not recover_saved_author(item)[0]


def test_post_author_across_providers():
    for platform in ("youtube","instagram","tiktok","facebook","threads","twitter","reddit","linkedin","online_news"):
        display,handle,reason=source_candidate(platform,"POST",
            {"post":{"author":{"display_name":"Public Creator","username":"public_cre"}}},
            {},"", "https://example.org/post/123")
        assert display=="Public Creator"
        assert handle=="@public_cre"
        assert reason=="post_author_metadata"


def test_permalink_handles_only_for_post_identifiers():
    cases=[
        ("tiktok","https://www.tiktok.com/@source_cre/video/789","@source_cre"),
        ("threads","https://www.threads.com/@source_cre/post/abc","@source_cre"),
        ("twitter","https://x.com/source_cre/status/123456789","@source_cre"),
        ("youtube","https://youtube.com/watch?v=123",""),
        ("instagram","https://www.instagram.com/p/abc",""),
        ("facebook","https://www.facebook.com/reel/123","")
    ]
    for platform,url,expected in cases:
        assert _url_handle(url,platform)==expected


def test_post_permalink_not_used_as_comment_identity():
    author,_,reason=source_candidate("tiktok","COMMENT",{},
        {}, "@source_cre", "https://www.tiktok.com/@source_cre/video/789")
    assert author=="" and reason=="comment_identity_unavailable"


def test_existing_valid_name_not_overwritten():
    item=row(author_name="Current public author",raw_payload_json=json.dumps({
        "comment":{"author":{"name":"Different claimed author"}}}))
    assert not recover_saved_author(item)[0]
    assert item.author_name=="Current public author"


def test_handles_can_recover_source_post_but_not_domain():
    item=row(platform="threads",content_type="POST",
             observed_handle="@source_cre",
             canonical_url="https://www.threads.com/@source_cre/post/abc")
    assert recover_saved_author(item)[0]
    assert item.author_name=="@source_cre"
    invalid=row(platform="youtube",content_type="POST",
                observed_handle="youtube.com",canonical_url="https://youtube.com/watch?v=123")
    assert not recover_saved_author(invalid)[0]


def test_legacy_imported_unknown_remains_unresolved_without_source_identity():
    item=row(platform="facebook",content_type="COMMENT",
             raw_payload_json=json.dumps({"Account":"UNKNOWN","Message":"Claim",
                 "Direct URL":"https://www.facebook.com/reel/123",
                 "_id":"123_random-id"}))
    assert not recover_saved_author(item)[0]


def test_ui_requires_preview_and_explicit_saved_metadata_confirmation():
    from pathlib import Path
    import app.campaigns as campaigns
    source=Path(campaigns.__file__).read_text()
    assert "campaignAuthorRecoveryPreview" in source
    assert "campaignAuthorRecoveryApply" in source
    assert "confirm_saved_metadata_only" in source
    assert "paid_provider_called':False" in source
    assert "if not _editable(p,c)" in source
    assert "_result_in_scope(db,p,item)" in source
