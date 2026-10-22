"""No-charge pilot sampling; never enqueues AI jobs or performs provider calls."""
import json
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
    except (TypeError,ValueError):raise ValueError('Select 40 or 50 posts') from None
    if limit not in (40,50):raise ValueError('Select 40 or 50 posts')
    try:anchor=int(data['anchor_id']) if data.get('anchor_id') is not None else None
    except (TypeError,ValueError):raise ValueError('Invalid sample anchor') from None
    if anchor is not None and anchor<=0:raise ValueError('Invalid sample anchor')
    query=(db.query(CampaignEvidence.id.label('link_id'),CampaignEvidence.result_id,
                    SocialListeningResult.run_id,SocialListeningResult.platform,
                    SocialListeningResult.published_at,SocialListeningResult.canonical_url,
                    func.substr(SocialListeningResult.text_content,1,300).label('excerpt'))
              .join(SocialListeningResult,CampaignEvidence.result_id==SocialListeningResult.id)
              .filter(CampaignEvidence.campaign_id==c.id))
    if anchor is not None:query=query.filter(CampaignEvidence.id<=anchor)
    newest=query.order_by(CampaignEvidence.id.desc()).limit(500).all()
    if anchor is None:anchor=newest[0].link_id if newest else 0
    visible=[row for row in newest if _result_in_scope(db,principal,SimpleNamespace(run_id=row.run_id))]
    chosen=choose_platform_sample(visible,limit)
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
    return {'campaign_id':str(c.id),'campaign_name':c.name,'requested':limit,
            'sample_anchor_id':anchor,'total':total,'records':rows,'counts':counts,
            'progress_percent':round(100*counts['completed']/total) if total else 0,
            'sampling_method':'Newest posts balanced across platforms (stable snapshot anchor)',
            'has_campaign_description':description,'active_admin_gates':active_gates,
            'main_keyword_count':len(json.loads(c.primary_keywords_json or '[]')),
            'secondary_keyword_count':len(json.loads(c.secondary_keywords_json or '[]')),
            'warnings':(['Add campaign description/objective before paid accuracy QA.'] if not description else [])
                      +(['No active Administration relevance gates.'] if not active_gates else []),
            'cost_note':'Preview costs 0 AI and 0 crawl credits. Actual future AI calls incur variable token charges.',
            'preview_only':True,'paid_provider_called':False}
