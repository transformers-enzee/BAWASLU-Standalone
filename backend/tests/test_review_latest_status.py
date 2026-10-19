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

def test_review_history_never_leaks_across_campaigns_or_evidence():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            snapshots=[
                EvidenceAssessment(id=970001,campaign_id=971001,result_id=972001,assessment_version=1,relevance_label='RELEVANT',potential_issue_signals_json='[]'),
                EvidenceAssessment(id=970002,campaign_id=971002,result_id=972001,assessment_version=1,relevance_label='RELEVANT',potential_issue_signals_json='[]'),
                EvidenceAssessment(id=970003,campaign_id=971001,result_id=972002,assessment_version=1,relevance_label='RELEVANT',potential_issue_signals_json='[]'),
            ]
            db.add_all(snapshots);db.flush()
            for assessment,decision in zip(snapshots,['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']):
                db.add(EvidenceReview(assessment_id=assessment.id,reviewer_id='reviewer',
                    decision=decision,rationale='Review for isolated scope only'))
            db.commit()
            def history(campaign_id,result_id):
                return (db.query(EvidenceReview,EvidenceAssessment.assessment_version)
                    .join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
                    .filter(EvidenceAssessment.campaign_id==campaign_id,
                            EvidenceAssessment.result_id==result_id,
                            EvidenceReview.decision.in_(['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']))
                    .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc())
                    .limit(10).all())
            assert [x.decision for x,_ in history(971001,972001)]==['FLAG_CONFIRMED']
            assert [x.decision for x,_ in history(971002,972001)]==['FLAG_DISMISSED']
            assert [x.decision for x,_ in history(971001,972002)]==['FURTHER_INVESTIGATION']
            assert history(971002,972002)==[]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()

def test_review_history_excludes_other_campaign_and_unknown_decision():
    engine=create_engine('sqlite:///:memory:')
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as db:
            own=EvidenceAssessment(id=980001,campaign_id=981001,result_id=982001,
                assessment_version=1,relevance_label='RELEVANT',potential_issue_signals_json='[]')
            other=EvidenceAssessment(id=980002,campaign_id=981002,result_id=982001,
                assessment_version=1,relevance_label='RELEVANT',potential_issue_signals_json='[]')
            db.add_all([own,other]);db.flush()
            db.add_all([
                EvidenceReview(assessment_id=own.id,reviewer_id='authorized',
                    decision='FLAG_DISMISSED',rationale='No independently corroborated evidence'),
                EvidenceReview(assessment_id=own.id,reviewer_id='legacy',
                    decision='UNSUPPORTED_DECISION',rationale='Legacy unrelated status'),
                EvidenceReview(assessment_id=other.id,reviewer_id='other-campaign',
                    decision='FLAG_CONFIRMED',rationale='Other campaign confidential review')])
            db.commit()
            rows=(db.query(EvidenceReview,EvidenceAssessment.assessment_version)
                .join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
                .filter(EvidenceAssessment.campaign_id==981001,
                        EvidenceAssessment.result_id==982001,
                        EvidenceReview.decision.in_(['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']))
                .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).limit(10).all())
            assert len(rows)==1
            assert rows[0][0].reviewer_id=='authorized'
            assert rows[0][0].decision=='FLAG_DISMISSED'
            assert db.query(EvidenceReview).count()==3
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
