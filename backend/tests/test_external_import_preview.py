from app.external_import_preview import map_fields
def test_zocialeye_field_mapping():
    result=map_fields(['Account','Message','Direct URL','Post URL','Source','Post time','_id'])
    assert result['text_content']=='Message'
    assert result['canonical_url']=='Direct URL'
    assert result['provider_result_id']=='_id'
def test_youtube_url_mapping():
    assert map_fields(['Message','Video URL'])['canonical_url']=='Video URL'
