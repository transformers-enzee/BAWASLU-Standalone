from app.external_import_preview import map_fields
def test_zocialeye_field_mapping():
    result=map_fields(['Account','Message','Direct URL','Post URL','Source','Post time','_id'])
    assert result['text_content']=='Message'
    assert result['canonical_url']=='Direct URL'
    assert result['provider_result_id']=='_id'
def test_youtube_url_mapping():
    assert map_fields(['Message','Video URL'])['canonical_url']=='Video URL'

def test_full_validation_csv(tmp_path):
    from app.external_import_preview import validate_all_rows
    file=tmp_path/'sample.csv'
    file.write_text('Message,Direct URL,Post URL,Comment URL,Source,Post time,_id\\n'
        'Report,https://example.org/a,,,facebook,2026-10-01,1\\n'
        'Reply,https://example.org/b,https://example.org/a,https://example.org/b,facebook,2026-10-02,2\\n'
        'Report,https://example.org/a,,,facebook,2026-10-01,1\\n',encoding='utf-8')
    result=validate_all_rows(file,{'https://example.org/a'})
    assert result['validation']['total_rows']==3
    assert result['validation']['duplicate_provider_ids']==1
    assert result['validation']['repeated_urls']==1
    assert result['validation']['comment']==1
    assert result['validation']['url_matches_existing_database']==2
    assert result['import_enabled'] is False
