"""v172.6 reproducible locality source-phrase evaluation and negatives."""
import pytest
from app.incident_regency_eval import evaluate_labeled_incident_regencies
from app.incident_regency_candidates import incident_regency_preview
from app.geography import regency_code_for

def code(name,province):
    result=regency_code_for(name,province)
    assert result
    return result

def labeled_cases():
    return [
      {'text':'Dugaan pelanggaran terjadi di Kab. Musi Banyuasin dan Musi Rawas Utara.',
       'expected_regency_codes':[code('Kabupaten Musi Banyuasin','16'),
                                 code('Kabupaten Musi Rawas Utara','16')]},
      {'text':'Insiden pemilu terjadi di Kota Bandung.',
       'expected_regency_codes':[code('Kota Bandung','32')]},
      {'text':'Kasus pelanggaran terjadi di Kota Bandung dan Kota Surabaya.',
       'expected_regency_codes':[code('Kota Bandung','32'),code('Kota Surabaya','35')]},
      {'text':'Pemilu berjalan lancar di Kota Bandung.',
       'expected_regency_codes':[]},
      {'text':'Tidak ada dugaan pelanggaran terjadi di Kota Bandung.',
       'expected_regency_codes':[]},
      {'text':'Akun dari Kota Bandung membahas dugaan pelanggaran.',
       'expected_regency_codes':[]},
      {'text':'Berita dari Kota Surabaya membahas kasus.',
       'expected_regency_codes':[]},
      {'text':'Dugaan kasus terjadi di Kabupaten Bandung dan Kota Bandung.',
       'expected_regency_codes':[code('Kabupaten Bandung','32'),code('Kota Bandung','32')]},
      {'text':'Bawaslu Kabupaten Bogor menyampaikan informasi.',
       'expected_regency_codes':[]},
      {'text':'Dugaan kasus terjadi di Kabupaten Bogor dan Bandung.',
       'expected_regency_codes':[code('Kabupaten Bogor','32')]},
    ]

def test_curated_location_benchmark_has_no_false_positive_or_false_negative():
    result=evaluate_labeled_incident_regencies(labeled_cases())
    assert result['labeled_cases']==10
    assert result['exact_match_cases']==10
    assert result['false_positives']==0
    assert result['false_negatives']==0
    assert result['micro_precision']==1
    assert result['micro_recall']==1
    assert result['paid_provider_called'] is False
    assert result['not_real_world_accuracy_without_representative_labels']

def test_evaluator_reports_misses_and_unknown_rates_without_faking_accuracy():
    cases=[{'text':'Kasus di Kota Bandung.','expected_regency_codes':[]},
           {'text':'Dugaan terjadi di wilayah tak diketahui.',
            'expected_regency_codes':['invented-code']}]
    report=evaluate_labeled_incident_regencies(cases)
    assert report['labeled_cases']==2
    assert report['exact_match_cases']==0
    assert report['false_positives']==1
    assert report['false_negatives']==1
    assert report['micro_f1']==0
    assert evaluate_labeled_incident_regencies([])['exact_match_rate'] is None

@pytest.mark.parametrize('text',[
  'Tidak ada dugaan pelanggaran terjadi di Kota Bandung.',
  'Tidak ditemukan insiden di Kota Surabaya.',
  'Pemilu berjalan lancar di Kota Bandung.',
  'Pilkada berjalan tertib di Kabupaten Bogor.',
  'Akun dari Kabupaten Bogor membahas laporan.',
])
def test_negated_or_routine_mentions_do_not_create_verified_place(text):
    report=incident_regency_preview(text)
    assert report['candidate_count']==0
    assert not report['kabupaten_kota_verified']

def test_multiple_regencies_remain_ambiguous_for_human_review():
    result=incident_regency_preview(
        'Kasus terjadi di Kab. Musi Banyuasin dan Musi Rawas Utara.')
    assert result['candidate_count']==2
    assert result['multiple_regency_candidates']
