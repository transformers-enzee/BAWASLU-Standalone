"""Bounded, post-collection AI contextual screening. No SocialCrawl requests."""
import json
import os
import logging
import threading
from sqlalchemy import update
from datetime import datetime, timedelta
import httpx
from .db import SessionLocal
from .models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment, IssueCategory, IssueCategoryPhrase, AIAssessmentJob, AIBudgetReservation

log=logging.getLogger(__name__)
_campaign_locks_guard=threading.Lock()
_campaign_locks={}
def _campaign_lock(campaign_id):
    with _campaign_locks_guard:
        return _campaign_locks.setdefault(int(campaign_id),threading.Lock())
def _arr(value):
    try:
        x=json.loads(value or '[]')
        return x if isinstance(x,list) else []
    except (TypeError,ValueError): return []

RELEVANCE_SCREENING_INSTRUCTIONS = """You are a neutral, evidence-grounded Indonesian election monitoring screener.
Return ONLY a JSON object with relevance_label (RELEVANT, IRRELEVANT, UNCERTAIN), confidence (LOW, MEDIUM, HIGH), explanation, locations (array of short strings), candidates (array of short strings), issue_category_ids (array of integer IDs), potential_violation_signals (array of objects each containing category_id integer and evidence_quote string from the provided source text).
FIRST assess topical relevance to the actual campaign objective using available caption and surrounding context, main and secondary keywords, and the Indonesian BAWASLU electoral oversight remit. A keyword or hashtag by itself is NOT evidence of topic relevance. Indonesian election news, credible election-administration activities, legitimate political discussion and public-order oversight can be RELEVANT even where there is no violation. Foreign elections unrelated to the campaign are IRRELEVANT.
SECOND, independently consider potential election-supervision issues, using ONLY configured active category IDs. No flagged category does NOT make a post irrelevant. Category association does not imply a violation. Only propose a potential_violation_signals entry when a concrete concern is supported by a verbatim source excerpt; ordinary campaigning or political opinion alone never qualifies. No issue signal is a legal finding.
If captions are vague, hashtags-only, or linked article/video substance is not in the supplied text, use UNCERTAIN rather than confidently excluding a plausibly relevant Indonesian election post. Do not invent linked material, location, people, allegations, or corroboration.
Explanations must separate what was actually observed from what remains unknown. Be politically neutral and do not infer misconduct from criticism or candidate mentions."""
VALID_RELEVANCE={'RELEVANT','IRRELEVANT','UNCERTAIN'}
def normalize_relevance_label(output):
    """Reject missing or unsupported labels without treating them as reviewed."""
    label=str(output.get('relevance_label') or '').strip().upper()
    return label if label in VALID_RELEVANCE else 'UNCERTAIN'

def enqueue_campaign_evidence(campaign_id):
    """Create durable pending rows; never calls an AI provider."""
    db=SessionLocal()
    try:
        linked=db.query(CampaignEvidence).filter_by(campaign_id=campaign_id).limit(500).all()
        added=0
        for link in linked:
            if db.query(EvidenceAssessment.id).filter_by(campaign_id=campaign_id,result_id=link.result_id).first():continue
            if db.query(AIAssessmentJob.id).filter_by(campaign_id=campaign_id,result_id=link.result_id).first():continue
            db.add(AIAssessmentJob(campaign_id=campaign_id,result_id=link.result_id,state='PENDING'));added+=1
        db.commit()
        return added
    finally:db.close()

def recover_stale_jobs(campaign_id=None):
    """Conditionally recover stale processing rows; never makes provider requests."""
    db=SessionLocal()
    try:
        cutoff=datetime.utcnow()-timedelta(minutes=10)
        query=db.query(AIAssessmentJob).filter(
            AIAssessmentJob.state=='PROCESSING',AIAssessmentJob.updated_at<cutoff)
        if campaign_id is not None:
            query=query.filter(AIAssessmentJob.campaign_id==int(campaign_id))
        updated=0
        for job in query.limit(500).all():
            new_state='FAILED' if job.attempts>=3 else 'PENDING'
            changed=db.execute(update(AIAssessmentJob).where(
                AIAssessmentJob.id==job.id,
                AIAssessmentJob.state=='PROCESSING',
                AIAssessmentJob.updated_at<cutoff
            ).values(state=new_state,last_error='Recovered stale processing job',
                     updated_at=datetime.utcnow()))
            updated+=int(changed.rowcount==1)
        db.commit()
        return updated
    finally:
        db.close()

def campaign_daily_budget_remaining(db,campaign_id):
    """Conservative request-count ceiling, not a monetary cost estimate."""
    try: ceiling=max(0,min(100,int(os.getenv('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN','0'))))
    except ValueError:ceiling=0
    today=datetime.utcnow().replace(hour=0,minute=0,second=0,microsecond=0)
    billed=db.query(AIAssessmentJob).filter(AIAssessmentJob.campaign_id==int(campaign_id),
        AIAssessmentJob.attempts>0,AIAssessmentJob.updated_at>=today).all()
    return max(0,ceiling-sum(j.attempts for j in billed))

def campaign_lifetime_budget_remaining(db,campaign_id):
    """Fail-closed lifetime attempt ceiling; avoids unlimited spending across UTC days."""
    try: ceiling=max(0,min(500,int(os.getenv('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN','0'))))
    except ValueError:ceiling=0
    jobs=db.query(AIAssessmentJob).filter(AIAssessmentJob.campaign_id==int(campaign_id),
        AIAssessmentJob.attempts>0).all()
    return max(0,ceiling-sum(job.attempts for job in jobs))

def reserve_automatic_ai_request(db,campaign_id):
    """Atomically reserve both quotas before any paid automatic provider request."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert
    try:
        daily=max(0,min(100,int(os.getenv('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN','0'))))
        lifetime=max(0,min(500,int(os.getenv('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN','0'))))
    except (ValueError,TypeError):return False
    if not daily or not lifetime:return False
    period=datetime.utcnow().strftime('%Y-%m-%d')
    try:
        dialect=db.bind.dialect.name
        # SQLite ignores SELECT FOR UPDATE; refuse unattended billing unless PostgreSQL provides row locks.
        if dialect!='postgresql':return False
        ins=pg_insert
        for key in ('lifetime',period):
            db.execute(ins(AIBudgetReservation).values(campaign_id=int(campaign_id),
                       budget_period=key,reserved_requests=0).on_conflict_do_nothing(
                       index_elements=['campaign_id','budget_period']))
        db.commit()
        # Lock the campaign lifetime row to serialize reservations across processes.
        lifetime_row=db.query(AIBudgetReservation).filter_by(campaign_id=int(campaign_id),
                            budget_period='lifetime').with_for_update().one()
        daily_row=db.query(AIBudgetReservation).filter_by(campaign_id=int(campaign_id),
                         budget_period=period).with_for_update().one()
        if lifetime_row.reserved_requests>=lifetime or daily_row.reserved_requests>=daily:
            db.rollback()
            return False
        lifetime_row.reserved_requests+=1
        daily_row.reserved_requests+=1
        db.commit()
        return True
    except Exception:
        db.rollback()
        log.exception('AI quota reservation refused')
        return False

def _assess_pending_campaign_locked(campaign_id, requested_limit=None):
    """Background task; each newly collected run processes at most configured AI requests."""
    if not os.getenv('OPENAI_API_KEY','').strip():
        log.info('AI screening skipped: OPENAI_API_KEY missing')
        return
    try: limit=max(0,min(25,int(os.getenv('BAWASLU_AI_ASSESSMENTS_PER_RUN','12'))))
    except ValueError: limit=12
    if requested_limit is not None: limit=min(limit,max(0,int(requested_limit)))
    if not limit:return
    db=SessionLocal()
    try:
        campaign=db.get(MonitoringCampaign,int(campaign_id))
        if not campaign:return
        # Automatic jobs require an explicit daily request ceiling.
        if requested_limit is None:
            # Reservations, not mutable job timestamps, are authoritative for automatic quotas.
            limit=min(limit,max(0,int(os.getenv('BAWASLU_AI_DAILY_REQUEST_LIMIT_PER_CAMPAIGN','0'))),max(0,int(os.getenv('BAWASLU_AI_LIFETIME_REQUEST_LIMIT_PER_CAMPAIGN','0'))))
            if not limit:return
        categories=db.query(IssueCategory).filter(IssueCategory.active==True).order_by(IssueCategory.sort_order).limit(50).all()
        category_names={c.id:c.name for c in categories}
        phrases=db.query(IssueCategoryPhrase).filter(IssueCategoryPhrase.active==True,IssueCategoryPhrase.category_id.in_(list(category_names))).limit(400).all() if category_names else []
        taxonomy=[{'id':c.id,'name':c.name,'phrases':[p.phrase for p in phrases if p.category_id==c.id][:12]} for c in categories]
        enqueue_campaign_evidence(campaign.id)
        links=db.query(CampaignEvidence).filter(CampaignEvidence.campaign_id==campaign.id).order_by(CampaignEvidence.id.desc()).limit(300).all()
        used=0
        for link in links:
            if used>=limit: break
            exists=db.query(EvidenceAssessment.id).filter_by(campaign_id=campaign.id,result_id=link.result_id).first()
            if exists:continue
            job=db.query(AIAssessmentJob).filter_by(campaign_id=campaign.id,result_id=link.result_id).first()
            if job and job.state in ('COMPLETED','PROCESSING'):continue
            if job and job.attempts>=3:continue
            item=db.get(SocialListeningResult,link.result_id)
            if not item:continue
            if not job:continue
            # Manual calls still need a pending reservation row; automatic calls are separately budgeted.
            # Atomic state transition prevents a second process from claiming the same row.
            claimed=db.execute(update(AIAssessmentJob).where(
                AIAssessmentJob.id==job.id,
                AIAssessmentJob.state=='PENDING',
                AIAssessmentJob.attempts<3
            ).values(state='PROCESSING',attempts=AIAssessmentJob.attempts+1,
                     updated_at=datetime.utcnow()))
            db.commit()
            if claimed.rowcount!=1:continue
            db.refresh(job)
            if requested_limit is None and not reserve_automatic_ai_request(db,campaign.id):
                job.state='PENDING';job.updated_at=datetime.utcnow();db.commit()
                break
            used+=1
            payload={'campaign':{'name':campaign.name,'objective':campaign.description,'main_keywords':_arr(campaign.primary_keywords_json),'secondary_keywords':_arr(campaign.secondary_keywords_json),'excluded_keywords':_arr(campaign.excluded_keywords_json)},'source':{'text':(item.text_content or '')[:5000],'platform':item.platform,'author':item.author_name},'active_issue_categories':taxonomy}
            try:
                model=os.getenv('BAWASLU_RELEVANCE_MODEL','gpt-4o-mini')
                url=os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')+'/chat/completions'
                response=httpx.post(url,headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},
                    json={'model':model,'temperature':0,'max_tokens':550,'response_format':{'type':'json_object'},
                    'messages':[{'role':'system','content':RELEVANCE_SCREENING_INSTRUCTIONS},
                    {'role':'user','content':json.dumps(payload,ensure_ascii=False)}]},timeout=30)
                response.raise_for_status()
                out=json.loads(response.json()['choices'][0]['message']['content'])
                label=normalize_relevance_label(out)
                confidence=str(out.get('confidence','LOW')).upper()
                if confidence not in ('LOW','MEDIUM','HIGH'):confidence='LOW'
                def strings(key):
                    v=out.get(key)
                    return [str(x)[:160] for x in v[:12] if isinstance(x,str)] if isinstance(v,list) else []
                issue_ids=out.get('issue_category_ids',[])
                issue_ids=[x for x in issue_ids if type(x) is int and x in category_names] if isinstance(issue_ids,list) else []
                signals=[]
                raw_signals=out.get('potential_violation_signals')
                if isinstance(raw_signals,list):
                    for signal in raw_signals[:8]:
                        if not isinstance(signal,dict):continue
                        cid=signal.get('category_id')
                        quote=str(signal.get('evidence_quote') or '').strip()
                        if type(cid) is int and cid in category_names and len(quote)>=12 and quote.casefold() in (item.text_content or '').casefold():
                            signals.append({'category_id':cid,'explanation':'Preliminary AI concern based on source excerpt','evidence_quote':quote[:350],'signal_type':'POTENTIAL_VIOLATION'})
                record=EvidenceAssessment(campaign_id=campaign.id,result_id=item.id,assessment_version=1,
                    model_version=model,relevance_label=label,relevance_confidence=confidence,
                    explanation=str(out.get('explanation') or '')[:1200],candidate_signals_json=json.dumps(strings('candidates')),
                    geographic_signals_json=json.dumps(strings('locations')),
                    potential_issue_signals_json=json.dumps(signals))
                db.add(record)
                if job:job.state='COMPLETED';job.last_error='';job.updated_at=datetime.utcnow()
                db.commit()
            except (httpx.HTTPError,KeyError,ValueError,TypeError,IndexError) as exc:
                db.rollback()
                if job:
                    job=db.get(AIAssessmentJob,job.id)
                    job.state='FAILED' if job.attempts>=3 else 'PENDING'
                    job.last_error=type(exc).__name__
                    job.updated_at=datetime.utcnow()
                    db.commit()
                log.warning('AI screening stopped after request error: %s',type(exc).__name__)
                break
    finally:
        db.close()


def assess_pending_campaign(campaign_id, requested_limit=None):
    """Allow only one worker per campaign in each process. Multi-process locking is still required."""
    lock=_campaign_lock(campaign_id)
    if not lock.acquire(blocking=False):
        log.info('AI campaign %s already processing in this instance',campaign_id)
        return
    try:
        return _assess_pending_campaign_locked(campaign_id,requested_limit)
    finally:
        lock.release()
