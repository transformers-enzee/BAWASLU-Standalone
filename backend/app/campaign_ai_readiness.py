"""Read-only, campaign-scoped queued AI assessment readiness and budget audit.

This is NOT an AI authorization or dispatch action. The actual worker still
must atomically claim a job and reserve quota before calling the provider.
"""
from datetime import datetime
import os
from sqlalchemy import and_, case, func, or_
from .models import AIAssessmentJob, AIBudgetReservation, CampaignEvidence, SocialListeningResult, EvidenceAssessment

def campaign_ai_worker_readiness(db,campaign_id,env=None):
    settings=os.environ if env is None else env
    cid=int(campaign_id)
    def cap(name, maximum):
        try:return max(0,min(maximum,int(settings.get(name,'0'))))
        except (TypeError,ValueError):return 0
    worker=str(settings.get('BAWASLU_AI_WORKER_ENABLED','false')).lower()=='true'
    enabled=str(settings.get('BAWASLU_AUTO_AI_SCREENING_ENABLED','false')).lower()=='true'
    provider=bool(str(settings.get('OPENAI_API_KEY','')).strip())
    daily=cap('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN',1000)
    lifetime=cap('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN',5000)
    per_run=cap('BAWASLU_AI_ASSESSMENTS_PER_RUN',50)
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
    # Match the authoritative manually-confirmed batch preview: an older PENDING
    # job may already have been assessed through another route. It must not
    # inflate the next-run estimate or be sent to the provider again.
    latest_id=(db.query(EvidenceAssessment.id)
        .filter(EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
                EvidenceAssessment.result_id==CampaignEvidence.result_id)
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).limit(1)
        .correlate(CampaignEvidence).scalar_subquery())
    unassessed=or_(EvidenceAssessment.id.is_(None),
       func.upper(func.coalesce(EvidenceAssessment.relevance_label,'')).in_(['','UNASSESSED']))
    assessed=~unassessed
    def amount(condition):
        return func.coalesce(func.sum(case((condition,1),else_=0)),0)
    counts=(db.query(
        func.count(AIAssessmentJob.id),
        amount(AIAssessmentJob.state=='PENDING'),
        amount(and_(pending,text_exists,unassessed)),
        amount(and_(pending,~text_exists,unassessed)),
        amount(and_(AIAssessmentJob.state=='PENDING',AIAssessmentJob.attempts>=3)),
        amount(AIAssessmentJob.state=='PROCESSING'),
        amount(AIAssessmentJob.state=='COMPLETED'),
        amount(AIAssessmentJob.state=='FAILED'),
        amount(AIAssessmentJob.state=='SUPERSEDED_ASSESSED'))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .outerjoin(SocialListeningResult,SocialListeningResult.id==CampaignEvidence.result_id)
        .outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT').one())
    total,pending_count,claimable,missing_text,attempt_cap,processing,completed,failed,superseded=map(int,counts)
    preassessed_pending=(db.query(func.count(AIAssessmentJob.id))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .join(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                AIAssessmentJob.state=='PENDING',assessed).scalar()) or 0
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
            'processing':processing,'completed':completed,'failed':failed,
            'superseded_assessed':superseded},
        'pending_already_assessed_excluded_from_ai':int(preassessed_pending),
        'estimated_max_requests_next_run':capacity if not reasons else 0,
        'ready_to_process':not reasons,
        'readiness_blockers':reasons,
        'readiness_is_authorization':False,
        'paid_ai_executed':False,
        'paid_provider_called':False,
        'database_writes':0,
    }

def campaign_manual_batch_preview(db,campaign_id,requested_limit,env=None):
    """No-cost read of eligible queued evidence and quota for explicit approval.

    Manual approval is separate from AUTO screening flags. The worker's
    budget reservation remains authoritative at execution time.
    """
    from .models import EvidenceAssessment
    from sqlalchemy import or_
    settings=os.environ if env is None else env
    if type(requested_limit) is not int or not 1<=requested_limit<=20:
        raise ValueError('Choose an integer batch size between 1 and 20')
    cid=int(campaign_id)
    try:
        run_limit=max(0,min(50,int(settings.get('BAWASLU_AI_ASSESSMENTS_PER_RUN','12'))))
        daily=max(0,min(1000,int(settings.get('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN','0'))))
        lifetime=max(0,min(5000,int(settings.get('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN','0'))))
    except (ValueError,TypeError):
        run_limit=daily=lifetime=0
    today=datetime.utcnow().strftime('%Y-%m-%d')
    reserved=(db.query(AIBudgetReservation.budget_period,
                       AIBudgetReservation.reserved_requests)
        .filter(AIBudgetReservation.campaign_id==cid,
                AIBudgetReservation.budget_period.in_([today,'lifetime'])).all())
    daily_used=sum(int(x.reserved_requests) for x in reserved if x.budget_period==today)
    life_used=sum(int(x.reserved_requests) for x in reserved if x.budget_period=='lifetime')
    # Latest assessment controls whether a historical source remains unassessed.
    latest_id=(db.query(EvidenceAssessment.id)
        .filter(EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
                EvidenceAssessment.result_id==CampaignEvidence.result_id)
        .order_by(EvidenceAssessment.assessment_version.desc(),
                  EvidenceAssessment.id.desc()).limit(1)
        .correlate(CampaignEvidence).scalar_subquery())
    label=func.upper(func.coalesce(EvidenceAssessment.relevance_label,''))
    eligible=(db.query(func.count(AIAssessmentJob.id))
        .join(CampaignEvidence,and_(
            CampaignEvidence.campaign_id==AIAssessmentJob.campaign_id,
            CampaignEvidence.result_id==AIAssessmentJob.result_id))
        .join(SocialListeningResult,SocialListeningResult.id==CampaignEvidence.result_id)
        .outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .filter(AIAssessmentJob.campaign_id==cid,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                AIAssessmentJob.state=='PENDING',
                AIAssessmentJob.attempts<3,
                func.length(func.trim(func.coalesce(SocialListeningResult.text_content,'')))>0,
                or_(EvidenceAssessment.id.is_(None),
                    label.in_(['','UNASSESSED']))).scalar()) or 0
    postgres=db.bind.dialect.name=='postgresql'
    configured=bool(str(settings.get('OPENAI_API_KEY','')).strip())
    cap=min(int(eligible),requested_limit,run_limit,
            max(0,daily-daily_used),max(0,lifetime-life_used))
    if not configured or not postgres:cap=0
    return {
       'campaign_id':str(cid),'unassessed':int(eligible),
       'eligible_queued_unassessed':int(eligible),
       'batch_limit':cap,'requested_sample_limit':requested_limit,
       'ai_key_configured':configured,'database_supports_reservations':postgres,
       'daily_request_limit':daily,'lifetime_request_limit':lifetime,
       'daily_reserved':daily_used,'lifetime_reserved':life_used,
       'daily_remaining':max(0,daily-daily_used),
       'lifetime_remaining':max(0,lifetime-life_used),
       'per_run_request_limit':run_limit,
       'socialcrawl_credits':0,'estimated_ai_requests':cap,
       'ai_token_cost_estimate':'Variable; provider token pricing applies',
       'paid_ai_executed':False,'paid_provider_called':False,'database_writes':0,
       'preview_is_authorization':False,
       'historical_window_limit_applied':False,
    }
