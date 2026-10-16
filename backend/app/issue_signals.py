"""Deterministic, credit-free validation of preliminary election issue signals.

Category phrases provide model context, not proof of a violation.
"""
def active_issue_taxonomy(categories, phrases):
    """Only active category IDs and active associated phrases reach the model."""
    active={c.id:c for c in categories if c.active}
    return [{'id':c.id,'name':c.name,'phrases':[p.phrase for p in phrases
             if p.active and p.category_id==c.id][:12]}
            for c in categories if c.id in active]

def validated_issue_signals(raw_signals, active_categories, source_text):
    """Reject unknown categories, unsupported quotes, and non-provisional signals."""
    result=[]
    if not isinstance(raw_signals,list):return result
    content=str(source_text or '').casefold()
    for signal in raw_signals[:8]:
        if not isinstance(signal,dict):continue
        cid=signal.get('category_id')
        if type(cid) is not int or cid not in active_categories:continue
        if signal.get('signal_type')!='POTENTIAL_VIOLATION':continue
        quote=str(signal.get('evidence_quote') or '').strip()
        if len(quote)<12 or quote.casefold() not in content:continue
        result.append({'category_id':cid,'category_name':active_categories[cid],
                       'explanation':str(signal.get('explanation') or '')[:400],
                       'evidence_quote':quote[:350]})
    return result

def rejected_issue_signal_reasons(raw_signals, active_categories, source_text):
    """Return aggregated rejection reasons without changing the original AI records."""
    reasons={'invalid_category':0,'invalid_signal_type':0,'missing_or_short_quote':0,'quote_not_in_source':0,'malformed_signal':0}
    if not isinstance(raw_signals,list):return reasons
    source=str(source_text or '').casefold()
    for signal in raw_signals:
        if not isinstance(signal,dict):
            reasons['malformed_signal']+=1;continue
        cid=signal.get('category_id')
        quote=str(signal.get('evidence_quote') or '').strip()
        if type(cid) is not int or cid not in active_categories:reasons['invalid_category']+=1
        elif signal.get('signal_type')!='POTENTIAL_VIOLATION':reasons['invalid_signal_type']+=1
        elif len(quote)<12:reasons['missing_or_short_quote']+=1
        elif quote.casefold() not in source:reasons['quote_not_in_source']+=1
    return reasons

def rejected_issue_type_summary(raw_signals, active_categories, source_text):
    """Count actual rejected type values without exposing original post content."""
    summary={}
    if not isinstance(raw_signals,list):return summary
    content=str(source_text or '').casefold()
    for signal in raw_signals:
        if not isinstance(signal,dict):continue
        cid=signal.get('category_id')
        if type(cid) is not int or cid not in active_categories:continue
        kind=signal.get('signal_type')
        if kind=='POTENTIAL_VIOLATION':continue
        quote=str(signal.get('evidence_quote') or '').strip()
        # Do not imply a safe migration: an invalid type remains rejected.
        key='(missing)' if kind is None or kind=='' else str(kind).strip()[:60]
        if not key:key='(blank)'
        key=key.replace('<','').replace('>','')
        summary[key]=summary.get(key,0)+1
    return summary
