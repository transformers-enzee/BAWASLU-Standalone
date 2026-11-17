"""Cross-module source IDs are not independent corroboration."""
import pytest
from app.assistant_cross_module_inventory import cross_module_inventory,cross_module_instruction
from app import intelligence_assistant as intel

def test_exact_selected_link_separate_counts():
    x=cross_module_inventory([
      {"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING"},
      {"record_id":"INT-1","record_type":"FORMAL_INTELLIGENCE",
       "origin_source_id":"social:7","review_status":"Validated as Relevant Intelligence",
       "verification_status":"UNVERIFIED"},
      {"record_id":"INT-2","record_type":"FORMAL_INTELLIGENCE","origin_source_id":"social:9"},
      {"record_id":"DOC-1-P3","record_type":"PDF_KNOWLEDGE"}])
    assert (x["selected_social_posts"],x["selected_inbox_records"],x["selected_pdf_pages"])==(1,2,1)
    assert x["explicit_source_link_count"]==1
    assert x["explicit_source_links"]==[{
      "inbox_record_id":"INT-1","social_record_id":"SOCIAL-7",
      "basis":"EXPLICIT_SAVED_SOCIAL_SOURCE_ID",
      "independent_corroboration":False,"source_truth_verified":False}]
    assert x["unlinked_inbox_records"]==1
    assert not x["formal_election_violation_determined"]

def test_weak_identity_and_missing_social_cannot_prove_overlap():
    rows=[{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING","title":"Same title"},
      {"record_id":"INT-1","record_type":"FORMAL_INTELLIGENCE","title":"Same title","origin_source_id":"7"},
      {"record_id":"INT-2","record_type":"FORMAL_INTELLIGENCE","origin_source_id":"social:9"}]
    x=cross_module_inventory(rows)
    assert x["explicit_source_link_count"]==0 and x["unlinked_inbox_records"]==2
    assert x["cross_module_absence_is_not_no_incident"]

def test_bounded_link_list_retains_total():
    rows=[{"record_id":"SOCIAL-7","record_type":"SOCIAL_LISTENING"}]+[
      {"record_id":f"INT-{i}","record_type":"FORMAL_INTELLIGENCE","origin_source_id":"social:7"} for i in range(5)]
    x=cross_module_inventory(rows,limit=2)
    assert x["explicit_source_link_count"]==5 and len(x["explicit_source_links"])==2
    assert x["links_truncated"]

def test_explicit_provenance_added_to_formal_evidence(monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(intel,"human_approved_triage",lambda _: {})
    monkeypatch.setattr(intel,"_validation_governance",lambda _: {"state":"","blockers":[],"note":""})
    monkeypatch.setattr(intel,"_jurisdiction",lambda _: "")
    monkeypatch.setattr(intel,"_canonical_utc",lambda _: "")
    monkeypatch.setattr(intel,"_utc_display",lambda _: "")
    row=SimpleNamespace(intelligence_id="INT-1",source_id="social:7",title="Claim",
      original_content="Claim",publication_date="",publication_datetime="",
      collection_datetime="",created_at=None,validated_at=None,
      jurisdiction_confirmed=False,priority="Medium",
      review_status="Validated as Relevant Intelligence",verification_status="UNVERIFIED",
      evidence_type="Social",observed_publisher_handle="",source_name="",author="")
    assert intel.assistant_evidence_record(row)["origin_source_id"]=="social:7"
    row.source_id="7"
    assert intel.assistant_evidence_record(row)["origin_source_id"]==""

def test_profile_gating():
    assert cross_module_instruction("SOCIAL_ANALYSIS")==""
    for p in ("CROSS_MODULE_REVIEW","CASE_REVIEW","EXECUTIVE_REPORT"):
      s=cross_module_instruction(p)
      assert "NOT two independent witnesses" in s
      assert "review_status" in s and "verification_status" in s
