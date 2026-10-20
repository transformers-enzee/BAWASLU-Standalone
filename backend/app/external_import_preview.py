"""Preview external ZocialEye exports without importing any records."""
import csv
from pathlib import Path

MAPPING={'text_content':('Message',),'canonical_url':('Direct URL','Post URL','Video URL','Topic URL'),
         'author_name':('Account',),'platform':('Source',),'published_at':('Post time',),
         'engagement':('Engagement',),'sentiment':('Sentiment',),'provider_result_id':('_id',),
         'content_type':('Type',),'main_keyword':('Main keyword',),'secondary_keyword':('Sub keyword',)}
def map_fields(headers):
    existing={str(h or '').strip().casefold():str(h).strip() for h in headers if h}
    return {key:next((existing[alias.casefold()] for alias in aliases if alias.casefold() in existing),None) for key,aliases in MAPPING.items()}
def preview_workbook(path):
    path=Path(path)
    if path.suffix.lower()=='.xlsx':
        from openpyxl import load_workbook
        book=load_workbook(path,read_only=True,data_only=True)
        sheets=[]
        for sheet in book:
            headers=[str(v or '').strip() for v in next(sheet.iter_rows(min_row=1,max_row=1,values_only=True),())]
            sheets.append({'name':sheet.title,'data_rows':max(0,(sheet.max_row or 1)-1),'columns':headers})
        names={s['name'] for s in sheets}
        recommended='all' if 'all' in names else next((s['name'] for s in sheets if s['data_rows'] and 'Message' in s['columns']),None)
        if not recommended:raise ValueError('No usable message sheet found')
        ws=book[recommended]
        rows=ws.iter_rows(min_row=2,max_row=min(ws.max_row or 1,26),values_only=True)
        mapping=map_fields(next(s['columns'] for s in sheets if s['name']==recommended))
        keys=next(s['columns'] for s in sheets if s['name']==recommended)
        sampled=list(rows)
        book.close()
    elif path.suffix.lower()=='.csv':
        with path.open('r',encoding='utf-8-sig',newline='') as handle:
            reader=csv.DictReader(handle)
            keys=reader.fieldnames or []
            sampled=[tuple(row.get(key) for key in keys) for _,row in zip(range(25),reader)]
        sheets=[{'name':'CSV','data_rows':sum(1 for _ in path.open('r',encoding='utf-8-sig'))-1,'columns':keys}]
        recommended='CSV';mapping=map_fields(keys)
    else:raise ValueError('Unsupported file type')
    def empty(idx,value):
        return not str(value[idx] if idx<len(value) else '').strip() if idx>=0 else True
    url_key=mapping.get('canonical_url');text_key=mapping.get('text_content')
    ui=keys.index(url_key) if url_key in keys else -1
    ti=keys.index(text_key) if text_key in keys else -1
    return {'sheets':sheets,'recommended_sheet':recommended,
        'estimated_rows_in_recommended_sheet':next(s['data_rows'] for s in sheets if s['name']==recommended),
        'mapped_fields':{k:v for k,v in mapping.items() if v},
        'sampled_rows':len(sampled),'sample_missing_url':sum(empty(ui,row) for row in sampled),
        'sample_missing_text':sum(empty(ti,row) for row in sampled),
        'warning':('Combined all sheet overlaps with platform-specific sheets: importing both would duplicate records. '
                   'Post and comment rows must be preserved separately using source IDs and parent links.') if recommended=='all'
                  else 'Check row types, source URLs, and IDs before enabling import.'}

def validate_all_rows(path, existing_urls=None):
    """Read only the selected combined sheet; counts are informational, not legal findings."""
    from collections import Counter
    from datetime import datetime
    from urllib.parse import urlparse
    existing_urls=set(existing_urls or ())
    path=Path(path)
    if path.suffix.lower()=='.xlsx':
        from openpyxl import load_workbook
        book=load_workbook(path,read_only=True,data_only=True)
        sheet=book['all'] if 'all' in book.sheetnames else next((s for s in book if s.max_row>1 and 'Message' in [str(c or '') for c in next(s.iter_rows(max_row=1,values_only=True))]),None)
        if sheet is None:raise ValueError('No usable message sheet')
        records=sheet.iter_rows(values_only=True)
    else:
        book=None
        handle=path.open('r',encoding='utf-8-sig',newline='')
        records=(tuple(row) for row in csv.reader(handle))
    try:
        headers=[str(v or '').strip() for v in next(records)]
        index={name:i for i,name in enumerate(headers)}
        def field(row,name):
            i=index.get(name,-1)
            return str(row[i] if 0<=i<len(row) and row[i] is not None else '').strip()
        counts=Counter()
        platforms=Counter()
        seen_ids=set()
        seen_urls=set()
        samples=[]
        for row in records:
            if not any(v not in (None,'') for v in row):continue
            counts['total_rows']+=1
            content=field(row,'Message')
            url=field(row,'Direct URL') or field(row,'Comment URL') or field(row,'Reply comment URL') or field(row,'Post URL')
            provider_id=field(row,'_id')
            source=field(row,'Source').casefold() or 'unknown'
            platforms[source]+=1
            if not content:counts['missing_content']+=1
            if not url:counts['missing_url']+=1
            elif urlparse(url).scheme not in ('http','https') or not urlparse(url).netloc:counts['invalid_url']+=1
            if not field(row,'Post time'):counts['missing_date']+=1
            kind='comment' if field(row,'Comment URL') or field(row,'Reply comment URL') else 'post_or_unknown'
            counts[kind]+=1
            if kind=='comment' and not field(row,'Post URL'):counts['comment_missing_parent_url']+=1
            if not provider_id:counts['missing_provider_id']+=1
            identity=(source,provider_id) if provider_id else None
            if identity:
                if identity in seen_ids:counts['duplicate_provider_ids']+=1
                else:seen_ids.add(identity)
            if url:
                if url in seen_urls:counts['repeated_urls']+=1
                else:seen_urls.add(url)
                if url in existing_urls:counts['url_matches_existing_database']+=1
            if len(samples)<5 and (not content or not url):
                samples.append({'row':counts['total_rows']+1,'issue':'missing content' if not content else 'missing URL'})
        return {'validation':dict(counts),'platform_distribution':dict(platforms),
                'sample_issues':samples,
                'validation_scope':'All non-empty data rows on the selected sheet only; no database writes',
                'duplicate_note':'Repeated URLs may represent distinct comments; do not automatically discard them.',
                'import_enabled':False}
    finally:
        if book:book.close()
        else:handle.close()
