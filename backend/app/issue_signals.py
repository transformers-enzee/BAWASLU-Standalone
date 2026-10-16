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
