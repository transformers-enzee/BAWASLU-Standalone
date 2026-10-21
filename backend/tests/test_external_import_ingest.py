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

def test_platform_from_post_url():
    assert parse_row({'_id':'a','Message':'text','Post URL':'https://www.instagram.com/p/ABC/'})['platform']=='instagram'
def test_platform_from_short_url():
    assert parse_row({'_id':'b','Message':'text','Post URL':'https://youtu.be/abc'})['platform']=='youtube'
def test_reject_undetected_platform():
    assert parse_row({'_id':'c','Message':'text','Post URL':'https://example.com/a'}) is None


def test_zocialeye_type_comment_without_comment_url():
    from app.external_import_ingest import parse_row
    item=parse_row({'Source':'instagram','_id':'comment-a','Message':'reply','Type':'comment','Post URL':'https://instagram.com/p/abc'})
    assert item['content_type']=='COMMENT'
    assert item['parent_url']=='https://instagram.com/p/abc'
