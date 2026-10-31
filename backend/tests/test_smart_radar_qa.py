"""QA Stage-1 schema and model workflow checks; never mutate live officer findings."""
import pytest
from fastapi import HTTPException
from app.smart_radar_qa import balanced_sample,CATS,TARGET,source_hash

def fake_records():
    return [{"qa_id":"QA-"+cat.replace(" ","_")+"-"+str(i),"curated_category":cat,
            "source_url":f"https://example.org/{cat.replace(' ','_')}/{i}"}
            for cat in CATS for i in range(20)]

def test_stratified_cohort_covers_all_categories():
    posts=fake_records()
    selected=balanced_sample(posts,set())
    assert len(selected)==100
    picked=[r for r in posts if r["qa_id"] in selected]
    assert all(sum(x["curated_category"]==cat for x in picked)==TARGET[cat] for cat in CATS)

def test_existing_pilot_urls_excluded_and_repeatable():
    posts=fake_records()
    overlap={r["source_url"] for r in posts[:3]}
    a=balanced_sample(posts,overlap)
    assert a==balanced_sample(posts,overlap)
    assert all(p["source_url"] not in overlap for p in posts if p["qa_id"] in a)

def test_missing_category_raises():
    records=[r for r in fake_records() if r["curated_category"]!="Digital Risks / Information"]
    with pytest.raises(HTTPException):
        balanced_sample(records,set())

def test_source_hash_changes_when_message_changes():
    assert source_hash("https://a","Text A")!=source_hash("https://a","Text B")
