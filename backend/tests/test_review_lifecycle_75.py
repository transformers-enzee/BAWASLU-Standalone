"""Build 75.0: Credit-free review persistence, audit and history lifecycle."""
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import EvidenceAssessment, EvidenceReview, AuditEvent
from app.access import audit

def test_human_review_lifecycle_preserves_evidence_and_audit():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            assessment=EvidenceAssessment(id=750001,campaign_id=751001,result_id=752001,
                assessment_version=1,relevance_label='RELEVANT',
                potential_issue_signals_json='[{"category_id":7,"evidence_quote":"quoted evidence"}]')
            db.add(assessment);db.flush()
            original=assessment.potential_issue_signals_json
            decision=EvidenceReview(assessment_id=assessment.id,reviewer_id='officer-one',
                decision='FURTHER_INVESTIGATION',rationale='Further evidence needs to be checked',
                created_at=datetime(2026,10,19,9,0))
            db.add(decision);db.flush()
            audit(db,{'id':'officer-one','name':'QA Officer'},'EvidenceReview',decision.id,
                'POTENTIAL_FLAG_REVIEW',{'campaign_id':assessment.campaign_id,
                 'result_id':assessment.result_id,'assessment_id':assessment.id,
                 'assessment_version':1,'decision':decision.decision,
                 'legacy_signal_present':True})
            history=(db.query(EvidenceReview,EvidenceAssessment.assessment_version)
                .join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
                .filter(EvidenceAssessment.campaign_id==751001,
                        EvidenceAssessment.result_id==752001,
                        EvidenceReview.decision.in_(['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']))
                .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).limit(10).all())
            assert len(history)==1
            assert history[0][0].decision=='FURTHER_INVESTIGATION'
            assert history[0][1]==1
            record=db.query(AuditEvent).filter_by(subject_type='EvidenceReview',subject_id=str(decision.id)).one()
            assert record.actor_id=='officer-one'
            assert json.loads(record.changes_json)['assessment_version']==1
            assert db.get(EvidenceAssessment,assessment.id).potential_issue_signals_json==original
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
