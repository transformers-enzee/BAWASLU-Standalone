"""Guard against QA benchmark leakage and noisy human-label exemplars."""
from app.smart_radar_qa_v2 import (
    EXPOSED_DIAGNOSTIC_IDS, label_review_flags, _accuracy,
    _exemplars, RULES_V2,
)

def sample(qid,category,message):
    return {"qa_id":qid,"category":category,"message_original":message,
            "source_url":"https://example.org/"+qid}

def test_previously_disclosed_cases_are_excluded_from_v2():
    assert EXPOSED_DIAGNOSTIC_IDS=={
        "QA-14141","QA-14352","QA-14806","QA-14835"
    }

def test_category_boundaries_include_both_sides():
    assert "Disputes / Legal" in RULES_V2
    assert "Allegations / Violations" in RULES_V2
    assert "SECONDARY tags" in RULES_V2
    assert "court hearing" in RULES_V2

def test_suspect_labels_flagged_not_overwritten():
    suspect=sample("QA-1","Voter Register / PDPB",
                   "Bawaslu dan Diskominfo berdialog tentang hoaks di ruang digital.")
    assert label_review_flags(suspect)
    assert suspect["category"]=="Voter Register / PDPB"
    other=sample("QA-2","Digital Risks / Information",
                 "Saya dulu pengawas TPS, banyak kenangan yang indah.")
    assert label_review_flags(other)
    assert other["category"]=="Digital Risks / Information"

def test_exemplar_selection_avoids_flagged_mismatches():
    train=[
        sample("QA-1","Voter Register / PDPB","Kegiatan ruang digital dan hoaks saja."),
        sample("QA-2","Voter Register / PDPB","Proses pemutakhiran daftar pemilih DPT di Bawaslu."),
        sample("QA-3","Disputes / Legal","Sidang perkara di MK mengenai sengketa hasil pemilu.")
    ]
    xs=_exemplars(train)
    assert len(xs)==2
    assert all("ruang digital" not in x["text"] for x in xs)

def test_accuracy_denominator_counts_only_saved_predictions():
    holdout=[sample("QA-1","Disputes / Legal","Sidang sengketa."),
             sample("QA-2","Allegations / Violations","Dugaan pelanggaran.")]
    results={"QA-1":{"primary_category":"Disputes / Legal"},
             "QA-2":{"primary_category":"Disputes / Legal"}}
    x=_accuracy(holdout,results)
    assert x["tested"]==2
    assert x["correct"]==1
    assert x["accuracy"]==0.5


def test_v2_is_paused_until_human_references_reviewed():
    from app.smart_radar_qa_v2 import V2_TESTING_PAUSED
    assert V2_TESTING_PAUSED is True

def test_disagreements_expose_only_reviewed_records(monkeypatch):
    import app.smart_radar_qa_v2 as mod
    monkeypatch.setattr(mod,"reviewer",lambda db,user: {"role":"National Administrator"})
    monkeypatch.setattr(mod,"qa_config",lambda: {"model":"unit-test"})
    class FakeRows:
        def mappings(self):return self
        def __iter__(self):
            yield {"qa_id":"QA-1","source_url":"https://example.org/1",
                   "platform":"x","message_original":"Teks asli",
                   "original_category":"Election Operations",
                   "human_category":"Election Operations",
                   "review_status":"awaiting_analyst_signoff",
                   "prompt_version":"qa-clean-human-guided-v2",
                   "processed_at":None,
                   "result_json":{"primary_category":"Allegations / Violations",
                                  "rationale":"Alasan AI","decision_boundary":"Alasan batas",
                                  "evidence_validation":"verified_verbatim"}}
            yield {"qa_id":"QA-2","source_url":"https://example.org/2",
                   "platform":"x","message_original":"Teks lainnya",
                   "original_category":"Election Operations",
                   "human_category":"Election Operations",
                   "review_status":"confirmed",
                   "prompt_version":"qa-clean-human-guided-v2",
                   "processed_at":None,
                   "result_json":{"primary_category":"Election Operations"}}
    class FakeDB:
        def execute(self,*args,**kwargs):return FakeRows()
    out=mod.calibration_v2_disagreements(user=object(),db=FakeDB())
    assert out["tested"]==2
    assert out["mismatches"]==1
    assert out["entries"][0]["qa_id"]=="QA-1"
    assert out["entries"][0]["human_category"]=="Election Operations"
    assert out["entries"][0]["review_status"]=="awaiting_analyst_signoff"
    assert out["human_labels_provisional"] is True
