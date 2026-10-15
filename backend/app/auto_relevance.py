"""Bounded, post-collection AI contextual screening. No SocialCrawl requests."""
import json
import os
import logging
import httpx
from .db import SessionLocal
from .models import MonitoringCampaign, CampaignEvidence, SocialListeningResult, EvidenceAssessment, IssueCategory, IssueCategoryPhrase

log=logging.getLogger(__name__)
def _arr(value):
    try:
        x=json.loads(value or '[]')
        return x if isinstance(x,list) else []
    except (TypeError,ValueError): return []

def assess_pending_campaign(campaign_id):
    """Background task; each newly collected run processes at most configured AI requests."""
    if not os.getenv('OPENAI_API_KEY','').strip():
        log.info('AI screening skipped: OPENAI_API_KEY missing')
        return
    try: limit=max(0,min(25,int(os.getenv('BAWASLU_AI_ASSESSMENTS_PER_RUN','12'))))
    except ValueError: limit=12
    if not limit:return
    db=SessionLocal()
    try:
        campaign=db.get(MonitoringCampaign,int(campaign_id))
        if not campaign:return
        categories=db.query(IssueCategory).filter(IssueCategory.active==True).order_by(IssueCategory.sort_order).limit(50).all()
        category_names={c.id:c.name for c in categories}
        phrases=db.query(IssueCategoryPhrase).filter(IssueCategoryPhrase.active==True,IssueCategoryPhrase.category_id.in_(list(category_names))).limit(400).all() if category_names else []
        taxonomy=[{'id':c.id,'name':c.name,'phrases':[p.phrase for p in phrases if p.category_id==c.id][:12]} for c in categories]
        links=db.query(CampaignEvidence).filter(CampaignEvidence.campaign_id==campaign.id).order_by(CampaignEvidence.id.desc()).limit(300).all()
        used=0
        for link in links:
            if used>=limit: break
            exists=db.query(EvidenceAssessment.id).filter_by(campaign_id=campaign.id,result_id=link.result_id).first()
            if exists:continue
            item=db.get(SocialListeningResult,link.result_id)
            if not item:continue
            used+=1
            payload={'campaign':{'name':campaign.name,'objective':campaign.description,'main_keywords':_arr(campaign.primary_keywords_json),'secondary_keywords':_arr(campaign.secondary_keywords_json),'excluded_keywords':_arr(campaign.excluded_keywords_json)},'source':{'text':(item.text_content or '')[:5000],'platform':item.platform,'author':item.author_name},'active_issue_categories':taxonomy}
            try:
                model=os.getenv('BAWASLU_RELEVANCE_MODEL','gpt-4o-mini')
                url=os.getenv('OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')+'/chat/completions'
                response=httpx.post(url,headers={'Authorization':'Bearer '+os.environ['OPENAI_API_KEY']},
                    json={'model':model,'temperature':0,'max_tokens':550,'response_format':{'type':'json_object'},
                    'messages':[{'role':'system','content':'You are a neutral election monitoring evidence screener. Respond with only JSON object containing relevance_label (RELEVANT, IRRELEVANT, UNCERTAIN), confidence (LOW, MEDIUM, HIGH), explanation, locations (array of short strings), candidates (array of short strings), issue_category_ids (array of integer IDs). Assess the topic context, not keyword occurrence alone. Never declare a violation or infer guilt; issue category flags are preliminary and must be supported by explicit text. Do not invent locations or names.'},
                    {'role':'user','content':json.dumps(payload,ensure_ascii=False)}]},timeout=30)
                response.raise_for_status()
                out=json.loads(response.json()['choices'][0]['message']['content'])
                label=str(out.get('relevance_label','UNCERTAIN')).upper()
                if label not in ('RELEVANT','IRRELEVANT','UNCERTAIN'):label='UNCERTAIN'
                confidence=str(out.get('confidence','LOW')).upper()
                if confidence not in ('LOW','MEDIUM','HIGH'):confidence='LOW'
                def strings(key):
                    v=out.get(key)
                    return [str(x)[:160] for x in v[:12] if isinstance(x,str)] if isinstance(v,list) else []
                issue_ids=out.get('issue_category_ids',[])
                issue_ids=[x for x in issue_ids if type(x) is int and x in category_names] if isinstance(issue_ids,list) else []
                record=EvidenceAssessment(campaign_id=campaign.id,result_id=item.id,assessment_version=1,
                    model_version=model,relevance_label=label,relevance_confidence=confidence,
                    explanation=str(out.get('explanation') or '')[:1200],candidate_signals_json=json.dumps(strings('candidates')),
                    geographic_signals_json=json.dumps(strings('locations')),
                    potential_issue_signals_json=json.dumps([{'category_id':x,'explanation':'AI-suggested category; requires human review'} for x in issue_ids]))
                db.add(record);db.commit()
            except (httpx.HTTPError,KeyError,ValueError,TypeError,IndexError) as exc:
                db.rollback()
                log.warning('AI screening stopped after request error: %s',type(exc).__name__)
                break
    finally:
        db.close()
