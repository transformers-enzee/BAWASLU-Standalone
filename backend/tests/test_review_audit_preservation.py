"""Build 73.3: Review decisions append independently of immutable assessments."""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import EvidenceAssessment, EvidenceReview

def test_multiple_officer_reviews_preserve_original_ai_evidence():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            source=[{'category_id':7,'evidence_quote':'pembagian uang kepada pemilih'}]
            evidence=EvidenceAssessment(id=920001,campaign_id=99001,result_id=99002,
                assessment_version=1,relevance_label='RELEVANT',
                model_version='historical-v1',potential_issue_signals_json=json.dumps(source),
                explanation='Original model output retained')
            db.add(evidence);db.commit()
            saved=evidence.potential_issue_signals_json
            for decision,reviewer in [('FURTHER_INVESTIGATION','officer-a'),('FLAG_DISMISSED','officer-b')]:
                db.add(EvidenceReview(assessment_id=evidence.id,reviewer_id=reviewer,
                    decision=decision,rationale='Review based on preserved source evidence'))
                db.commit()
            reviews=db.query(EvidenceReview).filter_by(assessment_id=evidence.id).order_by(EvidenceReview.id).all()
            assert [(x.reviewer_id,x.decision) for x in reviews]==[
                ('officer-a','FURTHER_INVESTIGATION'),('officer-b','FLAG_DISMISSED')]
            unchanged=db.get(EvidenceAssessment,evidence.id)
            assert unchanged.potential_issue_signals_json==saved
            assert unchanged.assessment_version==1
            assert unchanged.explanation=='Original model output retained'
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
