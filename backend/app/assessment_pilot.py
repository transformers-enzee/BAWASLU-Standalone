"""No-charge pilot sampling; never enqueues AI jobs or performs provider calls."""
import json
import os
from datetime import datetime
from collections import defaultdict
from types import SimpleNamespace
from sqlalchemy import func
from .access import allowed, has
from .models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment, AIAssessmentJob, RelevanceGateQuestion
from .socialcrawl import _result_in_scope

def choose_platform_sample(rows, limit):
    buckets=defaultdict(list)
    for row in rows: buckets[str(row.platform or 'unknown').lower()].append(row)
    platforms=sorted(buckets,key=lambda k:(-len(buckets[k]),k))
    sample=[];index=0
    while len(sample)<limit:
        added=False
        for platform in platforms:
            if index<len(buckets[platform]):
                sample.append(buckets[platform][index]);added=True
                if len(sample)==limit:break
        if not added:break
        index+=1
    return sample

def assessment_pilot_preview(db,principal,data,campaign_id):
    if not has(principal,'view_intelligence'):raise PermissionError('Intelligence access required')
    if not str(campaign_id or '').isdigit():raise ValueError('Select a campaign')
    c=db.get(MonitoringCampaign,int(campaign_id))
    if not c or not allowed(principal,c):raise PermissionError('Campaign not available')
    data=data if isinstance(data,dict) else {}
    try:limit=int(data.get('sample_size',40))
    except (TypeError,ValueError):raise ValueError('Select 10, 40 or 50 posts') from None
    if limit not in (10,40,50):raise ValueError('Select 10, 40 or 50 posts')
    try:anchor=int(data['anchor_id']) if data.get('anchor_id') is not None else None
    except (TypeError,ValueError):raise ValueError('Invalid sample anchor') from None
    if anchor is not None and anchor<=0:raise ValueError('Invalid sample anchor')
    query=(db.query(CampaignEvidence.id.label('link_id'),CampaignEvidence.result_id,
                    SocialListeningResult.run_id,SocialListeningResult.platform,
                    SocialListeningResult.published_at,SocialListeningResult.canonical_url,
                    func.substr(SocialListeningResult.text_content,1,300).label('excerpt'))
              .join(SocialListeningResult,CampaignEvidence.result_id==SocialListeningResult.id)
              .filter(CampaignEvidence.campaign_id==c.id,
                      CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'))
    if anchor is not None:query=query.filter(CampaignEvidence.id<=anchor)
    newest=query.order_by(CampaignEvidence.id.desc()).limit(500).all()
    if anchor is None:anchor=newest[0].link_id if newest else 0
    visible=[row for row in newest if _result_in_scope(db,principal,SimpleNamespace(run_id=row.run_id))]
    if limit==10:
        # Ten newest campaign-linked posts form a stable, anchored cohort.
        # Completed records remain visible for progress, and the start
        # endpoint enqueues only NOT_QUEUED records (never bills them again).
        chosen=visible[:limit]
    else:
        chosen=choose_platform_sample(visible,limit)
    # Cursor points below the oldest evidence link in this fixed snapshot.
    # Changing the cursor is explicit; refresh/start retain the current anchor.
    next_anchor_id=min(row.link_id for row in chosen)-1 if chosen else None
    ids=[row.result_id for row in chosen]
    assessments={};jobs={}
    if ids:
        records=(db.query(EvidenceAssessment)
                 .filter(EvidenceAssessment.campaign_id==c.id,EvidenceAssessment.result_id.in_(ids))
                 .order_by(EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc()).all())
        for a in records:assessments.setdefault(a.result_id,a)
        jobs={job.result_id:job for job in db.query(AIAssessmentJob).filter(
            AIAssessmentJob.campaign_id==c.id,AIAssessmentJob.result_id.in_(ids)).all()}
    counts={'completed':0,'processing':0,'queued':0,'failed':0,'not_queued':0}
    rows=[]
    for post in chosen:
        assessment=assessments.get(post.result_id);job=jobs.get(post.result_id)
        label=str(assessment.relevance_label or '').upper() if assessment else ''
        if label and label!='UNASSESSED':state='COMPLETED';counts['completed']+=1
        elif job and job.state=='PROCESSING':state='PROCESSING';counts['processing']+=1
        elif job and job.state=='PENDING':state='QUEUED';counts['queued']+=1
        elif job and job.state in ('FAILED','COMPLETED'):state='FAILED';counts['failed']+=1
        else:state='NOT_QUEUED';counts['not_queued']+=1
        url=post.canonical_url
        rows.append({'id':str(post.result_id),'platform':post.platform or 'Unknown',
                    'published_at':post.published_at,'text_excerpt':post.excerpt or '',
                    'source_url':url if isinstance(url,str) and url.startswith('https://') else None,
                    'assessment_state':state,'relevance_label':label if state=='COMPLETED' else None})
    active_gates=db.query(RelevanceGateQuestion.id).filter(RelevanceGateQuestion.active.is_(True)).count()
    description=bool(str(c.description or '').strip())
    total=len(rows)
    readiness=pilot_readiness(db,c)
    return {'readiness':readiness,
            'campaign_id':str(c.id),'campaign_name':c.name,'requested':limit,
            'sample_anchor_id':anchor,'next_anchor_id':next_anchor_id,'total':total,'records':rows,'counts':counts,
            'progress_percent':round(100*counts['completed']/total) if total else 0,
            'sampling_method':('Newest unassessed posts only (stable snapshot anchor)' if limit==10 else 'Newest posts balanced across platforms (stable snapshot anchor)'),
            'has_campaign_description':description,'active_admin_gates':active_gates,
            'main_keyword_count':len(json.loads(c.primary_keywords_json or '[]')),
            'secondary_keyword_count':len(json.loads(c.secondary_keywords_json or '[]')),
            'warnings':(['Add campaign description/objective before paid accuracy QA.'] if not description else [])
                      +(['No active Administration relevance gates.'] if not active_gates else []),
            'cost_note':'Preview costs 0 AI and 0 crawl credits. Actual future AI calls incur variable token charges.',
            'preview_only':True,'paid_provider_called':False}


def pilot_readiness(db,campaign):
    """Fail-closed request-budget readiness; token-based cost is not estimated."""
    from .models import AIBudgetReservation
    today=datetime.utcnow().strftime('%Y-%m-%d')
    def cap(name,maxval):
        try:return max(0,min(maxval,int(os.getenv(name,'0'))))
        except (TypeError,ValueError):return 0
    daily=cap('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN',400)
    lifetime=cap('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN',500)
    per_run=cap('BAWASLU_AI_ASSESSMENTS_PER_RUN',25)
    reserved={x.budget_period:x.reserved_requests for x in db.query(AIBudgetReservation).filter(
        AIBudgetReservation.campaign_id==campaign.id,AIBudgetReservation.budget_period.in_(['lifetime',today])).all()}
    daily_remaining=max(0,daily-reserved.get(today,0))
    lifetime_remaining=max(0,lifetime-reserved.get('lifetime',0))
    remaining=min(daily_remaining,lifetime_remaining)
    configured=bool(os.getenv('OPENAI_API_KEY','').strip())
    return {'ai_provider_configured':configured,'request_budget_remaining':remaining,
            'daily_request_limit':daily,'lifetime_request_limit':lifetime,
            'daily_requests_reserved':reserved.get(today,0),
            'lifetime_requests_reserved':reserved.get('lifetime',0),
            'daily_requests_remaining':daily_remaining,
            'lifetime_requests_remaining':lifetime_remaining,
            'per_run_limit':per_run,
            'per_request_worker_enabled':per_run>0,
            'database_supports_reservations':db.bind.dialect.name=='postgresql',
            'billing_model':'One model request per post, variable token charges; no SocialCrawl credits'}


def start_assessment_pilot(db, principal, payload, campaign_id):
    """Explicitly enroll only the currently selected sample; never call AI in this transaction."""
    from .models import AIAssessmentJob
    from .access import has
    if principal.get('role')!='National Administrator' or not has(principal,'administration'):
        raise PermissionError('National Administrator approval required for paid pilot')
    payload=payload if isinstance(payload,dict) else {}
    if payload.get('confirm_ai_cost') is not True:
        raise ValueError('Explicit paid AI request confirmation required')
    if not str(campaign_id or '').isdigit():raise ValueError('Select a campaign')
    # Serialize concurrent starts for one campaign across Render processes.
    campaign=(db.query(MonitoringCampaign).filter(MonitoringCampaign.id==int(campaign_id))
              .with_for_update().first())
    if campaign is None or not allowed(principal,campaign):
        raise PermissionError('Campaign unavailable to your account')
    if not str(campaign.description or '').strip():
        raise ValueError('Add the campaign objective/description before starting paid AI analysis')
    try:
        anchor=int(payload.get('anchor_id',0))
    except (TypeError,ValueError):
        raise ValueError('Preview the sample before starting') from None
    if anchor<=0:raise ValueError('Preview the sample before starting')
    if payload.get('resume') is True:
        resume=True
    else:
        resume=False
    preview=assessment_pilot_preview(db,principal,{
        'sample_size':payload.get('sample_size'),
        'anchor_id':anchor,
    },campaign.id)
    expected=payload.get('expected_result_ids')
    ids=[row['id'] for row in preview['records']]
    if len(ids)!=preview['requested'] or expected!=ids:
        raise ValueError('Sample changed; refresh the preview before approving costs')
    readiness=preview['readiness']
    if not readiness['ai_provider_configured']:
        raise ValueError('AI provider key is not configured')
    if not readiness['per_request_worker_enabled'] or not readiness['database_supports_reservations']:
        raise ValueError('AI worker request limit or protected database reservations unavailable')
    if preview['counts']['processing']>0:
        raise ValueError('This sample is already being assessed; refresh progress')
    if preview['counts']['failed']>0:
        raise ValueError('Failed or ambiguous paid AI calls require human review; do not retry automatically')
    if resume:
        if not preview['counts']['queued']:
            raise ValueError('No queued posts remain to resume')
        target=[row['id'] for row in preview['records'] if row['assessment_state']=='QUEUED']
    else:
        if preview['counts']['queued']:
            raise ValueError('Existing queued posts found. Use Resume queued batch to avoid duplicates')
        target=[row['id'] for row in preview['records'] if row['assessment_state']=='NOT_QUEUED']
        if not target:
            raise ValueError('No unassessed posts to enqueue')
    if readiness['request_budget_remaining']<len(target):
        raise ValueError(
            f"AI request budget: {readiness['request_budget_remaining']} available, "
            f"{len(target)} requested. Daily: {readiness['daily_requests_reserved']}/"
            f"{readiness['daily_request_limit']}; lifetime: "
            f"{readiness['lifetime_requests_reserved']}/"
            f"{readiness['lifetime_request_limit']}. "
            "Select a smaller batch or wait for the daily allowance to reset; "
            "do not retry paid requests automatically."
        )
    # Database row lock + unique constraint keep start idempotent.
    for rid in target:
        if not resume:
            db.add(AIAssessmentJob(campaign_id=campaign.id,result_id=int(rid),
                                   state='PENDING',attempts=0))
    db.commit()
    return {'campaign_id':str(campaign.id),'batch_result_ids':[int(x) for x in target],
            'queued':len(target),'started':True,'socialcrawl_credits':0,
            'billing_confirmed':True,'paid_provider_called':False,
            'notice':'Saved selected jobs. AI screening starts after the HTTP response.'}


def execute_assessment_pilot(campaign_id,result_ids):
    """Best-effort in-process runner; persisted jobs allow explicit recovery after a restart.

    A job with an ambiguous provider outcome is FAILED rather than retried.
    """
    from .auto_relevance import assess_pending_campaign
    for result_id in result_ids:
        assess_pending_campaign(int(campaign_id),requested_limit=1,target_result_id=int(result_id))
