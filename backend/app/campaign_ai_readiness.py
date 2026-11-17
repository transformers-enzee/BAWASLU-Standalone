"""Read-only, campaign-scoped queued AI assessment readiness and budget audit.

This is NOT an AI authorization or dispatch action. The actual worker still
must atomically claim a job and reserve quota before calling the provider.
"""
from datetime import datetime
import os
from sqlalchemy import and_, case, func
from .models import AIAssessmentJob, AIBudgetReservation, CampaignEvidence, SocialListeningResult

def campaign_ai_worker_readiness(db,campaign_id,env=None):
    settings=os.environ if env is None else env
    cid=int(campaign_id)
    def cap(name, maximum):
        try:return max(0,min(maximum,int(settings.get(name,'0'))))
        except (TypeError,ValueError):return 0
    worker=str(settings.get('BAWASLU_AI_WORKER_ENABLED','false')).lower()=='true'
    enabled=str(settings.get('BAWASLU_AUTO_AI_SCREENING_ENABLED','false')).lower()=='true'
    provider=bool(str(settings.get('OPENAI_API_KEY','')).strip())
    daily=cap('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN',100)
    lifetime=cap('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN',500)
    per_run=cap('BAWASLU_AI_ASSESSMENTS_PER_RUN',25)
    postgres=db.bind.dialect.name=='postgresql'
    today=datetime.utcnow().strftime('%Y-%m-%d')
    daily_used,lifetime_used=(db.query(
        func.coalesce(func.sum(case((AIBudgetReservation.budget_period==today,
                                     AIBudgetReservation.reserved_requests),else_=0)),0),
        func.coalesce(func.sum(case((AIBudgetReservation.budget_period=='lifetime',
                                     AIBudgetReservation.reserved_requests),else_=0)),0))
        .filter(AIBudgetReservation.campaign_id==cid,
                AIBudgetReservation.budget_period.in_([today,'lifetime'])).one())
    daily_used=int(daily_used); lifetime_used=int(lifetime_used)
    daily_remaining=max(0,daily-daily_used)
    lifetime_remaining=max(0,lifetime-lifetime_used)
    pending=and_(AIAssessmentJob.state=='PENDING',AIAssessmentJob.attempts<3)
    text_exists=and_(SocialListeningResult.id.is_not(None),
            func.length(func.trim(func.coalesce(SocialListeningResult.text_content,'')))>0)
    def amount(condition):
        return func.coalesce(func.sum(case((condition,1),else_=0)),0)
    counts=(db.query(
        func.count(AIAssessmentJob.id),
        amount(AIAssessmentJob.state=='PENDING'),
        amount(and_(pending,text_exists)),
        amount(and_(pending,~text_exists)),
        amount(and_(AIAssessmentJob.state=='PENDING',AIAssessmentJob.attempts>=3)),
        amount(AIAssessmentJob.state=='PROCESSING'),
        amount(AIAssessmentJob.state=='COMPLETED'),
        amount(AIAssessmentJob.state=='FAILED'))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .outerjoin(SocialListeningResult,SocialListeningResult.id==CampaignEvidence.result_id)
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT').one())
    total,pending_count,claimable,missing_text,attempt_cap,processing,completed,failed=map(int,counts)
    capacity=min(claimable,per_run,daily_remaining,lifetime_remaining)
    reasons=[]
    if not worker:reasons.append('WORKER_DISABLED')
    if not enabled:reasons.append('AUTO_SCREENING_DISABLED')
    if not provider:reasons.append('AI_PROVIDER_NOT_CONFIGURED')
    if not postgres:reasons.append('POSTGRES_RESERVATION_REQUIRED')
    if not daily_remaining or not lifetime_remaining:reasons.append('AI_REQUEST_BUDGET_EXHAUSTED')
    if not per_run:reasons.append('PER_RUN_LIMIT_ZERO')
    if not claimable:reasons.append('NO_CLAIMABLE_JOBS')
    return {
        'worker_enabled':worker,'automatic_screening_enabled':enabled,
        'database_supports_reservations':postgres,'ai_provider_configured':provider,
        'daily_request_limit':daily,'lifetime_request_limit':lifetime,
        'per_run_request_limit':per_run,'daily_reserved':daily_used,
        'lifetime_reserved':lifetime_used,
        'daily_remaining':daily_remaining,'lifetime_remaining':lifetime_remaining,
        'queue_counts':{'ordinary_jobs':total,'pending':pending_count,
            'claimable_pending_with_text':claimable,
            'pending_missing_source_or_text':missing_text,
            'pending_attempts_exhausted':attempt_cap,
            'processing':processing,'completed':completed,'failed':failed},
        'estimated_max_requests_next_run':capacity if not reasons else 0,
        'ready_to_process':not reasons,
        'readiness_blockers':reasons,
        'readiness_is_authorization':False,
        'paid_ai_executed':False,
        'paid_provider_called':False,
        'database_writes':0,
    }
