"""Calibration must never give a held-out source its human label as a prompt example."""
from app.smart_radar_calibration import split_examples,canonical_key
CATS=["Disputes / Legal","Election Operations","Allegations / Violations"]
def row(i,c,text=None):
    return {"qa_id":f"QA-{i}","category":c,"source_url":f"https://example.org/{i}",
            "message_original":text or f"Berita tentang kegiatan dan pelanggaran proses demokrasi dalam catatan {i}."}
def test_holdout_does_not_leak_to_training():
    rows=[row(i,c) for i,c in enumerate(CATS) for _ in []]
    rows=[row(i*100+j,category) for i,category in enumerate(CATS) for j in range(9)]
    train,holdout,excluded=split_examples(rows)
    assert len(train)>0 and len(holdout)>0
    assert not {r["qa_id"] for r in train}&{r["qa_id"] for r in holdout}
    assert not {canonical_key(r) for r in train}&{canonical_key(r) for r in holdout}
    assert excluded==0
def test_duplicate_source_text_same_split():
    rows=[row(i,"Election Operations") for i in range(10)]
    duplicate=row(100,"Election Operations",rows[0]["message_original"])
    rows.append(duplicate)
    train,holdout,excluded=split_examples(rows)
    assert len(train)+len(holdout)==10
    assert excluded==0
def test_conflicting_labels_excluded():
    a=row(1,"Election Operations")
    b=row(2,"Disputes / Legal",a["message_original"])
    train,holdout,excluded=split_examples([a,b])
    assert not train and not holdout and excluded==2
