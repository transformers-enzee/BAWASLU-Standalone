"""Read-only server-side saved-post filtering with bounded response pages."""
import heapq
import json
from datetime import date
from types import SimpleNamespace
from sqlalchemy import case, func, or_, and_, literal
from .models import CampaignEvidence,SocialListeningResult,EvidenceAssessment
from .project_boolean import parse_boolean,evaluate_boolean
from .saved_post_facets import parse_filters,metadata,matches,accumulate,facet_payload,new_counters
from itertools import islice

def _batches(rows,size):
    rows=iter(rows)
    while True:
        batch=list(islice(rows,size))
        if not batch:return
        yield batch

def search_page(db,p,c,q,opts,page_size):
    from .socialcrawl import _result_in_scope
    from .officer_sentiment import OfficerSentimentCorrection
    from .campaigns import _captured_post_metrics
    from sqlalchemy import select
    spec=opts.get('search')
    if not isinstance(spec,dict):raise ValueError('Invalid saved post search')
    mode=spec.get('mode','standard');sort=spec.get('sort','newest')
    if mode not in ('standard','boolean') or sort not in ('newest','oldest','engagement'):
        raise ValueError('Invalid saved post search mode or sort')
    text=str(spec.get('query') or '').strip()
    if len(text)>512:raise ValueError('Search query exceeds 512 characters')
    tree=parse_boolean(text,require_positive=False)[0] if text and mode=='boolean' else None
    filters=parse_filters(spec)
    platforms_selected=filters['platform']
    sentiments=[x.lower() for x in filters['sentiment']]
    if any(x not in ('positive','negative','neutral','unclassified') for x in sentiments):raise ValueError('Invalid sentiment')
    include_facets=opts.get('include_facets') is True
    advanced=any((bool(v) if isinstance(v,list) else True) for k,v in filters.items() if k not in ('platform','sentiment'))
    rich=advanced or include_facets
    start=str(spec.get('from') or '');end=str(spec.get('to') or '')
    for val in (start,end):
        if val and (len(val)!=10 or date.fromisoformat(val).isoformat()!=val):raise ValueError('Invalid search date')
    if start and end and start>end:raise ValueError('Start date must not follow end date')
    cursor=None
    if opts.get('cursor'):
        try:
            value=json.loads(opts['cursor'])
            if not isinstance(value,list) or len(value)!=2 or type(value[1]) is not int or value[1]<1:raise ValueError()
            if sort=='engagement':
                if type(value[0]) is not int or value[0]<0:raise ValueError()
            elif not isinstance(value[0],str) or len(value[0])>64:raise ValueError()
            cursor=tuple(value)
        except (ValueError,TypeError):raise ValueError('Invalid saved post cursor')
    nationwide=p.get('geographic_scope')=='Nationwide'
    scope={}
    def visible(run_id):
        if nationwide:return True
        if run_id not in scope:scope[run_id]=_result_in_scope(db,p,SimpleNamespace(run_id=run_id))
        return scope[run_id]
    # Only authorized source facets, independent of active filters.
    base=q.order_by(None)
    if nationwide:
        platforms=sorted(x[0] for x in base.with_entities(SocialListeningResult.platform).distinct().all() if x[0])
    else:
        platforms=sorted({plat for plat,rid in base.with_entities(SocialListeningResult.platform,SocialListeningResult.run_id).distinct().yield_per(200) if plat and visible(rid)})
    if platforms_selected:base=base.filter(SocialListeningResult.platform.in_(platforms_selected))
    day=func.substr(SocialListeningResult.published_at,1,10)
    if start:base=base.filter(day>=start)
    if end:base=base.filter(day!='',day<=end)
    if sentiments or rich:
        # Mirror the latest saved sentiment version and officer overrides.
        a=EvidenceAssessment;correction=OfficerSentimentCorrection
        assessed=select(a.sentiment).where(a.campaign_id==c.id,a.result_id==SocialListeningResult.id).order_by(
            a.assessment_version.desc(),a.id.desc()).limit(1).correlate(SocialListeningResult).scalar_subquery()
        officer=select(correction.sentiment).where(correction.campaign_id==c.id,correction.result_id==SocialListeningResult.id).order_by(
            correction.id.desc()).limit(1).correlate(SocialListeningResult).scalar_subquery()
        label=func.upper(func.coalesce(officer,assessed,'UNCLASSIFIED'))
        if sentiments:
            choices=[label==v.upper() for v in sentiments if v!='unclassified']
            if 'unclassified' in sentiments:choices.append(label.notin_(['POSITIVE','NEGATIVE','NEUTRAL']))
            base=base.filter(or_(*choices))
    stamp=func.coalesce(SocialListeningResult.published_at,'')
    # SQL fast path for nationwide date-ordered browsing without text matching.
    # For exact Boolean/Unicode text evaluation, stream only required columns;
    # keep at most one response page in memory, never hydrate the whole corpus.
    descending=sort!='oldest'
    counters=new_counters() if include_facets else None
    if nationwide and not text and sort!='engagement' and not rich:
        total=base.count()
        subset=base
        if cursor:
            op=stamp<cursor[0] if descending else stamp>cursor[0]
            tie=CampaignEvidence.id<cursor[1] if descending else CampaignEvidence.id>cursor[1]
            subset=subset.filter(or_(op,and_(stamp==cursor[0],tie)))
        order=[stamp.desc(),CampaignEvidence.id.desc()] if descending else [stamp.asc(),CampaignEvidence.id.asc()]
        rows=subset.with_entities(CampaignEvidence.id,stamp).order_by(*order).limit(page_size+1).all()
        ranked=[(str(ts or ''),eid) for eid,ts in rows]
    else:
        total=0
        post=SocialListeningResult
        fields=[CampaignEvidence.id,post.run_id,stamp,post.text_content if (text or rich) else literal(''),
                post.engagement_json if (sort=='engagement' or rich) else literal(''),
                post.author_name,post.observed_handle,post.canonical_url,post.id]
        if rich:
            from .models import AIAssessmentJob
            a=EvidenceAssessment
            latest=select(a.id).where(a.campaign_id==c.id,a.result_id==post.id).order_by(
                case((func.upper(func.coalesce(a.model_version,'')).in_(['PRISM_PENDING_OPENAI','PRISM_OPENAI_TOPIC_CLASSIFIER']),1),else_=0).asc(),
                a.assessment_version.desc(),a.id.desc()).limit(1).correlate(post).scalar_subquery()
            base=base.outerjoin(a,a.id==latest).outerjoin(AIAssessmentJob,and_(
                AIAssessmentJob.campaign_id==c.id,AIAssessmentJob.result_id==post.id))
            fields += [post.platform,post.content_type,post.language,a.model_version,a.relevance_label,
                       a.topic_labels_json,a.candidate_signals_json,a.geographic_signals_json,a.potential_issue_signals_json,
                       a.public_concern_signals_json,AIAssessmentJob.state,officer,assessed]
        geography=bool(include_facets or filters['province'] or filters['regency'] or filters['location_confidence'])
        def eligible():
            nonlocal total
            for batch in _batches(base.with_entities(*fields).yield_per(200),200):
                authorized=[row for row in batch if visible(row[1])]
                reviews={}
                if rich and geography:
                    from .jurisdiction_review import jurisdiction_statuses_for_posts
                    reviews=jurisdiction_statuses_for_posts(db,[(c.id,row[8],SimpleNamespace(text_content=row[3])) for row in authorized])
                for row in authorized:
                    eid,rid,ts,content,eng,author,handle,url,result_id=row[:9]
                    if text:
                        if tree is not None:
                            if not evaluate_boolean(tree,content):continue
                        elif not (any(text.casefold() in str(v or '').casefold() for v in (content,author,handle,url)) or text==str(result_id)):continue
                    if rich:
                        plat,kind,lang,model,rel,topics,candidates,signals,issues,concerns,job,corrected,tone=row[9:]
                        meta=metadata((content,author,handle,plat,kind,lang,eng,model,rel,topics,candidates,signals,issues,concerns,job,corrected,tone),_captured_post_metrics,reviews.get((c.id,result_id)),geography)
                        if not matches(meta,filters):continue
                        if counters is not None:accumulate(counters,meta)
                    total+=1
                    key=(_captured_post_metrics(eng).get('engagement_total') or 0,eid) if sort=='engagement' else (str(ts or ''),eid)
                    if cursor and not (key<cursor if descending else key>cursor):continue
                    yield key
        ranked=(heapq.nlargest if descending else heapq.nsmallest)(page_size+1,eligible())
    has_more=len(ranked)>page_size
    ranked=ranked[:page_size]
    ids=[key[1] for key in ranked]
    by_id={link.id:(link,item) for link,item in q.filter(CampaignEvidence.id.in_(ids)).all()} if ids else {}
    links=[by_id[eid] for eid in ids if eid in by_id]
    return links,total,has_more,(json.dumps(list(ranked[-1])) if has_more and ranked else None),platforms,(facet_payload(counters) if counters is not None else None)
