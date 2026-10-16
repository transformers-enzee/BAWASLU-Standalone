from app.thumbnail_cache import _allowed_image_host

def test_image_cache_rejects_untrusted_and_insecure_image_urls():
    assert _allowed_image_host('https://instagram.fkiv8-1.fna.fbcdn.net/photo.jpg')
    assert _allowed_image_host('https://p16-common-sign.tiktokcdn-us.com/cover.jpeg')
    assert not _allowed_image_host('http://instagram.fkiv8-1.fna.fbcdn.net/photo.jpg')
    assert not _allowed_image_host('https://fakefbcdn.net/photo.jpg')
    assert not _allowed_image_host('https://localhost/photo.jpg')
    assert not _allowed_image_host('https://fbcdn.net.evil.example/photo.jpg')
    assert not _allowed_image_host('https://user:password@fbcdn.net/photo.jpg')


def test_thumbnail_diagnostics_reject_untrusted_url_without_network():
    from app.thumbnail_cache import cache_thumbnail_diagnostic
    from types import SimpleNamespace
    class Empty:
        def get(self,model,key): return None
    item=SimpleNamespace(id=42)
    assert cache_thumbnail_diagnostic(Empty(),item,'')=='no_valid_url'
    assert cache_thumbnail_diagnostic(Empty(),item,'https://example.com/a.jpg')=='unsupported_host'
    assert cache_thumbnail_diagnostic(Empty(),item,'https://p16.tiktokcdn.com/a.jpg?x-expires=1')=='expired_url'


def test_expired_provider_thumbnail_is_visible_to_recovery_diagnostics():
    from app.campaigns import _existing_thumbnail
    from types import SimpleNamespace
    import json
    expired='https://p16.tiktokcdn.com/cover.jpg?x-expires=1'
    item=SimpleNamespace(raw_payload_json=json.dumps({'source_items':[{'media':{'thumbnail_url':expired}}]}))
    assert _existing_thumbnail(item)==''
    assert _existing_thumbnail(item,include_expired=True)==expired


def test_instagram_post_nested_image_versions_thumbnail():
    from types import SimpleNamespace
    from app.campaigns import _existing_thumbnail
    import json
    uri='https://instagram.fna.fbcdn.net/photo.jpg'
    record=SimpleNamespace(raw_payload_json=json.dumps({'post':{'image_versions2':{'candidates':[{'url':uri}]}}}))
    assert _existing_thumbnail(record)==uri
