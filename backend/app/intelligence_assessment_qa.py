"""Read-only, synthetic AI assessment workbench for national staging QA.

No model, crawler, billing, incident tables, officer decisions or persistent writes.
Expected values are *illustrative fixtures*, not validated gold training labels.
"""
import os
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .access import has, profile
from .auth import current_user
from .db import get_db
from .models import User
from .intelligence_contract import (
    CONTRACT_VERSION, FIELD_GROUPS, INSIGHT_VARIABLES,
    FieldAssessment, FieldCorrection, CorrectionState, effective_value,
)

router = APIRouter(prefix="/api/intelligence-assessment-qa",
                   tags=["intelligence-assessment-qa"])

def _case(case_id, title, focus, source, expected, sample_predictions, note):
    return {
        "id":case_id, "title":title, "focus":focus,
        "source_id":"SYNTH-"+case_id.upper(), "source_text":source,
        "expected":expected, "sample_predictions":sample_predictions,
        "review_note":note, "reference_status":"ILLUSTRATIVE_NOT_OFFICER_GOLD",
    }

CASES = (
    _case(
        "money-politics", "Money-politics allegation", "Violation screening",
        "Postingan simulasi menyatakan uang dibagikan saat kampanye. Tidak ada saksi independen atau dokumen pendukung.",
        {"primary_issue":"alleged_money_politics","violation_type":"money_politics",
         "allegation_status":"allegation","verification_status":"unverified",
         "evidence_strength":"uncorroborated","review_priority":"needs_verification"},
        {"primary_issue":"alleged_money_politics","violation_type":"money_politics",
         "allegation_status":"substantiated_by_authority","verification_status":"unverified",
         "evidence_strength":"uncorroborated","review_priority":"needs_verification"},
        "An unsupported claim must not be represented as a substantiated violation."
    ),
    _case(
        "actor-role", "Candidate mentioned, not accused", "Actor attribution",
        "Seorang pengguna membahas pernyataan seorang calon yang membantah dugaan, tanpa menuduh calon tersebut sebagai pelaku.",
        {"candidate_role":"quoted_denial","allegation_status":"inconclusive",
         "verification_status":"unverified","primary_issue":"public_discussion"},
        {"candidate_role":"accused","allegation_status":"inconclusive",
         "verification_status":"unverified","primary_issue":"public_discussion"},
        "Mentioned persons, accused parties and quoted denials are different roles."
    ),
    _case(
        "unknown-location", "Event location is ambiguous", "Geography",
        "Akun berprofil Bandung menulis bahwa peristiwa diduga terjadi di suatu desa, tanpa menyebut lokasi kejadian.",
        {"event_location":"unknown","location_basis":"unknown",
         "jurisdiction_status":"uncertain","location_confidence":0},
        {"event_location":"Bandung","location_basis":"account_profile",
         "jurisdiction_status":"in_scope","location_confidence":0.9},
        "An account profile is not proof of incident location or jurisdiction."
    ),
    _case(
        "pilkades", "Village-head election allegation", "Election jurisdiction",
        "Dalam contoh rekaan ini, sebuah unggahan membahas dugaan pembagian uang pada pemilihan kepala desa.",
        {"election_type":"PILKADES","jurisdiction_status":"uncertain",
         "competent_authority":"requires_review","allegation_status":"allegation"},
        {"election_type":"PILKADES","jurisdiction_status":"in_scope",
         "competent_authority":"BAWASLU","allegation_status":"allegation"},
        "Pilkades must not automatically be assigned to BAWASLU jurisdiction."
    ),
    _case(
        "duplicate-posts", "Repeated viral allegation", "Duplicate and incident grouping",
        "Tiga unggahan simulasi mengulang laporan yang sama mengenai satu insiden, tanpa bukti adanya tiga peristiwa terpisah.",
        {"duplicate_cluster_id":"SYNTH-DUP-1","incident_cluster_id":"SYNTH-INCIDENT-1",
         "corroborating_sources":0,"verification_status":"unverified"},
        {"duplicate_cluster_id":"SYNTH-DUP-1","incident_cluster_id":"SYNTH-INCIDENT-3",
         "corroborating_sources":3,"verification_status":"unverified"},
        "Multiple reposts are not three independent incidents or corroborating sources."
    ),
    _case(
        "public-criticism", "Political criticism only", "Sentiment vs violation",
        "Komentar bernada negatif mengkritik BAWASLU dan meminta transparansi tanpa menyampaikan dugaan pelanggaran tertentu.",
        {"sentiment":"NEGATIVE","sentiment_target":"BAWASLU",
         "primary_issue":"public_criticism","violation_type":"none",
         "allegation_status":"inconclusive"},
        {"sentiment":"NEGATIVE","sentiment_target":"BAWASLU",
         "primary_issue":"public_criticism","violation_type":"money_politics",
         "allegation_status":"inconclusive"},
        "Negative sentiment is not by itself an election-law violation."
    ),
    _case(
        "conflicting-sources", "Contradictory source accounts", "Evidence",
        "Unggahan A menyebut insiden terjadi pada Senin; unggahan B membantah dan menyatakan tidak ada kejadian terkonfirmasi.",
        {"verification_status":"inconclusive","contradicting_sources":1,
         "evidence_strength":"unverified","source_authenticity":"unknown"},
        {"verification_status":"verified","contradicting_sources":1,
         "evidence_strength":"verified","source_authenticity":"unknown"},
        "Contradictions require independent verification, not confident certainty."
    ),
    _case(
        "approved-override", "Approved officer correction", "Human precedence",
        "Pada data simulasi, AI menandai jenis isu sebagai money politics; peninjau memberi koreksi yang telah disetujui.",
        {"violation_type":"money_politics","human_review_status":"approved"},
        {"violation_type":"money_politics","human_review_status":"approved"},
        "The preview below must preserve the AI suggestion and use an approved officer value downstream."
    ),
)

LOOKUP = {item["id"]:item for item in CASES}
KNOWN_FIELDS = frozenset(field for values in FIELD_GROUPS.values() for field in values)


def require_national_admin(db, user):
    grant = profile(db, user)
    if (grant.get("role") != "National Administrator"
            or grant.get("geographic_scope") != "Nationwide"
            or not has(grant, "administration")):
        raise HTTPException(status_code=403, detail="National Administrator access required")
    if os.getenv("BAWASLU_ASSESSMENT_QA_ENABLED", "").lower() not in ("1","true","yes"):
        raise HTTPException(status_code=404, detail="Assessment QA is disabled for this environment")
    return grant


def catalog_payload():
    return {
        "version":"183.6", "contract_version":CONTRACT_VERSION,
        "synthetic_only":True, "paid_model_called":False, "persistent_writes":False,
        "real_ai_connected":False, "human_gold_labels":False,
        "field_groups":{k:list(fields) for k,fields in FIELD_GROUPS.items()},
        "insight_variables":list(INSIGHT_VARIABLES), "cases":list(CASES),
    }


def override_preview():
    assessment = FieldAssessment(
        field="violation_type", ai_value="money_politics", ai_confidence=0.74,
        evidence_refs=("SYNTH-APPROVED-OVERRIDE",),
        assessment_version=CONTRACT_VERSION)
    approved = FieldCorrection(
        field="violation_type", human_value="other_regulatory_issue",
        reason="Synthetic officer review demonstration",
        evidence_refs=("SYNTH-APPROVED-OVERRIDE",),
        reviewer_id="synthetic-reviewer", state=CorrectionState.APPROVED, revision=1)
    proposed = FieldCorrection(
        field="violation_type", human_value="other_regulatory_issue",
        reason="Synthetic pending review demonstration",
        evidence_refs=("SYNTH-APPROVED-OVERRIDE",),
        reviewer_id="synthetic-reviewer", state=CorrectionState.PROPOSED, revision=1)
    return {
        "ai_value":assessment.ai_value,
        "approved_effective_value":effective_value(assessment, approved),
        "unapproved_effective_value":effective_value(assessment, proposed),
        "persisted":False, "officer_record_modified":False,
    }


def evaluate(case_id: str, predictions: dict[str, Any]):
    case = LOOKUP.get(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Unknown synthetic test case")
    if len(predictions) > len(KNOWN_FIELDS):
        raise HTTPException(status_code=422, detail="Too many prediction fields")
    bad_fields = sorted(set(predictions) - KNOWN_FIELDS)
    if bad_fields:
        raise HTTPException(status_code=422, detail="Unknown contract field(s): "+", ".join(bad_fields[:5]))
    for value in predictions.values():
        if isinstance(value, (dict,list,tuple,set)) or (
            value is not None and (not isinstance(value,(str,int,float,bool))
                                    or isinstance(value,str) and len(value)>300)
        ):
            raise HTTPException(status_code=422, detail="Prediction values must be short scalar values")
    details = []
    for field, expected in case["expected"].items():
        supplied = field in predictions and predictions[field] is not None
        actual = predictions.get(field)
        status = "MISSING" if not supplied else "MATCH" if actual == expected and type(actual) == type(expected) else "MISMATCH"
        details.append({"field":field, "expected":expected, "actual":actual,
                        "status":status, "group":next(k for k,v in FIELD_GROUPS.items() if field in v)})
    matched = sum(d["status"] == "MATCH" for d in details)
    supplied = sum(d["status"] != "MISSING" for d in details)
    result = {
        "case_id":case_id, "reference_status":case["reference_status"],
        "synthetic_only":True, "paid_model_called":False, "persistent_writes":False,
        "compared_fields":len(details), "provided_fields":supplied,
        "matched_fields":matched, "mismatched_fields":sum(d["status"]=="MISMATCH" for d in details),
        "missing_fields":len(details)-supplied,
        "coverage":round(supplied / len(details),4),
        "agreement":round(matched / len(details),4),
        "extra_fields_not_scored":sorted(set(predictions)-set(case["expected"])),
        "details":details, "override_preview":override_preview() if case_id=="approved-override" else None,
    }
    return result


class EvaluationRequest(BaseModel):
    case_id: str = Field(min_length=1, max_length=80)
    predictions: dict[str, Any] = Field(default_factory=dict)


@router.get("/catalog")
def catalog(user:User=Depends(current_user), db:Session=Depends(get_db)):
    require_national_admin(db, user)
    return catalog_payload()


@router.post("/evaluate")
def evaluate_submission(body:EvaluationRequest, user:User=Depends(current_user),
                        db:Session=Depends(get_db)):
    require_national_admin(db, user)
    return evaluate(body.case_id, body.predictions)
