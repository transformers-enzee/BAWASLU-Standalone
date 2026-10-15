from app.thumbnail_cache import _allowed_image_host

def test_image_cache_rejects_untrusted_and_insecure_image_urls():
    assert _allowed_image_host('https://instagram.fkiv8-1.fna.fbcdn.net/photo.jpg')
    assert _allowed_image_host('https://p16-common-sign.tiktokcdn-us.com/cover.jpeg')
    assert not _allowed_image_host('http://instagram.fkiv8-1.fna.fbcdn.net/photo.jpg')
    assert not _allowed_image_host('https://fakefbcdn.net/photo.jpg')
    assert not _allowed_image_host('https://localhost/photo.jpg')
    assert not _allowed_image_host('https://fbcdn.net.evil.example/photo.jpg')
    assert not _allowed_image_host('https://user:password@fbcdn.net/photo.jpg')
