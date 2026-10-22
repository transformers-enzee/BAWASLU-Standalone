"""Build 73.9: Audit event identity and tamper-resistant review association tests."""
import json
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import AuditEvent, EvidenceAssessment, EvidenceReview
from app.access import audit

def test_human_review_audit_preserves_identity_provenance_and_assessment_snapshot():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            assessment=EvidenceAssessment(id=950001,campaign_id=951001,result_id=952001,
                assessment_version=2,relevance_label='RELEVANT',
                potential_issue_signals_json='[{"category_id":7,"evidence_quote":"test source quotation"}]')
            db.add(assessment);db.flush()
            evidence_snapshot=assessment.potential_issue_signals_json
            review=EvidenceReview(assessment_id=assessment.id,reviewer_id='officer-11',
                decision='FURTHER_INVESTIGATION',rationale='Further evidence is necessary')
            db.add(review);db.flush()
            audit(db,{'id':'officer-11','name':'Review Officer'},'EvidenceReview',review.id,
                'POTENTIAL_FLAG_REVIEW',{'campaign_id':951001,'result_id':952001,
                'assessment_id':assessment.id,'assessment_version':2,
                'decision':review.decision,'legacy_signal_present':True})
            events=db.query(AuditEvent).filter_by(subject_type='EvidenceReview',subject_id=str(review.id)).all()
            assert len(events)==1
            event=events[0]
            assert event.actor_id=='officer-11'
            assert event.actor_name=='Review Officer'
            assert event.action=='POTENTIAL_FLAG_REVIEW'
            payload=json.loads(event.changes_json)
            assert payload['assessment_id']==assessment.id
            assert payload['assessment_version']==2
            assert payload['decision']=='FURTHER_INVESTIGATION'
            assert payload['legacy_signal_present'] is True
            assert db.get(EvidenceReview,review.id).assessment_id==assessment.id
            assert db.get(EvidenceAssessment,assessment.id).potential_issue_signals_json==evidence_snapshot
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
