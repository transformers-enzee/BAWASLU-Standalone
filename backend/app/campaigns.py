"""Architecture v2 campaign configuration — no paid crawl execution.

A campaign is a persistent plan, distinct from any provider run. All actions
are enforced in the existing authenticated Social Listening API.
"""
import json
from datetime import date, datetime, timezone
from sqlalchemy.orm import Session
from .models import MonitoringCampaign, CampaignRun, CampaignEvidence
from .access import has, allowed, audit
from .socialcrawl import _scope_filters, AVAILABLE_PLATFORMS

MAX_KEYWORDS=30
MAX_CAMPAIGNS_PER_LIST=200
MAX_NAME=255

def _keywords(value,label,mandatory=False):
    if not isinstance(value,list):
        raise ValueError(label+' must be a list of keywords')
    if len(value)>MAX_KEYWORDS:
        raise ValueError(label+' exceeds 30 keywords')
    found={}
    for entry in value:
        if not isinstance(entry,str):
            raise ValueError(label+' must contain text')
        value=entry.strip()
        if not value or len(value)>120:
            raise ValueError(label+' keywords must be 1–120 characters')
        found.setdefault(value.casefold(),value)
    if mandatory and not found: raise ValueError(label+' requires at least one keyword')
    return list(found.values())

def _iso_date(value,label):
    if not value: return ''
    if not isinstance(value,str): raise ValueError(label+' must be a date')
    try: return date.fromisoformat(value).isoformat()
    except ValueError: raise ValueError(label+' must be YYYY-MM-DD')

def _normalize(db,p,data):
    if not isinstance(data,dict): raise ValueError('Campaign configuration must be an object')
    name=str(data.get('name') or '').strip()
    if not name or len(name)>MAX_NAME: raise ValueError('Campaign name must be 1–255 characters')
    description=str(data.get('description') or '').strip()
    if len(description)>2000: raise ValueError('Campaign description must not exceed 2000 characters')
    primary=_keywords(data.get('primary_keywords',[]),'Main keywords',True)
    secondary=_keywords(data.get('secondary_keywords',[]),'Secondary keywords')
    excluded=_keywords(data.get('excluded_keywords',[]),'Excluded keywords')
    overlap={x.casefold() for x in primary}&{x.casefold() for x in excluded}
    if overlap: raise ValueError('Main keywords cannot also be excluded')
    platforms=data.get('platforms',[])
    if not isinstance(platforms,list) or not platforms: raise ValueError('Select at least one platform')
    if len(platforms)>len(AVAILABLE_PLATFORMS): raise ValueError('Too many platforms')
    platforms=list(dict.fromkeys(platforms))
    if any(not isinstance(x,str) or x not in AVAILABLE_PLATFORMS for x in platforms):
        raise ValueError('Invalid Social Listening platform')
    language=data.get('language','') or ''
    if language not in ('','id','en','ms'): raise ValueError('Unsupported language')
    start=_iso_date(data.get('date_from'),'Start date')
    end=_iso_date(data.get('date_to'),'End date')
    if start and end and start>end: raise ValueError('Start date must be before end date')
    interval=data.get('interval_minutes',180)
    if type(interval) is not int or not 60<=interval<=10080:
        raise ValueError('Monitoring interval must be 60–10080 minutes')
    # Reuse established regional scope validation before persisting.
    filters=_scope_filters(p,{'query':' '.join(primary),'platforms':platforms,
       'province':data.get('province') or '', 'regency_city':data.get('regency_city') or ''})
    return {'name':name,'description':description,
       'primary_keywords_json':json.dumps(primary,ensure_ascii=False),
       'secondary_keywords_json':json.dumps(secondary,ensure_ascii=False),
       'excluded_keywords_json':json.dumps(excluded,ensure_ascii=False),
       'platforms_json':json.dumps(platforms),
       'language':language,'date_from':start,'date_to':end,
       'province':filters.get('province',''),'regency_city':filters.get('regency_city',''),
       'interval_minutes':interval}

def _view(db,c):
    counts=db.query(CampaignRun).filter(CampaignRun.campaign_id==c.id).count()
    evidence=db.query(CampaignEvidence).filter(CampaignEvidence.campaign_id==c.id).count()
    return {'id':str(c.id),'name':c.name,'description':c.description,
       'primary_keywords':json.loads(c.primary_keywords_json or '[]'),
       'secondary_keywords':json.loads(c.secondary_keywords_json or '[]'),
       'excluded_keywords':json.loads(c.excluded_keywords_json or '[]'),
       'platforms':json.loads(c.platforms_json or '[]'),'language':c.language,
       'date_from':c.date_from,'date_to':c.date_to,
       'province':c.province,'regency_city':c.regency_city,
       'interval_minutes':c.interval_minutes,'status':c.status,
       'created_by':c.created_by,
       'next_run_at':c.next_run_at.isoformat() if c.next_run_at else None,
       'last_success_at':c.last_success_at.isoformat() if c.last_success_at else None,
       'run_count':counts,'evidence_count':evidence,
       'created_at':c.created_at.isoformat() if c.created_at else None}

def _editable(p,c):
    if p.get('role')=='National Administrator' and has(p,'administration'): return True
    return c.created_by==p.get('id') and has(p,'add_intelligence')

def campaign_action(db:Session,p,action,data,id=None):
    if not has(p,'view_intelligence'): raise PermissionError('No intelligence access')
    if action=='campaignKeywordPreview':
        from .campaign_scheduler import keyword_screen
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if not isinstance(data,dict) or not isinstance(data.get('text'),str):
            raise ValueError('Enter text for the keyword preview')
        sample=data['text'].strip()
        if len(sample)>5000: raise ValueError('Keyword preview is limited to 5000 characters')
        result=keyword_screen(c,{'text_content':sample})
        return {'screening':result,'paid_provider_called':False,
                'notice':'Local matching preview only; provider-side OR retrieval has not been verified'}
    if action=='campaignCostPreview':
        from .socialcrawl import estimate_search_cost
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted')
        values=_normalize(db,p,data)
        filters={'query':' '.join(json.loads(values['primary_keywords_json'])),
                 'exclude_terms':json.loads(values['excluded_keywords_json']),
                 'platforms':json.loads(values['platforms_json']),
                 'language':values['language'],
                 'date_from':values['date_from'],'date_to':values['date_to'],
                 'province':values['province'],'regency_city':values['regency_city']}
        estimate=estimate_search_cost(filters)
        return {'estimated_credits':estimate['estimated_credits'],
                'components':estimate['components'],
                'billing_warning':'Estimate only. Actual provider credits may vary.',
                'paid_run_enabled':False,'approval_required':True}
    if action=='listCampaigns':
        rows=db.query(MonitoringCampaign).order_by(MonitoringCampaign.created_at.desc(),MonitoringCampaign.id.desc()).all()
        visible=[r for r in rows if allowed(p,r)]
        return {'campaigns':[_view(db,r) for r in visible[:MAX_CAMPAIGNS_PER_LIST]],'total':len(visible),
                'automatic_paid_crawling_enabled':False}
    if action in ('campaignSchedulePreview','campaignHistory'):
        from .campaign_scheduler import campaign_schedule_preview, campaign_history
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if action=='campaignSchedulePreview':
            return {'schedule':campaign_schedule_preview(db,c)}
        return {'history':campaign_history(db,c)}
    if action=='getCampaign':
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        return {'campaign':_view(db,c)}
    if action=='createCampaign':
        if not has(p,'add_intelligence'): raise PermissionError('Not permitted to create campaigns')
        values=_normalize(db,p,data)
        c=MonitoringCampaign(**values,status='DRAFT',created_by=p['id'])
        db.add(c);db.commit();db.refresh(c)
        audit(db,p,'MonitoringCampaign',c.id,'CAMPAIGN_CREATED',{'name':{'new':c.name},'status':{'new':'DRAFT'}})
        return {'campaign':_view(db,c),'message':'Campaign saved in draft; scheduled paid crawling is not enabled'}
    if action=='updateCampaign':
        c=db.get(MonitoringCampaign,int(id)) if str(id or '').isdigit() else None
        if not c or not allowed(p,c): raise ValueError('Campaign not available')
        if not _editable(p,c): raise PermissionError('Only campaign owner or national administrator can edit')
        if c.status not in ('DRAFT','PAUSED'): raise ValueError('Campaign cannot be edited in its current state')
        values=_normalize(db,p,{**_view(db,c),**(data or {})})
        for k,v in values.items(): setattr(c,k,v)
        # PAUSED is a configuration state, not a scheduler activation.
        desired=(data or {}).get('status',c.status)
        if desired not in ('DRAFT','PAUSED'): raise ValueError('Scheduled campaign activation is not yet available')
        previous_status=c.status;c.status=desired;c.updated_at=datetime.now(timezone.utc).replace(tzinfo=None)
        db.commit()
        audit(db,p,'MonitoringCampaign',c.id,'CAMPAIGN_UPDATED',{'status':{'old':previous_status,'new':c.status}})
        return {'campaign':_view(db,c)}
    raise ValueError('Unsupported campaign action')
