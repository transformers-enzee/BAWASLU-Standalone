from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from app.db import Base
from app.models import EvidenceAssessment, EvidenceReview

def test_latest_review_is_current_while_prior_decisions_remain_auditable():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            assessment=EvidenceAssessment(id=930001,campaign_id=931001,result_id=932001,
               assessment_version=1,relevance_label='RELEVANT',
               model_version='test-engine',potential_issue_signals_json='[]')
            db.add(assessment);db.flush()
            before=assessment.potential_issue_signals_json
            first=EvidenceReview(assessment_id=assessment.id,reviewer_id='officer-a',
               decision='FURTHER_INVESTIGATION',rationale='Evidence requires verification',
               created_at=datetime(2026,10,1,10,0))
            second=EvidenceReview(assessment_id=assessment.id,reviewer_id='officer-b',
               decision='FLAG_DISMISSED',rationale='No supporting evidence available',
               created_at=datetime(2026,10,2,10,0))
            db.add_all([first,second]);db.commit()
            latest=(db.query(EvidenceReview).filter_by(assessment_id=assessment.id)
                    .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).first())
            assert latest.decision=='FLAG_DISMISSED'
            assert db.query(EvidenceReview).filter_by(assessment_id=assessment.id).count()==2
            assert db.get(EvidenceAssessment,assessment.id).potential_issue_signals_json==before
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()

def test_review_history_is_scoped_to_current_assessment_version():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            old=EvidenceAssessment(id=940001,campaign_id=941001,result_id=942001,
                assessment_version=1,relevance_label='RELEVANT',potential_issue_signals_json='[]')
            current=EvidenceAssessment(id=940002,campaign_id=941001,result_id=942001,
                assessment_version=2,relevance_label='RELEVANT',potential_issue_signals_json='[]')
            db.add_all([old,current]);db.flush()
            db.add_all([
                EvidenceReview(assessment_id=old.id,reviewer_id='officer-a',
                    decision='FLAG_CONFIRMED',rationale='Initial officer review',
                    created_at=datetime(2026,10,1,9,0)),
                EvidenceReview(assessment_id=current.id,reviewer_id='officer-b',
                    decision='FURTHER_INVESTIGATION',rationale='Updated assessment needs corroboration',
                    created_at=datetime(2026,10,2,9,0))])
            db.commit()
            # History spans versions, while each review remains attached to its AI snapshot.
            rows=(db.query(EvidenceReview).join(EvidenceAssessment,
                     EvidenceReview.assessment_id==EvidenceAssessment.id)
                  .filter(EvidenceAssessment.campaign_id==941001,
                          EvidenceAssessment.result_id==942001)
                  .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).all())
            assert len(rows)==2
            assert rows[0].decision=='FURTHER_INVESTIGATION'
            assert rows[0].assessment_id==current.id
            assert rows[1].assessment_id==old.id
            assert db.get(EvidenceAssessment,old.id).assessment_version==1
            assert db.get(EvidenceAssessment,current.id).assessment_version==2
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()

def test_review_history_latest_ten_and_equal_timestamp_order():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            assessment=EvidenceAssessment(id=960001,campaign_id=961001,result_id=962001,
                assessment_version=1,relevance_label='RELEVANT',
                potential_issue_signals_json='[]')
            db.add(assessment);db.flush()
            shared_time=datetime(2026,10,19,8,0)
            for index in range(12):
                db.add(EvidenceReview(assessment_id=assessment.id,
                    reviewer_id=f'officer-{index}',
                    decision='FURTHER_INVESTIGATION',
                    rationale=f'Review iteration {index} with supporting notes',
                    created_at=shared_time))
            db.commit()
            ordered=(db.query(EvidenceReview,EvidenceAssessment.assessment_version)
                .join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
                .filter(EvidenceAssessment.campaign_id==961001,
                        EvidenceAssessment.result_id==962001,
                        EvidenceReview.decision.in_(['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']))
                .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc())
                .limit(10).all())
            assert len(ordered)==10
            assert [review.reviewer_id for review,_ in ordered]==[
                f'officer-{index}' for index in range(11,1,-1)]
            assert all(version==1 for _,version in ordered)
            assert db.query(EvidenceReview).filter_by(assessment_id=assessment.id).count()==12
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
