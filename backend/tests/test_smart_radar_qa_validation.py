"""No model call needed: verify output validation remains evidence-safe."""
import json
import pytest
from app.smart_radar_qa_validation import (
    QAOutputError,validate_qa_v2_output,verbatim_source_span)
CATS={"Allegations / Violations","Disputes / Legal","Election Operations"}
SOURCE="Sidang perkara sengketa hasil Pilpres berlangsung di Mahkamah Konstitusi."

def payload(primary="Disputes / Legal",quote="Sidang perkara sengketa",
            secondary=None,finish_reason="stop"):
    d={"primary_category":primary,"evidence_quote":quote,"rationale":"Perkara hukum"}
    if secondary is not None:d["secondary_categories"]=secondary
    return {"choices":[{"finish_reason":finish_reason,
         "message":{"content":json.dumps(d)}}]}

def test_exact_quote_and_category_stay_valid():
    result=validate_qa_v2_output(payload(),"Sidang perkara sengketa hasil",CATS,"baseline")
    assert result["primary_category"]=="Disputes / Legal"
    assert result["evidence_validation"]=="verified_verbatim"
    assert result["evidence_quote"]=="Sidang perkara sengketa"

def test_whitespace_quoted_source_keeps_real_span_only():
    source="Sidang  perkara\nsengketa hasil"
    result=validate_qa_v2_output(payload(),source,CATS,"baseline")
    assert result["evidence_quote"]=="Sidang  perkara\nsengketa"
    assert result["evidence_validation"]=="verified_verbatim"

def test_nonverbatim_quote_does_not_drop_classification_or_claim_evidence():
    result=validate_qa_v2_output(payload(quote="Sidang perkara sengketa palsu"),
                                 SOURCE,CATS,"baseline")
    assert result["primary_category"]=="Disputes / Legal"
    assert result["evidence_quote"]==""
    assert result["evidence_quote_proposed"]=="Sidang perkara sengketa palsu"
    assert result["evidence_validation"]=="needs_source_review"
    assert "evidence_quote_not_verified" in result["qa_validation_warnings"]

def test_secondary_bad_values_filtered_without_fabricating_categories():
    result=validate_qa_v2_output(payload(secondary=[
        "Election Operations","not a real category","Disputes / Legal"]),SOURCE,CATS,"guided")
    assert result["secondary_categories"]==["Election Operations"]
    assert "invalid_secondary_category_dropped" in result["qa_validation_warnings"]

def test_truncation_produces_explicit_diagnostic():
    with pytest.raises(QAOutputError) as err:
        validate_qa_v2_output(payload(finish_reason="length"),SOURCE,CATS,"guided")
    assert err.value.code=="output_truncated"

def test_invalid_primary_never_saved_as_category():
    with pytest.raises(QAOutputError) as err:
        validate_qa_v2_output(payload(primary="Legalish"),SOURCE,CATS,"guided")
    assert err.value.code=="invalid_category"

def test_missing_content_explained():
    with pytest.raises(QAOutputError) as err:
        validate_qa_v2_output({"choices":[{"message":{"content":None},"finish_reason":"stop"}]},SOURCE,CATS,"baseline")
    assert err.value.code=="empty_content"
