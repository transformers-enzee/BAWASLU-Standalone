"""Read-only evidence reconciliation; preserve historical and reviewed sources."""
import json
from collections import Counter
from types import SimpleNamespace
from .models import CampaignEvidence, SocialListeningResult

IMPORT_METHODS={'EXTERNAL_PROVIDER_IMPORT','HUMAN_REVIEWED_IMPORT'}
IMPORT_PROVIDERS={'ZOCIALEYE','HUMAN_VERIFIED_WORKBOOK'}


def import_match_fields(c,text,kind,run_id,snapshot=None):
    from .prism_discover import search_snapshot,snapshot_signature
    from .campaign_scheduler import keyword_screen
    snapshot=snapshot or search_snapshot(c)
    match=keyword_screen(SimpleNamespace(**snapshot),{'text_content':text})
    return {'provenance':kind,'import_policy':'AUTHORIZED_IMPORT_PRESERVE_ALL',
            'matched_at_import':match['matched'],'search_mode':match['search_mode'],
            'query_revision':snapshot_signature(snapshot),'import_run_id':run_id}


def audit_link(c,link,item,revision):
    from .campaign_scheduler import keyword_screen
    from .project_boolean import decode_project_query,boolean_term_trace
    try:fields=json.loads(link.matched_fields_json or '{}')
    except (ValueError,TypeError):fields={}
    if not isinstance(fields,dict):fields={}
    method=link.match_method or 'UNKNOWN'
    imported=method in IMPORT_METHODS or item.provider in IMPORT_PROVIDERS
    saved=fields.get('query_revision')
    # This is a current stored-text check, not a new assessment or a claim
    # about what was searchable at the time of collection.
    match=keyword_screen(c,{'text_content':item.text_content})
    current=decode_project_query(c.primary_keywords_json)
    trace=boolean_term_trace(current['ast'],item.text_content) if current['search_mode']=='BOOLEAN' else None
    return {'evidence_id':str(link.id),'result_id':str(item.id),'match_method':method,
            'provenance':'AUTHORIZED_IMPORT' if imported else 'COLLECTED_OR_LEGACY',
            'saved_revision':saved,
            'revision_status':'UNKNOWN' if not saved else 'CURRENT' if saved==revision else 'HISTORICAL',
            'matches_current_text':bool(match['matched']),
            'matching_status':'MATCH' if match['matched'] else 'NO_MATCH',
            'main_keywords':match['main_keywords'],'secondary_keywords':match['secondary_keywords'],
            'excluded_keywords':match['excluded_keywords'],'boolean_terms':trace,
            'preserved':True}


def audit_page(db,p,c,opts):
    from .prism_discover import search_snapshot,snapshot_signature
    from .socialcrawl import _result_in_scope
    try:
        limit=int(opts.get('page_size') or 100)
        cursor=int(opts.get('cursor') or 0)
    except (TypeError,ValueError):raise ValueError('Invalid search audit pagination')
    if not 1<=limit<=200 or cursor<0:raise ValueError('Search audit page size must be 1-200')
    revision=snapshot_signature(search_snapshot(c))
    expected=opts.get('query_revision')
    if expected and expected!=revision:raise ValueError('Search configuration changed; restart the audit')
    q=(db.query(CampaignEvidence,SocialListeningResult)
       .join(SocialListeningResult,CampaignEvidence.result_id==SocialListeningResult.id)
       .filter(CampaignEvidence.campaign_id==c.id,CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'))
    if cursor:q=q.filter(CampaignEvidence.id>cursor)
    batch=q.order_by(CampaignEvidence.id.asc()).limit(limit+1).all()
    page=batch[:limit]
    rows=[audit_link(c,link,item,revision) for link,item in page if _result_in_scope(db,p,item)]
    counts=Counter(row['matching_status'] for row in rows)
    versions=Counter(row['revision_status'] for row in rows)
    return {'query_revision':revision,'rows':rows,'page_visible':len(rows),
            'page_counts':{'matching':counts['MATCH'],'not_matching':counts['NO_MATCH'],
                'imports':sum(row['provenance']=='AUTHORIZED_IMPORT' for row in rows),
                'historical_revision':versions['HISTORICAL'],'unknown_revision':versions['UNKNOWN']},
            'has_more':len(batch)>limit,'next_cursor':str(page[-1][0].id) if len(batch)>limit and page else None,
            'paid_provider_called':False,'writes':0,'scope':'CURRENT_SAVED_TEXT_ONLY'}


def aggregate_audit(db,p,c,opts):
    """Whole authorized project reconciliation; explicitly requested, no writes.

    Match the latest-version Inbox relevance contract while keeping collection
    matching and AI relevance independent. Count links, not cross-project sums.
    """
    from sqlalchemy import func
    from .models import EvidenceAssessment
    from .socialcrawl import _result_in_scope
    from .prism_discover import search_snapshot,snapshot_signature
    from .campaign_scheduler import keyword_screen
    from .collection_date_scope import publication_in_window
    from .officer_sentiment import OfficerSentimentCorrection
    revision=snapshot_signature(search_snapshot(c))
    start=str(opts.get('date_from') or '');end=str(opts.get('date_to') or '')
    from datetime import date
    for value in (start,end):
        if value and (len(value)!=10 or date.fromisoformat(value).isoformat()!=value):raise ValueError('Invalid reconciliation date')
    if start and end and start>end:raise ValueError('Start date must not follow end date')
    latest_id=(db.query(EvidenceAssessment.id).filter(
        EvidenceAssessment.campaign_id==CampaignEvidence.campaign_id,
        EvidenceAssessment.result_id==CampaignEvidence.result_id)
        .order_by(EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc())
        .limit(1).correlate(CampaignEvidence).scalar_subquery())
    latest_tone=(db.query(OfficerSentimentCorrection.sentiment).filter(
        OfficerSentimentCorrection.campaign_id==CampaignEvidence.campaign_id,
        OfficerSentimentCorrection.result_id==CampaignEvidence.result_id)
        .order_by(OfficerSentimentCorrection.id.desc()).limit(1).correlate(CampaignEvidence).scalar_subquery())
    q=(db.query(SocialListeningResult.run_id,SocialListeningResult.text_content,
        SocialListeningResult.published_at,CampaignEvidence.match_method,CampaignEvidence.matched_fields_json,
        EvidenceAssessment.relevance_label,EvidenceAssessment.model_version,
        func.coalesce(latest_tone,EvidenceAssessment.sentiment))
        .select_from(SocialListeningResult)
        .join(CampaignEvidence,CampaignEvidence.result_id==SocialListeningResult.id)
        .outerjoin(EvidenceAssessment,EvidenceAssessment.id==latest_id)
        .filter(CampaignEvidence.campaign_id==c.id,CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'))
    day=func.substr(SocialListeningResult.published_at,1,10)
    if start:q=q.filter(day>=start)
    if end:q=q.filter(day<=end)
    counts=Counter();sentiment=Counter();scope={}
    for rid,text,stamp,method,fields,label,model,tone in q.yield_per(500):
        if rid not in scope:scope[rid]=_result_in_scope(db,p,SimpleNamespace(run_id=rid))
        if not scope[rid] or not publication_in_window(stamp,start,end):continue
        counts['captured']+=1
        counts['matching_current_search' if keyword_screen(c,{'text_content':text})['matched'] else 'not_matching_current_search']+=1
        if method in IMPORT_METHODS:counts['authorized_imports']+=1
        try:meta=json.loads(fields or '{}')
        except (ValueError,TypeError):meta={}
        saved=meta.get('query_revision') if isinstance(meta,dict) else None
        counts['unknown_revision' if not saved else 'current_revision' if saved==revision else 'historical_revision']+=1
        label=str(label or '').upper()
        if model=='PRISM_PENDING_OPENAI' or label not in ('RELEVANT','HIGHLY_RELEVANT','IRRELEVANT','UNCERTAIN'):
            counts['pending_relevance']+=1
        else:
            counts['assessed_relevance']+=1
            if label in ('RELEVANT','HIGHLY_RELEVANT'):
                counts['inbox_eligible']+=1
                tone=str(tone or '').upper()
                sentiment[tone if tone in ('POSITIVE','NEUTRAL','NEGATIVE') else 'UNCLASSIFIED']+=1
            else:counts['not_inbox_eligible_after_assessment']+=1
    keys=('captured','matching_current_search','not_matching_current_search','authorized_imports','unknown_revision',
          'current_revision','historical_revision','pending_relevance','assessed_relevance','inbox_eligible','not_inbox_eligible_after_assessment')
    return {'query_revision':revision,'counts':{key:counts[key] for key in keys},
            'inbox_eligible_sentiment':{key:sentiment[key] for key in ('POSITIVE','NEUTRAL','NEGATIVE','UNCLASSIFIED')},
            'date_from':start,'date_to':end,'scope':'AUTHORIZED_PROJECT_LINKS',
            'count_integrity':counts['captured']==counts['matching_current_search']+counts['not_matching_current_search']==counts['pending_relevance']+counts['assessed_relevance'] and counts['assessed_relevance']==counts['inbox_eligible']+counts['not_inbox_eligible_after_assessment'] and sum(sentiment.values())==counts['inbox_eligible'],
            'historical_evidence_preserved':True,'paid_provider_called':False,'writes':0}
