"""v172.0: province-to-Kabupaten/Kota source-grounded preview and guardrails."""
from app.incident_regency_candidates import incident_regency_preview, incident_regency_candidates
from app.processing_hints import incident_location_cues

def test_explicit_kabupaten_names_from_saved_electoral_incident():
    text=('Dugaan pencoblosan lebih dari sekali terjadi di Kabupaten Musi Banyuasin '
          'dan Kabupaten Musi Rawas Utara.')
    result=incident_regency_preview(text)
    assert [x['regency_city'] for x in result['candidates']]==[
        'Kabupaten Musi Banyuasin','Kabupaten Musi Rawas Utara']
    assert not result['multiple_provinces']
    assert result['multiple_regency_candidates']
    assert result['kabupaten_kota_verified'] is False
    assert all(x['province_code']=='16' for x in result['candidates'])
    assert incident_location_cues(text)==['Sumatera Selatan']

def test_explicit_kota_is_identified_without_publisher_location_guessing():
    result=incident_regency_preview('Dugaan pelanggaran pemilu terjadi di Kota Bandung.')
    assert len(result['candidates'])==1
    assert result['candidates'][0]['province_code']=='32'
    assert incident_location_cues('Dugaan pelanggaran pemilu terjadi di Kota Bandung.')==['Jawa Barat']
    assert not incident_regency_candidates('Akun dari Kota Bandung membahas pemilu.')
    assert not incident_regency_candidates('Kantor Bawaslu di Kota Bandung membahas dugaan kasus.')

def test_single_province_with_two_cities_is_still_ambiguous():
    report=incident_regency_preview(
        'Dugaan pelanggaran terjadi di Kota Bandung dan Kota Cimahi.')
    assert report['candidate_count']==2
    assert report['multiple_regency_candidates']
    assert not report['multiple_provinces']

def test_conflicting_provinces_are_explicitly_visible():
    report=incident_regency_preview(
        'Dugaan pelanggaran terjadi di Kota Bandung dan Kota Surabaya.')
    assert report['candidate_count']==2
    assert report['multiple_provinces']
    assert set(incident_location_cues(
        'Dugaan pelanggaran terjadi di Kota Bandung dan Kota Surabaya.'))=={'Jawa Barat','Jawa Timur'}

def test_no_explicit_incident_context_no_region():
    assert incident_regency_preview('Bawaslu Kabupaten Bogor memberikan sambutan.')['candidate_count']==0
    assert incident_regency_preview('Berita dari Kota Bandung tentang pemilu.')['candidate_count']==0
    assert incident_regency_preview('Insiden terjadi di wilayah tak bernama.')['candidate_count']==0

def test_preview_purely_readonly_and_no_provider():
    report=incident_regency_preview('Kasus pemilu di Kabupaten Aceh Selatan.')
    assert report['candidate_count']==1
    assert report['provider_calls']==0
    assert report['requires_human_incident_review']
    assert report['method']=='EXPLICIT_INCIDENT_LOCATION_TEXT_AND_LOCAL_REGION_REGISTRY'
