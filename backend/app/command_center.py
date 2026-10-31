"""Permission-scoped, read-only Executive Intelligence Command Center.

Derived entirely from existing campaign evidence, assessments, reviews,
watchlists and linked account posts. No paid provider or AI calls.
"""
import json
import re
from collections import defaultdict, Counter
from datetime import date, datetime, timedelta
from sqlalchemy import and_, func
from .access import allowed, has
from .geography import province_code_for, province_name_for, regency_code_for, REGENCY_BY_CODE, PROVINCES, INDONESIAN_PROVINCE_ALIASES

def _province_name(code):
    names=INDONESIAN_PROVINCE_ALIASES.get(str(code),[])
    return names[0] if names else province_name_for(code)
from .issue_signals import validated_issue_signals, phrase_screening_candidates, shared_violation_decision
from .models import (MonitoringCampaign, CampaignEvidence, EvidenceAssessment,
    EvidenceReview, SocialListeningResult, IssueCategory, IssueCategoryPhrase,
    WatchlistItem, SourceAccount, WatchlistAccountEvidence, WatchlistAccountSync, IntelligenceItem)
from .socialcrawl import _result_in_scope

def _as_list(raw):
    try:
        value=json.loads(raw or '[]')
        return value if isinstance(value,list) else []
    except (TypeError, ValueError):
        return []

def _period(data):
    today=datetime.utcnow().date()
    preset=str(data.get('period') or '7d')
    if preset not in ('today','7d','30d','custom','all'):
        raise ValueError('Unknown date range')
    if preset=='all':
        start=date(1970,1,1);end=today
    elif preset=='custom':
        try:
            start=date.fromisoformat(str(data.get('date_from') or ''))
            end=date.fromisoformat(str(data.get('date_to') or ''))
        except ValueError:
            raise ValueError('A custom range requires two valid dates')
    else:
        days={'today':1,'7d':7,'30d':30}[preset]
        start=today-timedelta(days=days-1);end=today
    if start>end or (preset!='all' and (end-start).days>366) or end>today:
        raise ValueError('Date range must be valid, no more than 367 days, and not in the future')
    return start.isoformat(),end.isoformat(),preset

def _day(value):
    raw=str(value or '')[:10]
    try:return date.fromisoformat(raw).isoformat()
    except (ValueError,TypeError):return ''

def _scope(p,data):
    selected=str(data.get('province') or '').strip()
    scope=p.get('geographic_scope')
    if scope=='Nationwide':
        if selected and not province_code_for(selected):
            raise ValueError('Unknown province')
        return selected, 'Nationwide' if not selected else _province_name(province_code_for(selected))
    assigned=str(p.get('province') or '').strip()
    assigned_code=province_code_for(assigned,p.get('province_code'))
    if not assigned_code:
        raise PermissionError('Geographic assignment is not configured')
    if selected and province_code_for(selected)!=assigned_code:
        raise PermissionError('Province is outside your authorized scope')
    label=', '.join(x for x in (p.get('regency_city'),p.get('province')) if x) if scope=='Regency/City' else assigned
    return assigned,label

def _region_code(c):
    # A monitoring campaign's targeted region is NOT proof of the post's origin.
    return province_code_for(c.province)

def _explicit_province_mentions(text):
    # Surface observed province references as thematic associations, not incident locations.
    # Match known aliases as whole phrases; do not infer geography from author identity.
    normalized=' '+re.sub(r'[^a-z0-9]+',' ',str(text or '').lower()).strip()+' '
    found=set()
    for code,names in INDONESIAN_PROVINCE_ALIASES.items():
        for name in names:
            term=' '+re.sub(r'[^a-z0-9]+',' ',name.lower()).strip()+' '
            if len(term.strip())>=4 and term in normalized:
                found.add(code)
                break
    return found

def _briefing(relevant, alerts, waiting, provinces, watch_count, from_day, to_day):
    if not relevant and not alerts:
        return {'text':'No AI-assessed relevant campaign evidence was available for this period and authorized monitoring scope. This does not mean no electoral issues occurred.',
                'kind':'DATA_COVERAGE_NOTICE','sources':[], 'limitation':'Unassessed and uncollected posts are not represented.'}
    parts=[str(len(relevant))+' distinct AI-assessed relevant mention'+('s' if len(relevant)!=1 else '')+' were available for this period.']
    if alerts:
        kinds=Counter(a['category'] for a in alerts)
        top=', '.join(k for k,_ in kinds.most_common(2))
        parts.append(str(len(alerts))+' preliminary issue alert'+('s' if len(alerts)!=1 else '')+' need'+('' if len(alerts)!=1 else 's')+' attention, including '+top+'.')
    else:
        parts.append('No preliminary issue alerts were identified among the assessed relevant records in scope.')
    if waiting:
        parts.append(str(waiting)+' alert'+('s' if waiting!=1 else '')+' await'+('' if waiting!=1 else 's')+' human review.')
    if provinces:
        parts.append('The highest volume of scoped assessed mentions is associated with '+provinces[0]['province']+' monitoring campaigns; this does not identify the authors\' locations.')
    if watch_count:
        parts.append(str(watch_count)+' captured Watchlist post'+('s' if watch_count!=1 else '')+' were linked to monitored accounts in the period.')
    return {'text':' '.join(parts),'kind':'EVIDENCE_DERIVED_BRIEFING',
            'sources':[{'campaign_id':r['campaign_id'],'result_id':r['result_id']} for r in (alerts[:3] or relevant[:3])],
            'limitation':'Compiled from stored AI assessments, not a comprehensive analysis of all crawled conversations. No new generative AI request was made.'}

def build_command_center(db,p,data=None):
    if not has(p,'view_intelligence'):
        raise PermissionError('View intelligence permission required')
    data=data if isinstance(data,dict) else {}
    start,end,preset=_period(data)
    selected,scope_label=_scope(p,data)
    selected_code=province_code_for(selected)
    campaigns=[c for c in db.query(MonitoringCampaign).all() if allowed(p,c)]
    if selected_code:
        campaigns=[c for c in campaigns if _region_code(c)==selected_code]
    campaigns_by_id={c.id:c for c in campaigns}
    campaigns_ids=list(campaigns_by_id)
    # Latest version per (campaign, source), avoiding inflation from reassessment.
    assessed_rows=[]
    if campaigns_ids:
        latest=(db.query(EvidenceAssessment.campaign_id.label('cid'),
                         EvidenceAssessment.result_id.label('rid'),
                         func.max(EvidenceAssessment.assessment_version).label('ver'))
                .filter(EvidenceAssessment.campaign_id.in_(campaigns_ids))
                .group_by(EvidenceAssessment.campaign_id,EvidenceAssessment.result_id)
                .subquery())
        assessed_rows=(db.query(EvidenceAssessment,SocialListeningResult)
            .join(latest,and_(EvidenceAssessment.campaign_id==latest.c.cid,
                              EvidenceAssessment.result_id==latest.c.rid,
                              EvidenceAssessment.assessment_version==latest.c.ver))
            .join(SocialListeningResult,SocialListeningResult.id==EvidenceAssessment.result_id)
            .join(CampaignEvidence,and_(CampaignEvidence.campaign_id==EvidenceAssessment.campaign_id,
                                        CampaignEvidence.result_id==EvidenceAssessment.result_id,
                                        CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'))
            .filter(func.substr(SocialListeningResult.published_at,1,10)>=start,
                    func.substr(SocialListeningResult.published_at,1,10)<=end)
            .order_by(EvidenceAssessment.created_at.desc(),EvidenceAssessment.id.desc()).all())
    categories=db.query(IssueCategory).filter(IssueCategory.active.is_(True)).all()
    category_names={row.id:row.name for row in categories}
    phrases=db.query(IssueCategoryPhrase).filter(IssueCategoryPhrase.active.is_(True)).all()
    relevant={}
    alerts_by_post={}
    region_posts=defaultdict(set)
    region_captured=defaultdict(set)
    region_unknown_captured=set()
    platform_counts=Counter()
    day_counts=Counter()
    latest_captured=[]
    region_flags=defaultdict(set)
    unknown_posts=set()
    evidence_checked=0
    assessed_ids=set()
    source_updated=None
    for assessment,post in assessed_rows:
        campaign=campaigns_by_id[assessment.campaign_id]
        if not _result_in_scope(db,p,post):continue
        evidence_checked+=1
        assessed_ids.add(post.id)
        if source_updated is None or post.collected_at and post.collected_at>source_updated:
            source_updated=post.collected_at
        if str(assessment.relevance_label or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
            continue
        note={'result_id':str(post.id),'campaign_id':str(campaign.id),
              'campaign_name':campaign.name,'source_url':post.canonical_url,
              'platform':post.platform,'author':post.author_name or post.observed_handle or 'Unknown author',
              'published_at':post.published_at,'detected_at':assessment.created_at.isoformat() if assessment.created_at else None,
              'summary':(assessment.explanation or post.text_content or '').strip()[:260],
              'relevance_label':assessment.relevance_label}
        relevant.setdefault(post.id,note)
        code=_region_code(campaign)
        if code:region_posts[code].add(post.id)
        else:unknown_posts.add(post.id)
        explicit=validated_issue_signals(_as_list(assessment.potential_issue_signals_json),
                                         category_names,post.text_content)
        # Keyword-only leads are not saved source-validated potential violations.
        # Same review states and validated issue candidates used by Intelligence Inbox.
        review=(db.query(EvidenceReview).join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
                .filter(EvidenceAssessment.campaign_id==campaign.id,
                        EvidenceAssessment.result_id==post.id,
                        EvidenceReview.decision.in_(['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']))
                .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).first())
        decision=review.decision if review else 'AWAITING_REVIEW'
        decision_view=shared_violation_decision(explicit,decision)
        if not decision_view['is_flagged']:continue
        signal=explicit[0] if explicit else {'category_name':'Officer-reviewed issue',
            'evidence_quote':'','explanation':'Check saved source evidence',
            'signal_provenance':'HUMAN_REVIEW'}
        if code:region_flags[code].add(post.id)
        candidate=_as_list(assessment.candidate_signals_json)
        candidate_name=''
        if candidate:
            first=candidate[0]
            candidate_name=str(first.get('name') or first.get('value') or '') if isinstance(first,dict) else str(first)
        alert={**note,'assessment_version':assessment.assessment_version,
               'violation_uncertainty':decision_view['uncertainty_label'],'category':signal['category_name'],'evidence_quote':signal.get('evidence_quote','')[:280],
               'description':signal.get('explanation') or note['summary'],
               'candidate':candidate_name[:120], 'province':_province_name(code) if code else 'Unknown / Unclassified',
               'province_basis':'CAMPAIGN_MONITORING_SCOPE' if code else 'UNCLASSIFIED',
               'review_status':decision,
               'signal_provenance':signal.get('signal_provenance',''),
               'priority':'Review now' if decision=='FURTHER_INVESTIGATION' else 'Awaiting review',
               'priority_order':3 if decision=='FURTHER_INVESTIGATION' else 2 if decision=='FLAG_CONFIRMED' else 1}
        prior=alerts_by_post.get(post.id)
        if prior is None or alert['priority_order']>prior['priority_order']:
            alerts_by_post[post.id]=alert
    # Homepage recency is based on saved assessment time, not publication time.
    latest_assessed=[]
    latest_alerts=[]
    if campaigns_ids:
        all_recent=(db.query(EvidenceAssessment,SocialListeningResult)
          .join(SocialListeningResult,SocialListeningResult.id==EvidenceAssessment.result_id)
          .join(CampaignEvidence,and_(CampaignEvidence.campaign_id==EvidenceAssessment.campaign_id,
                CampaignEvidence.result_id==EvidenceAssessment.result_id,
                CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'))
          .filter(EvidenceAssessment.campaign_id.in_(campaigns_ids))
          .order_by(EvidenceAssessment.created_at.desc(),EvidenceAssessment.id.desc())
          .limit(300).all())
        seen_recent=set()
        for assessment,post in all_recent:
            if post.id in seen_recent or not _result_in_scope(db,p,post):continue
            campaign=campaigns_by_id.get(assessment.campaign_id)
            if not campaign:continue
            seen_recent.add(post.id)
            note={'result_id':str(post.id),'campaign_id':str(campaign.id),
                  'campaign_name':campaign.name,'source_url':post.canonical_url,
                  'platform':post.platform,'author':post.author_name or post.observed_handle or 'Unknown author',
                  'published_at':post.published_at,
                  'detected_at':assessment.created_at.isoformat() if assessment.created_at else None,
                  'summary':(assessment.explanation or post.text_content or '').strip()[:260],
                  'relevance_label':assessment.relevance_label,'record_type':'ASSESSED_SOCIAL'}
            latest_assessed.append(note)
            if str(assessment.relevance_label or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):continue
            signals=validated_issue_signals(_as_list(assessment.potential_issue_signals_json),category_names,post.text_content)
            # Only saved, quoted issue evidence and officer decisions are actionable.
            review=(db.query(EvidenceReview).join(EvidenceAssessment,EvidenceReview.assessment_id==EvidenceAssessment.id)
               .filter(EvidenceAssessment.campaign_id==campaign.id,EvidenceAssessment.result_id==post.id,
                       EvidenceReview.decision.in_(['FLAG_CONFIRMED','FLAG_DISMISSED','FURTHER_INVESTIGATION']))
               .order_by(EvidenceReview.created_at.desc(),EvidenceReview.id.desc()).first())
            decision=review.decision if review else 'AWAITING_REVIEW'
            decision_view=shared_violation_decision(signals,decision)
            if not decision_view['is_flagged']:continue
            signal=signals[0] if signals else {'category_name':'Officer-reviewed issue',
                'evidence_quote':'','explanation':'Check saved source evidence',
                'signal_provenance':'HUMAN_REVIEW'}
            latest_alerts.append({**note,'assessment_version':assessment.assessment_version,
                'violation_uncertainty':decision_view['uncertainty_label'],'category':signal['category_name'],
                 'description':signal.get('explanation') or note['summary'],
                 'evidence_quote':signal.get('evidence_quote',''),
                 'province':_province_name(_region_code(campaign)) if _region_code(campaign) else 'Unclassified',
                 'review_status':decision,'signal_provenance':signal.get('signal_provenance','')})
    # Complete coverage denominator: all campaign-linked, authorized captured
    # posts in the period, including posts that have not received AI screening.
    # Use narrow columns to avoid loading large raw-payload JSON records.
    captured_ids=set()
    if campaigns_ids:
        from types import SimpleNamespace
        captured_query=(db.query(CampaignEvidence.campaign_id,
                                  SocialListeningResult.id,SocialListeningResult.run_id,
                                  SocialListeningResult.platform,SocialListeningResult.published_at)
            .join(SocialListeningResult,CampaignEvidence.result_id==SocialListeningResult.id)
            .filter(CampaignEvidence.campaign_id.in_(campaigns_ids),
                    CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                    func.substr(SocialListeningResult.published_at,1,10)>=start,
                    func.substr(SocialListeningResult.published_at,1,10)<=end)
            .yield_per(600))
        for campaign_id,post_id,run_id,platform,published_at in captured_query:
            if not _result_in_scope(db,p,SimpleNamespace(run_id=run_id)):
                continue
            code=_region_code(campaigns_by_id[campaign_id])
            if code:region_captured[code].add(post_id)
            else:region_unknown_captured.add(post_id)
            if post_id in captured_ids:
                continue
            captured_ids.add(post_id)
            platform_counts[str(platform or 'Unknown').strip() or 'Unknown']+=1
            day_counts[_day(published_at)]+=1
            latest_captured.append({
                'result_id':str(post_id),'platform':platform or 'Unknown',
                'published_at':published_at})
    latest_captured.sort(key=lambda row:row['published_at'] or '',reverse=True)
    latest_captured=latest_captured[:3]
    # Hydrate source details only for the small visible highlights.
    for entry in latest_captured:
        original=db.get(SocialListeningResult,int(entry['result_id']))
        if original:
            entry.update({'source_url':original.canonical_url,
                          'author':original.author_name or 'Unknown author',
                          'preview':str(original.text_content or '').strip()[:170]})
    # Distinguish when a post was published from when it entered Social Listening.
    # The normal activity trend uses publication date, but an older post can
    # still have been collected today. Aggregate ingestion in SQL (not by
    # transferring potentially 40k+ full evidence rows to the API process).
    collected_query=(db.query(func.count(func.distinct(SocialListeningResult.id)))
        .join(CampaignEvidence,CampaignEvidence.result_id==SocialListeningResult.id)
        .filter(CampaignEvidence.campaign_id.in_(campaigns_ids),
                    CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                SocialListeningResult.collected_at>=datetime.fromisoformat(start),
                SocialListeningResult.collected_at<datetime.combine(date.fromisoformat(end)+timedelta(days=1),datetime.min.time()))) if campaigns_ids else None
    if collected_query is not None and p.get('geographic_scope')!='Nationwide':
        from types import SimpleNamespace
        run_query=(db.query(SocialListeningResult.run_id)
            .join(CampaignEvidence,CampaignEvidence.result_id==SocialListeningResult.id)
            .filter(CampaignEvidence.campaign_id.in_(campaigns_ids),
                    CampaignEvidence.match_method!='WATCHLIST_ACCOUNT',
                    SocialListeningResult.collected_at>=datetime.fromisoformat(start),
                    SocialListeningResult.collected_at<datetime.combine(date.fromisoformat(end)+timedelta(days=1),datetime.min.time()))
            .distinct())
        authorized_runs=[run_id for (run_id,) in run_query
                         if _result_in_scope(db,p,SimpleNamespace(run_id=run_id))]
        collected_query=collected_query.filter(SocialListeningResult.run_id.in_(authorized_runs))
    newly_collected=int(collected_query.scalar() or 0) if collected_query is not None else 0
    # Include zero-activity dates; missing bars would overstate continuity.
    daily_series=[{'date':(date.fromisoformat(start)+timedelta(days=n)).isoformat(),
                   'count':day_counts.get((date.fromisoformat(start)+timedelta(days=n)).isoformat(),0)}
                  for n in range((date.fromisoformat(end)-date.fromisoformat(start)).days+1)] if preset!='all' else []
    assessed_coverage=len(captured_ids.intersection(assessed_ids))
    unassessed_coverage=len(captured_ids)-assessed_coverage

    alerts=list(alerts_by_post.values())
    alerts.sort(key=lambda a:(a['priority_order'],a['detected_at'] or ''),reverse=True)
    by_region=[{'province':_province_name(code),'count':len(posts),
                'relevant_count':len(region_posts.get(code,set())),
                'flagged':len(region_flags.get(code,set())),
                'province_code':code} for code,posts in region_captured.items()]
    by_region.sort(key=lambda r:(r['flagged'],r['count']),reverse=True)
    # Use the same period, campaign authorization and source-run scope as
    # the Social Evidence Inbox summary. Old code independently fetched all
    # assessments from all dates, giving a stale province map after filtering.
    # Restore the Build 90.6 all-time geography inventory. A post published
    # before the dashboard date filter must not disappear from the map merely
    # because its AI assessment was saved recently.
    regional_assessed=defaultdict(set)
    if campaigns_ids:
        latest_geo=(db.query(EvidenceAssessment.campaign_id.label('cid'),
                             EvidenceAssessment.result_id.label('rid'),
                             func.max(EvidenceAssessment.assessment_version).label('ver'))
            .filter(EvidenceAssessment.campaign_id.in_(campaigns_ids))
            .group_by(EvidenceAssessment.campaign_id,EvidenceAssessment.result_id).subquery())
        geo_rows=(db.query(EvidenceAssessment,SocialListeningResult)
            .join(latest_geo,and_(EvidenceAssessment.campaign_id==latest_geo.c.cid,
                 EvidenceAssessment.result_id==latest_geo.c.rid,
                 EvidenceAssessment.assessment_version==latest_geo.c.ver))
            .join(SocialListeningResult,SocialListeningResult.id==EvidenceAssessment.result_id)
            .join(CampaignEvidence,and_(CampaignEvidence.campaign_id==EvidenceAssessment.campaign_id,
                 CampaignEvidence.result_id==EvidenceAssessment.result_id,
                 CampaignEvidence.match_method!='WATCHLIST_ACCOUNT'))
            .all())
        for assessment,post in geo_rows:
            if not _result_in_scope(db,p,post):continue
            codes=set()
            for signal in _as_list(assessment.geographic_signals_json):
                value=signal if isinstance(signal,str) else (signal.get('province') or signal.get('name') or signal.get('value') or signal.get('regency_city') or '') if isinstance(signal,dict) else ''
                value=str(value or '').strip()
                code=province_code_for(value)
                if not code:
                    city=regency_code_for(value)
                    if city:code=str(REGENCY_BY_CODE[city].get('province_code') or '')
                if not code and value.lower().replace(' ','') in ('sumbar','sumaterabarat'):code='13'
                if code and (not selected_code or code==selected_code):codes.add(code)
            for code in codes:regional_assessed[code].add(assessment.result_id)
    regional_inbox_signals=[{'province':_province_name(code),'province_code':code,'records':len(ids)}
        for code,ids in regional_assessed.items()]
    regional_inbox_signals.sort(key=lambda item:item['records'],reverse=True)
    # Regional Intelligence Inbox heatmap is an all-time authorized inventory.
    # It is independent of the campaign-post monitoring date window.
    regional_intel=defaultdict(lambda:{'records':set(),'pending':set(),'potential':set(),'confirmed':set(),'mentioned':set()})
    unclassified_intel=0
    national_intel=0
    mapped_intel_ids=set()
    for record in db.query(IntelligenceItem).all():
        if not allowed(p,record):continue
        # National records have no province by design; do not mark them as unmapped.
        if record.jurisdiction_type=='National':
            national_intel+=1
            continue
        # Match the recorded province fields used in the Intelligence Inbox.
        # Keep human-confirmed jurisdictions distinguishable from recorded but unconfirmed ones.
        areas=_as_list(record.geographic_assignments_json) if record.jurisdiction_type=='Multi-Region' else [{'province':record.province,'province_code':record.province_code}]
        codes=set()
        for area in areas:
            if not isinstance(area,dict):continue
            code=province_code_for(area.get('province') or area.get('province_name'),area.get('province_code'))
            if code and (not selected_code or code==selected_code):codes.add(code)
        # If no explicit assigned province exists, allow source-supported associations.
        # Never overwrite jurisdiction fields or claim these are verified locations.
        mention_codes=set()
        if not codes:
            for raw in (record.location_text,record.ai_summary,record.title,record.original_content):
                mention_codes.update(_explicit_province_mentions(str(raw or '')[:6000]))
            for field in (record.ai_geography_json,record.proposed_geography_json):
                try: structured=json.loads(field or '{}')
                except (TypeError,ValueError):structured={}
                if isinstance(structured,dict):
                    province_value=structured.get('province') or structured.get('province_name')
                    candidate=province_code_for(province_value,structured.get('province_code'))
                    if candidate:mention_codes.add(candidate)
            if selected_code:mention_codes={code for code in mention_codes if code==selected_code}
            codes=mention_codes
        if not codes:
            unclassified_intel+=1
            continue
        try: proposed=json.loads(record.ai_suggestions_json or '{}')
        except (ValueError,TypeError):proposed={}
        decisions=proposed.get('_decisions') or {}
        try: screening=json.loads(record.supervision_screening_json or '{}')
        except (ValueError,TypeError):screening={}
        raw_signal=str(screening.get('supervision_signal') or '').upper()
        ai_signal=str(proposed.get('supervision_signal') or '').upper()
        flagged=(raw_signal=='POTENTIAL REGULATORY ISSUE' or
                 (decisions.get('supervision_signal',{}).get('status')!='Human Rejected' and ai_signal in ('POTENTIAL REGULATORY ISSUE','REVIEW RECOMMENDED')))
        for code in codes:
            mapped_intel_ids.add(record.id)
            entry=regional_intel[code];entry['records'].add(record.id)
            if code in mention_codes:entry['mentioned'].add(record.id)
            if record.jurisdiction_confirmed is True and code not in mention_codes:entry['confirmed'].add(record.id)
            if record.review_status in ('Pending Review','Awaiting Validation'):entry['pending'].add(record.id)
            if flagged:entry['potential'].add(record.id)
    regional_intelligence=[{'province':_province_name(code),'province_code':code,
        'records':len(v['records']),'confirmed':len(v['confirmed']),'associated':len(v['mentioned']),'pending':len(v['pending']),
        'potential_signals':len(v['potential'])} for code,v in regional_intel.items()]
    regional_intelligence.sort(key=lambda x:(x['potential_signals'],x['pending'],x['records']),reverse=True)
    # Read-only signal volume inventory. Only authorized saved assessments are
    # counted; a source mention is not a legal finding or suspicion of a person.
    # Resolve known candidate aliases before counting. Post-ID sets prevent
    # multiple spellings in one source from inflating mention volume.
    candidate_aliases={
        'gibran':'Gibran Rakabuming Raka',
        'gibran rakabuming':'Gibran Rakabuming Raka',
        'gibran rakabuming raka':'Gibran Rakabuming Raka',
        'prabowo':'Prabowo Subianto',
        'prabowo subianto':'Prabowo Subianto',
    }
    candidate_inventory={}
    category_post_ids=defaultdict(set)
    seen_signal_posts=set()
    for assessment,post in (all_recent if campaigns_ids else []):
        if post.id in seen_signal_posts or not _result_in_scope(db,p,post):continue
        seen_signal_posts.add(post.id)
        if str(assessment.relevance_label or '').upper() not in ('RELEVANT','HIGHLY_RELEVANT'):continue
        for item in _as_list(assessment.candidate_signals_json):
            name=(item.get('name') or item.get('value') or '') if isinstance(item,dict) else item
            name=str(name or '').strip()[:120]
            if len(name)<3:continue
            normalized=re.sub(r'\\s+',' ',name).strip().casefold()
            name=candidate_aliases.get(normalized,name)
            key=name.casefold()
            entry=candidate_inventory.setdefault(key,{'name':name,'posts':set()})
            entry['posts'].add(post.id)
        signals=validated_issue_signals(_as_list(assessment.potential_issue_signals_json),category_names,post.text_content)
        # Issue volume uses saved quote-validated assessment signals only.
        for signal in signals:
            category_post_ids[str(signal['category_name'])].add(post.id)
    candidate_coverage=sorted(
        [{'name':v['name'],'mentions':len(v['posts'])} for v in candidate_inventory.values()],
        key=lambda row:(-row['mentions'],row['name'].casefold()))[:10]
    issue_volume=sorted(
        [{'category':name,'posts':len(ids)} for name,ids in category_post_ids.items()],
        key=lambda row:(-row['posts'],row['category']))[:10]
    # Descriptive operational queue size only, NEVER a person's guilt score.
    review_volume=len(latest_alerts)
    activity_band=('HIGH VOLUME' if review_volume>=20 else
                   'ELEVATED VOLUME' if review_volume>=5 else
                   'LOW VOLUME' if review_volume>0 else 'NO FLAGS')
    # Combine assessed social posts with traditional/manual Intelligence Inbox
    # records. These are presented as recent records, NOT counted again in
    # the distinct AI-assessed social indicators above.
    manual_recent=[]
    for record in db.query(IntelligenceItem).all():
        if not allowed(p,record):continue
        if selected_code and province_code_for(record.province,record.province_code)!=selected_code:
            continue
        date_text=record.publication_datetime or record.publication_date or ''
        display_date=date_text if _day(date_text) else record.created_at.isoformat() if record.created_at else ''
        if not start<=_day(display_date)<=end:continue
        manual_recent.append({
            'record_type':'INTELLIGENCE_ITEM','id':str(record.id),
            'campaign_name':record.intelligence_id or 'Intelligence Inbox record',
            'platform':record.platform or record.source_type or 'Recorded source',
            'author':record.observed_publisher_handle or record.author or record.source_name or 'Unknown source',
            'source_url':record.source_url,
            'published_at':display_date,
            'summary':(record.ai_summary or record.title or record.original_content or '').strip()[:260],
            'review_status':record.review_status,
            'date_basis':'SOURCE_PUBLICATION' if _day(date_text) else 'RECORD_CREATED'
        })
    for item in manual_recent:
        item['inbox_at']=item.get('published_at') or ''
    recent=sorted(latest_assessed+manual_recent,
                  key=lambda x:x.get('detected_at') or x.get('inbox_at') or '',reverse=True)[:3]
    # Watchlist highlights use only evidence explicitly linked to registered
    # accounts, not noisy substring matches against people's names.
    watch_items=[w for w in db.query(WatchlistItem).all() if allowed(p,w)]
    if selected_code:
        watch_items=[w for w in watch_items if province_code_for(w.province)==selected_code]
    watch_rows=[];watch_count_ids=set()
    if watch_items:
        ids=[w.id for w in watch_items]
        joined=(db.query(WatchlistItem,SourceAccount,WatchlistAccountEvidence,SocialListeningResult)
            .join(SourceAccount,SourceAccount.watchlist_id==WatchlistItem.id)
            .join(WatchlistAccountEvidence,WatchlistAccountEvidence.account_id==SourceAccount.id)
            .join(SocialListeningResult,SocialListeningResult.id==WatchlistAccountEvidence.result_id)
            .filter(WatchlistItem.id.in_(ids),
                    func.substr(SocialListeningResult.published_at,1,10)>=start,
                    func.substr(SocialListeningResult.published_at,1,10)<=end)
            .order_by(SocialListeningResult.published_at.desc(),SocialListeningResult.id.desc()).yield_per(200))
        seen_watch=set()
        for w,account,edge,post in joined:
            if not _result_in_scope(db,p,post):continue
            watch_count_ids.add(post.id)
            if w.id in seen_watch or len(watch_rows)>=5:continue
            seen_watch.add(w.id)
            watch_rows.append({'watchlist_id':str(w.id),'name':w.name,'province':w.province or 'Unclassified',
                'platform':post.platform,'handle':account.handle,'last_post_at':post.published_at,
                'last_post_url':post.canonical_url,'summary':(post.text_content or '')[:170]})
            # Keep scanning to count all scoped linked posts, not only highlights.
    waiting=sum(a['review_status']=='AWAITING_REVIEW' for a in alerts)
    briefing=_briefing(list(relevant.values()),alerts,
                       waiting,by_region,len(watch_count_ids),start,end)
    # The scope-specific executive snapshot includes ACTUAL captured mentions,
    # not just posts already assessed by AI.
    location_phrase=('Across authorized national monitoring campaigns' if not selected_code
                     else 'Within monitoring campaigns covering '+scope_label)
    activity_text=(location_phrase+', '+str(len(captured_ids))+
                   ' distinct social posts were captured from '+start+' to '+end+'.')
    if platform_counts:
        activity_text+=(' Most captured activity came from '+
            ', '.join(name+' ('+str(count)+')' for name,count in platform_counts.most_common(2))+'.')
    if assessed_coverage<len(captured_ids):
        activity_text+=(' '+str(unassessed_coverage)+' of these posts have not yet received AI assessment.')
    activity_text+=(' '+str(len(relevant))+' distinct posts were assessed as relevant.')
    if alerts:
        activity_text+=(' '+str(len(alerts))+' preliminary issue alert(s) remain on record; '+str(waiting)+' await human review.')
    else:
        activity_text+=' No undismissed preliminary issue alerts were identified among the assessed relevant posts in this period.'
    briefing['text']=activity_text
    briefing['kind']='LOCATION_EVIDENCE_BRIEFING' if captured_ids else 'DATA_COVERAGE_NOTICE'
    briefing['limitation']=('Compiled from captured campaign-linked posts and existing assessments only. '
        'Selected geography means monitoring campaign coverage, not verified post origin. '
        'Potential violations are preliminary and require authorized BAWASLU review.')
    attention=[]
    for issue in alerts[:3]:
        attention.append({
            'kind':'POTENTIAL_ISSUE','title':issue['category'],
            'description':issue['description'][:150],
            'review_status':issue['review_status'],
            'recommended_action':'Verify source evidence and assess whether further investigation is warranted.',
            'campaign_id':issue['campaign_id'],'result_id':issue['result_id']})
    if unassessed_coverage:
        attention.append({'kind':'ASSESSMENT_COVERAGE','title':'Evidence still awaiting AI assessment',
            'description':str(unassessed_coverage)+' captured post(s) have no AI assessment in this period.',
            'review_status':'NOT_ASSESSED',
            'recommended_action':'Open Social Listening to review captured evidence and its assessment status.'})

    # Action-oriented briefing: point to supported reviews, never fabricate an
    # AI narrative or turn missing assessments into a finding of no risk.
    focus=[]
    for item in latest_alerts[:3]:
        focus.append({'kind':'REVIEW_EVIDENCE','title':'Review preliminary '+item['category']+' signal',
            'detail':(item.get('description') or item.get('summary') or '')[:180],
            'campaign_id':item['campaign_id'],'result_id':item['result_id'],
            'basis':'STORED_ASSESSMENT'})
    if not focus and unassessed_coverage:
        focus.append({'kind':'COVERAGE_GAP','title':'Prioritize AI screening of unassessed captured evidence',
            'detail':'There are captured posts in this publication period without an AI assessment. Select a representative sample in Social Listening before drawing conclusions.',
            'basis':'CAPTURED_UNASSESSED_POSTS'})
    if not focus:
        focus.append({'kind':'VERIFY_COVERAGE','title':'Review recent Intelligence Inbox evidence and collection coverage',
            'detail':'No evidence-backed issue alert is available in the current authorized view. Check source coverage, assessments and review decisions before treating this as an absence of electoral issues.',
            'basis':'COVERAGE_STATUS'})
    return {'period':{'preset':preset,'date_from':start,'date_to':end},
            'available_provinces':[{'name':_province_name(row['code']),'code':str(row['code'])} for row in PROVINCES] if p.get('geographic_scope')=='Nationwide' else [{'name':scope_label,'code':province_code_for(selected)}],
            'scope':{'label':scope_label,'geographic_scope':p.get('geographic_scope'),
                     'selected_province':selected,'can_select_national':p.get('geographic_scope')=='Nationwide'},
            'generated_at':datetime.utcnow().isoformat()+'Z',
            'latest_evidence_at':source_updated.isoformat()+'Z' if source_updated else None,
            'indicators':{'relevant_mentions':len(relevant),
                'potential_alerts':len(latest_alerts),
                'awaiting_review':sum(x['review_status']=='AWAITING_REVIEW' for x in latest_alerts),
                'emerging_issues':None},
            'briefing':briefing,'focus_actions':focus,'attention_actions':attention[:4],
            'alerts':latest_alerts[:10], 'latest_intelligence':recent,
            'activity':{'captured_mentions':len(captured_ids),
                        'newly_collected_mentions':newly_collected,
                        'published_date_basis':'SOURCE_PUBLISHED_AT',
                        'ingestion_date_basis':'SOURCE_COLLECTED_AT',
                        'top_platforms':[{'platform':k,'count':v} for k,v in platform_counts.most_common(5)],
                        'daily':daily_series,
                        'recent_captured':latest_captured,
                        'data_basis':'CAMPAIGN_LINKED_CAPTURED_POSTS'},
            'regions':by_region[:38],
            'regional_intelligence':regional_intelligence[:38],
            'regional_intelligence_period':'ALL_TIME_AUTHORIZED',
            'regional_inbox_signals':regional_inbox_signals,
            'regional_inbox_signals_period':'ALL_TIME_AUTHORIZED',
            'signal_intelligence':{'candidate_mentions':candidate_coverage,
                'issue_categories':issue_volume,'flagged_assessment_volume':review_volume,
                'volume_band':activity_band,'thresholds':{'elevated':5,'high':20},
                'basis':'LATEST_SAVED_ASSESSMENTS_UNDER_AUTHORIZED_CAMPAIGNS',
                'legal_determination':False},
            'regional_monitoring_coverage':by_region[:38],
            'mapped_intelligence':len(mapped_intel_ids),
            'unclassified_intelligence':unclassified_intel,
            'national_intelligence':national_intel,
            'unknown_region_mentions':len(region_unknown_captured),
            'region_method':'CAMPAIGN_MONITORING_SCOPE_NOT_POST_ORIGIN',
            'watchlist':{'entries':watch_rows,'captured_posts_in_period':len(watch_count_ids),
                         'monitored_profiles':len(watch_items)},
            'coverage':{'captured_posts_in_period':len(captured_ids),
                        'assessed_posts_in_period':assessed_coverage,
                        'unassessed_posts_in_period':unassessed_coverage,
                        'assessed_pairs_in_period':evidence_checked,'relevant_distinct_posts':len(relevant),
                        'distinct_campaigns_in_scope':len(campaigns_by_id),
                        'warning':'Publication-date counts and newly collected counts are different measures. AI relevance and potential alerts require stored assessments. Province indicates campaign monitoring scope, not verified author location.'},
            'capabilities':{'emerging_issues':False,'ai_generated_new_summary':False,
                            'cross_module_assistant':False},
            'paid_provider_called':False}
