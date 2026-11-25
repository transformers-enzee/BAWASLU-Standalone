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
