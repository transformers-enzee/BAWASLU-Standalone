import re
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
        if signal.get('signal_type') not in ('POTENTIAL_VIOLATION','REPORTED_INCIDENT',None):continue
        if 'signal_type' in signal and signal['signal_type'] is None:continue
        quote=str(signal.get('evidence_quote') or '').strip()
        if len(quote)<12 or quote.casefold() not in content:continue
        result.append({'category_id':cid,'category_name':active_categories[cid],
                       'explanation':str(signal.get('explanation') or '')[:400],
                       'evidence_quote':quote[:350],
                       'signal_provenance':'LEGACY_MISSING_TYPE' if 'signal_type' not in signal else 'EXPLICIT_TYPE',
                       'requires_human_verification':True,'signal_type':signal.get('signal_type') or 'POTENTIAL_VIOLATION','time_context':signal.get('time_context','UNKNOWN'),**({'alleged_actor':str(signal.get('alleged_actor'))[:160], 'alleged_activity':str(signal.get('alleged_activity'))[:160], 'attribution_status':'SOURCE_ALLEGATION_UNVERIFIED'} if signal.get('alleged_actor') and signal.get('alleged_activity') else {})})
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
        elif signal.get('signal_type') not in ('POTENTIAL_VIOLATION','REPORTED_INCIDENT') and 'signal_type' in signal:reasons['invalid_signal_type']+=1
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
        if kind in ('POTENTIAL_VIOLATION','REPORTED_INCIDENT') or 'signal_type' not in signal:continue
        quote=str(signal.get('evidence_quote') or '').strip()
        # Do not imply a safe migration: an invalid type remains rejected.
        key='(missing)' if kind is None or kind=='' else str(kind).strip()[:60]
        if not key:key='(blank)'
        key=key.replace('<','').replace('>','')
        summary[key]=summary.get(key,0)+1
    return summary


def validated_actor_issue_signals(raw_signals, active_categories, source_text):
    """Conservative actor-specific AI triage; never establishes guilt.

    Both named alleged actor and activity must appear in the cited source excerpt.
    Legacy category-only flags are intentionally not promoted to actor findings.
    """
    confirmed=[]
    for raw in (raw_signals if isinstance(raw_signals,list) else [])[:8]:
        if not isinstance(raw,dict):continue
        actor=str(raw.get('alleged_actor') or '').strip()[:160]
        activity=str(raw.get('alleged_activity') or '').strip()[:160]
        quote=str(raw.get('evidence_quote') or '').strip()
        if not actor or not activity or len(actor)<3 or len(activity)<4:
            continue
        if actor.casefold() not in quote.casefold():
            continue
        # Require a direct, source-visible concern in the SAME cited excerpt.
        # This is a conservative screening gate, not verification of the allegation.
        allegation=re.compile(r'\b(?:alleged|allegedly|accused|bribery|bribed|violat(?:ion|ions|ed|ing)|'
                              r'misconduct|vote.buying|dugaan|diduga|dituduh|pelanggaran|'
                              r'penyuapan|suap|menyuap|politik uang|penghambatan|'
                              r'intimidasi|manipulasi|kecurangan)\b',re.IGNORECASE)
        if not allegation.search(quote):continue
        # The cited person can be the reporter, not the accused actor.
        after=quote.casefold().split(actor.casefold(),1)[1].lstrip(' ,:')
        if re.match(r'^(reports?|reported|says?|said|claims?|claimed|alleges?|'
                    r'melaporkan|mengadukan|menyatakan|mengatakan|menilai)\b',after):
            continue
        for signal in validated_issue_signals([raw],active_categories,source_text):
            confirmed.append({**signal,'alleged_actor':actor,'alleged_activity':activity,
                              'attribution_status':'SOURCE_ALLEGATION_UNVERIFIED'})
    return confirmed

def actor_signal_diagnostic(raw_signals, active_categories, source_text):
    """Counts only; no raw source, identities, quotations, or model text stored."""
    candidates=raw_signals if isinstance(raw_signals,list) else []
    reasons={}
    for raw in candidates[:8]:
        if not isinstance(raw,dict):
            reason='malformed'
        elif type(raw.get('category_id')) is not int or raw['category_id'] not in active_categories:
            reason='inactive_or_unknown_category'
        elif not str(raw.get('alleged_actor') or '').strip() or not str(raw.get('alleged_activity') or '').strip():
            reason='missing_actor_or_activity'
        elif not str(raw.get('evidence_quote') or '').strip() or str(raw['evidence_quote']).casefold() not in str(source_text or '').casefold():
            reason='quote_missing_from_source'
        elif not validated_actor_issue_signals([raw],active_categories,source_text):
            reason='actor_attribution_or_allegation_gate'
        else:
            continue
        reasons[reason]=reasons.get(reason,0)+1
    return {'candidate_count':min(len(candidates),8),'accepted_count':len(validated_actor_issue_signals(candidates,active_categories,source_text)),'rejected_reasons':reasons}


def phrase_screening_candidates(source_text, categories, phrases):
    """Unverified keyword leads for human review, not adjudicated violations.

    Only administrator-configured active phrases are used. A bare mention of a
    phrase is insufficient: require nearby allegation/reporting context. This
    does not invoke AI or modify stored assessments.
    """
    text=str(source_text or '')
    if not text.strip():
        return []
    lower=text.casefold()
    active={c.id:c.name for c in categories if c.active}
    markers=('dugaan', 'diduga', 'dilaporkan', 'melaporkan',
             'pengaduan', 'mengadukan', 'terjadi', 'indikasi',
             'alleged', 'allegation', 'reported', 'accused')
    matches=[]
    for phrase in phrases:
        if not phrase.active or phrase.category_id not in active:
            continue
        term=str(phrase.phrase or '').strip()
        if len(term)<5:
            continue
        pattern=r'(?<!\w)'+re.escape(term.casefold())+r'(?!\w)'
        hit=re.search(pattern,lower)
        if not hit:
            continue
        left=max(0,hit.start()-115)
        right=min(len(text),hit.end()+115)
        excerpt=text[left:right].strip()
        if not any(marker in excerpt.casefold() for marker in markers):
            continue
        # Avoid treating historic court verdict reporting as a new allegation.
        if re.search(r'(majelis hakim|putusan pengadilan|diputus bersalah|vonis)',excerpt,re.IGNORECASE):
            continue
        matches.append({'category_id':phrase.category_id,
                        'category_name':active[phrase.category_id],
                        'evidence_quote':excerpt[:350],
                        'explanation':'Administrator phrase with allegation context; needs independent human verification.',
                        'signal_provenance':'KEYWORD_SCREENING',
                        'requires_human_verification':True})
        if len(matches)>=4:
            break
    return matches

def validated_reported_incident_signals(raw_signals, active_categories, source_text):
    """Validate source-quoted reported incidents, without assigning actor guilt.

    AI must explicitly propose these leads; keyword matching alone cannot flag.
    """
    if not isinstance(raw_signals,list):return []
    source=str(source_text or '')
    result=[]
    for raw in raw_signals[:8]:
        if not isinstance(raw,dict):continue
        cid=raw.get('category_id')
        quote=str(raw.get('evidence_quote') or '').strip()
        if type(cid) is not int or cid not in active_categories:continue
        if len(quote)<20 or len(quote)>350 or quote.casefold() not in source.casefold():continue
        context=str(raw.get('time_context') or '').upper()
        if context not in ('HISTORICAL','CURRENT','UNKNOWN'):continue
        result.append({'category_id':cid,'category_name':active_categories[cid],
            'signal_type':'REPORTED_INCIDENT','signal_provenance':'AI_REPORTED_INCIDENT',
            'evidence_quote':quote,'explanation':str(raw.get('explanation') or '')[:400],
            'time_context':context,'requires_human_verification':True})
    return result
