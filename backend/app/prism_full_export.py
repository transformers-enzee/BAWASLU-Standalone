"""Read already-paid result pages, committing only verified cursors."""
import json
import os
from datetime import datetime,timezone
from urllib.parse import urlencode
import httpx

def read_export_page(url,cursor,safe_url):
    key=os.getenv('SOCIALCRAWL_API_KEY','').strip()
    q=url+('?'+urlencode({'cursor':cursor}) if cursor else '')
    with httpx.Client(timeout=65,follow_redirects=False) as client:
        response=client.get(safe_url(q),headers={'x-api-key':key})
    response.raise_for_status()
    items=[];next_cursor=None;complete=False
    for line in response.text.splitlines():
        if not line.strip():continue
        obj=json.loads(line)
        if not isinstance(obj,dict):raise ValueError('Invalid provider export row')
        if 'next_cursor' in obj:next_cursor=str(obj['next_cursor'] or '') or None
        elif 'complete' in obj:complete=obj['complete'] is True
        else:items.append(obj)
    if not complete and not next_cursor:raise ValueError('Provider export did not return a completion marker or cursor')
    return items,next_cursor,complete

def ingest_full_export(db,c,run,meta,data,nxt,status,checkpoint,store,safe_url):
    cursor=meta.get('full_export_cursor')
    seen=set()
    def persist(items,next_cursor,complete):
        nonlocal run,meta
        run,meta=checkpoint(status,status.get('run_id'),persist=False)
        for offset in range(0,len(items),100):
            run.result_count=store(db,run,c,items[offset:offset+100],full_assessment=True,commit=False)
            db.flush()
        meta=json.loads(run.query_json or '{}')
        diag=meta.get('collection_diagnostics') or {}
        kept=(meta.get('provider_diagnostics') or {}).get('kept')
        scanned=int(diag.get('raw_provider_items') or 0)
        if complete and type(kept) is int and kept>scanned:
            raise ValueError('Provider reports additional retained rows; export completeness cannot be verified')
        requested=(meta.get('body') or {}).get('limit')
        meta['provider_limit_reached']=bool(type(requested) is int and requested>0 and
            (scanned>=requested or (type(kept) is int and kept>=requested)))
        meta['full_export_cursor']=next_cursor
        meta['full_export_complete']=complete
        meta['export_incomplete']=not complete
        meta['submission_uncertain']=False
        meta['watermark']=None
        if complete:
            run.status='COMPLETED' if status.get('status')=='completed' else 'PARTIAL'
            if run.status=='COMPLETED':
                if not meta.get('provider_limit_reached'):
                    meta['watermark']=nxt.get('watermark')
                c.last_success_at=datetime.now(timezone.utc).replace(tzinfo=None)
        run.query_json=json.dumps(meta,ensure_ascii=False)
        db.commit()
    if meta.get('full_export_complete'):
        persist([],None,True);return
    results_url=nxt.get('results_url')
    if not results_url:
        items=list(data.get('items') or [])
        kept=(meta.get('provider_diagnostics') or {}).get('kept')
        if (data.get('pagination') or {}).get('next_cursor') or type(kept) is not int or kept>len(items):
            raise ValueError('Provider export completeness cannot be verified; recover stored run')
        persist(items,None,True);return
    url=str(results_url).rstrip('/')+'/results.jsonl'
    while True:
        if cursor in seen:raise ValueError('Provider export cursor repeated; recover after review')
        seen.add(cursor)
        items,next_cursor,complete=read_export_page(url,cursor,safe_url)
        if next_cursor and next_cursor in seen:raise ValueError('Provider export cursor repeated; recover after review')
        persist(items,next_cursor,complete)
        if complete:return
        cursor=next_cursor
