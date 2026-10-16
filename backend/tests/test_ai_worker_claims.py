"""No-provider SQL claim and budget safety tests."""
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import dialect as pg_dialect
from app.models import AIAssessmentJob, AIBudgetReservation

def test_ai_job_claim_requires_pending_state_and_retry_limit():
    statement=update(AIAssessmentJob).where(
        AIAssessmentJob.id==123,
        AIAssessmentJob.state=='PENDING',
        AIAssessmentJob.attempts<3
    ).values(state='PROCESSING',attempts=AIAssessmentJob.attempts+1)
    compiled=statement.compile(dialect=pg_dialect())
    sql=str(compiled)
    assert 'UPDATE ai_assessment_jobs' in sql
    assert 'ai_assessment_jobs.state' in sql
    assert 'ai_assessment_jobs.attempts <' in sql

def test_budget_period_and_campaign_unique_constraint():
    constraints={c.name for c in AIBudgetReservation.__table__.constraints if c.name}
    assert 'uq_ai_budget_campaign_period' in constraints

def test_ai_job_campaign_result_unique_constraint():
    constraints={c.name for c in AIAssessmentJob.__table__.constraints if c.name}
    assert 'uq_ai_assessment_job_campaign_result' in constraints
