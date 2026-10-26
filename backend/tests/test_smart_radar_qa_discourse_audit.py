from app.smart_radar_qa_discourse_audit import (
    discourse_features, feature_overlap, lexical_vs_discourse_audit
)
def test_features_are_interpretable_and_normalize_entities():
    x=discourse_features("Pengawasan partisipatif untuk &amp; pemilih lansia; hoaks di ruang digital")
    assert "oversight_action" in x
    assert "inclusive_access" in x
    assert "information_environment" in x
def test_empty_overlap():
    assert feature_overlap("tanpa kategori", "tanpa kata relevan") == 0
def test_discourse_ranking_does_not_peek_at_gold():
    targets=[{"qa_id":"t","message_original":"pengawasan partisipatif lansia",
              "shahrin_category":"Citizen Reports / Public Concerns",
              "source_hash":"t","source_url":"t"}]
    exemplars=[{"qa_id":"a","message_original":"sidang MK perkara PHPU",
                "shahrin_category":"Disputes / Legal","source_hash":"a","source_url":"a"},
               {"qa_id":"b","message_original":"inklusif bagi lansia dan disabilitas",
                "shahrin_category":"Citizen Reports / Public Concerns","source_hash":"b","source_url":"b"}]
    scores={("t","a"):0.9,("t","b"):0.1}
    result=lexical_vs_discourse_audit(targets,exemplars,scores)
    assert result["lexical_hits"]==0
    assert result["discourse_hits"]==1
    assert result["n"]==1
    targets[0]["shahrin_category"]="Disputes / Legal"
    changed=lexical_vs_discourse_audit(targets,exemplars,scores)
    assert changed["rows"][0]["discourse_category"]==result["rows"][0]["discourse_category"]
