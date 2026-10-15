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

def assess_pending_campaign(campaign_id, requested_limit=None):
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
                db.add(record);db.commit()
            except (httpx.HTTPError,KeyError,ValueError,TypeError,IndexError) as exc:
                db.rollback()
                log.warning('AI screening stopped after request error: %s',type(exc).__name__)
                break
    finally:
        db.close()
