from app.external_import_ingest import parse_row
def test_post_identity_and_provenance():
    row=parse_row({'Source':'YouTube','_id':'abc','Message':'An example','Direct URL':'https://example.com/a','Post time':'2026-10-01'})
    assert row['provider_result_id']=='abc'
    assert row['content_type']=='POST'
def test_comment_with_shared_parent_url():
    row=parse_row({'Source':'facebook','_id':'comment-1','Message':'A comment','Direct URL':'https://example.com/p','Comment URL':'https://example.com/c','Post URL':'https://example.com/p'})
    assert row['content_type']=='COMMENT'
    assert row['parent_url']=='https://example.com/p'
def test_skip_missing_content():
    assert parse_row({'Source':'x','_id':'abc','Message':'','Direct URL':'https://x.com/a'}) is None
