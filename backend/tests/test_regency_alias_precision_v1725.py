"""v172.5: abbreviation and multi-Kabupaten precision safety benchmark."""
import pytest
from app.incident_regency_candidates import incident_regency_preview
from app.processing_hints import incident_location_cues

@pytest.mark.parametrize('text,expected',[
 ('Dugaan pelanggaran terjadi di Kabupaten Musi Banyuasin dan Musi Rawas Utara.',
  {'Kabupaten Musi Banyuasin','Kabupaten Musi Rawas Utara'}),
 ('Kasus pemilu terjadi di Kab. Musi Banyuasin.',
  {'Kabupaten Musi Banyuasin'}),
 ('Dugaan pelanggaran terjadi di Kab Musi Rawas Utara.',
  {'Kabupaten Musi Rawas Utara'}),
 ('Kecurangan pemilu dilaporkan di Kota Bandung dan Kota Cimahi.',
  {'Kota Bandung','Kota Cimahi'}),
 ('Dugaan pelanggaran terjadi di Kabupaten Bandung dan Kota Bandung.',
  {'Kabupaten Bandung','Kota Bandung'}),
 ('Laporan pemilu terjadi di Kota Surabaya.',
  {'Kota Surabaya'}),
 ('Dugaan pelanggaran terjadi di Kabupaten Aceh Selatan.',
  {'Kabupaten Aceh Selatan'}),
 ('Pemilu berjalan lancar di Kota Bandung.',
  {'Kota Bandung'}),
 ('Dugaan kasus pemilu terjadi di Kota Bandung; kantor pusat di Kota Surabaya.',
  {'Kota Bandung'}),
 ('Kantor Bawaslu di Kota Bandung membahas dugaan pelanggaran.',set()),
 ('Akun dari Kota Bandung membahas isu pemilu.',set()),
 ('Berita dari Kota Surabaya membahas pemungutan suara.',set()),
 ('Kabupaten Bandung mengeluarkan pemberitahuan soal pemilu.',set()),
 ('Dugaan pelanggaran di Bandung.',set()),
 ('Laporan kasus dari Kabupaten Bandung.',set()),
 ('Dugaan pelanggaran terjadi di Kabupaten Bogor dan Bandung.',
  {'Kabupaten Bogor'}),
 ('Dugaan pelanggaran terjadi di Kota Bandung dan Bandung.',
  {'Kota Bandung'}),
])
def test_source_location_precision_fixture(text,expected):
    preview=incident_regency_preview(text)
    detected={x['regency_city'] for x in preview['candidates']}
    assert detected==expected
    assert preview['kabupaten_kota_verified'] is False
    assert preview['provider_calls']==0

def test_ambiguous_two_regencies_from_abbreviated_report_block_auto_confirmation():
    text='Dugaan pencoblosan ganda di Kab. Musi Banyuasin dan Musi Rawas Utara.'
    report=incident_regency_preview(text)
    assert report['candidate_count']==2
    assert report['multiple_regency_candidates']
    assert not report['multiple_provinces']
    assert incident_location_cues(text)==['Sumatera Selatan']

def test_cross_province_followup_never_silently_reduces_to_one_city():
    text='Dugaan pelanggaran terjadi di Kota Bandung dan Kota Surabaya.'
    report=incident_regency_preview(text)
    assert report['candidate_count']==2
    assert report['multiple_provinces']
    assert set(incident_location_cues(text))=={'Jawa Barat','Jawa Timur'}

def test_unqualified_ambiguous_bandung_does_not_infer_regency():
    report=incident_regency_preview(
        'Dugaan pelanggaran terjadi di Kabupaten Bogor dan Bandung.')
    assert report['candidate_count']==1

def test_fixture_exact_set_scoring_is_measurable():
    cases=[
      ('Dugaan pelanggaran terjadi di Kab. Musi Banyuasin dan Musi Rawas Utara.',
        {'Kabupaten Musi Banyuasin','Kabupaten Musi Rawas Utara'}),
      ('Akun dari Kota Bandung membahas pemilu.',set()),
      ('Dugaan pelanggaran terjadi di Kabupaten Bandung dan Kota Bandung.',
        {'Kabupaten Bandung','Kota Bandung'}),
      ('Bawaslu Sumatera Selatan berbicara soal pemilu.',set())]
    exact=sum({x['regency_city'] for x in incident_regency_preview(body)['candidates']}==expected
              for body,expected in cases)
    assert exact==len(cases)
