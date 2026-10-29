"""Persist reviewed incident/narrative/duplicate groups from authorized saved posts.

No crawl or paid model inference. Proposed grouping is NOT a confirmed legal
violation or event. A separate authorized human decision can accept/reject it.
"""
import hashlib
import json
from datetime import datetime
from .models import (CampaignFindingGroup,MonitoringCampaign,CampaignEvidence,
                     SocialListeningResult,EvidenceAssessment)
from .access import allowed,has,audit
from .socialcrawl import _result_in_scope
from .processing_hints import (exact_source_groups,incident_cluster_candidates,
                               emerging_narrative_candidates)

GROUP_TYPES={'EXACT_DUPLICATE','INCIDENT_CANDIDATE','NARRATIVE_CANDIDATE'}
MAX_SOURCE_ROWS=300
MAX_GROUPS_PER_SAVE=25


def campaign_for(db,p,raw_id):
    if not str(raw_id or '').isdigit():
        raise ValueError('Select a valid campaign')
    campaign=db.get(MonitoringCampaign,int(raw_id))
    if not campaign or not allowed(p,campaign):
        raise PermissionError('Campaign unavailable')
    return campaign


def eligible_source_rows(db,p,campaign,limit=MAX_SOURCE_ROWS):
    """Latest relevant saved assessment for each explicitly linked source."""
    from .sentiment_processing import relevance_is_assessed
    links=(db.query(CampaignEvidence).filter_by(campaign_id=campaign.id)
           .order_by(CampaignEvidence.id.asc()).limit(limit+1).all())
    rows=[]
    for link in links[:limit]:
        post=db.get(SocialListeningResult,link.result_id)
        if not post or not _result_in_scope(db,p,post):
            continue
        assessment=(db.query(EvidenceAssessment).filter_by(
            campaign_id=campaign.id,result_id=post.id)
            .order_by(EvidenceAssessment.assessment_version.desc(),
                      EvidenceAssessment.id.desc()).first())
        if not relevance_is_assessed(assessment) or str(
                assessment.relevance_label).upper() not in ('RELEVANT','HIGHLY_RELEVANT'):
            continue
        try: signals=json.loads(assessment.candidate_signals_json or '[]')
        except (TypeError,ValueError): signals=[]
        rows.append({'id':str(post.id),'campaign_id':str(campaign.id),
            'text_content':post.text_content,
            'canonical_url':post.canonical_url,
            'published_at':post.published_at,
            'author_name':post.author_name,
            'candidate_signals':signals if isinstance(signals,list) else [],
            'relevance_label':assessment.relevance_label})
    return rows,len(links)>limit


def propose_groups(rows):
    proposals=[]
    for group in exact_source_groups(rows):
        proposals.append({'type':'EXACT_DUPLICATE','label':'Repeated normalized source content',
                          'source_ids':group['post_ids'],'incident_verified':False})
    for group in incident_cluster_candidates(rows):
        proposals.append({'type':'INCIDENT_CANDIDATE',
            'label':group['discussion_anchor']+' · '+group['incident_province_unverified']+
                    ' · '+group['publication_month'],
            'source_ids':group['source_ids'],'incident_verified':False})
    for group in emerging_narrative_candidates(rows):
        proposals.append({'type':'NARRATIVE_CANDIDATE','label':group['anchor'],
            'source_ids':group['source_ids'],'incident_verified':False})
    return sorted(proposals,key=lambda x:(x['type'],x['label'],x['source_ids']))


def group_key(campaign_id,group):
    encoded=json.dumps([int(campaign_id),group['type'],
        sorted(str(x) for x in group['source_ids'])],
        separators=(',',':'),ensure_ascii=False)
    return hashlib.sha256(encoded.encode('utf-8')).hexdigest()


def serialize_group(group):
    try: ids=json.loads(group.source_ids_json or '[]')
    except (TypeError,ValueError):ids=[]
    return {'id':str(group.id),'campaign_id':str(group.campaign_id),
        'group_type':group.group_type,'label':group.label,
        'source_ids':ids,'review_status':group.review_status,
        'review_rationale':group.review_rationale,
        'reviewed_by':group.reviewed_by,
        'grouping_reviewed':group.review_status in ('ACCEPTED','REJECTED'),
        'legal_violation_confirmed':False,
        'paid_provider_called':False}


def visible_saved_groups(db,p,campaign):
    groups=(db.query(CampaignFindingGroup).filter_by(campaign_id=campaign.id)
            .order_by(CampaignFindingGroup.id.desc()).limit(100).all())
    if not groups:return []
    valid_ids=set()
    for link in db.query(CampaignEvidence).filter_by(campaign_id=campaign.id).all():
        source=db.get(SocialListeningResult,link.result_id)
        if source and _result_in_scope(db,p,source):
            valid_ids.add(str(link.result_id))
    visible=[]
    for group in groups:
        entry=serialize_group(group)
        if entry['source_ids'] and set(entry['source_ids']).issubset(valid_ids):
            visible.append(entry)
    return visible


def finding_group_action(db,p,action,data,id=None):
    if not has(p,'view_intelligence'):
        raise PermissionError('Viewing intelligence is required')
    campaign=campaign_for(db,p,id or data.get('campaign_id'))
    if action=='campaignFindingGroupsList':
        saved=visible_saved_groups(db,p,campaign)
        return {'groups':saved,'count':len(saved),
            'accepted_count':sum(x['review_status']=='ACCEPTED' for x in saved),
            'pending_count':sum(x['review_status']=='PROPOSED' for x in saved),
            'paid_provider_called':False}
    if action in ('campaignFindingGroupsPreview','campaignFindingGroupsSave'):
        rows,truncated=eligible_source_rows(db,p,campaign)
        proposals=propose_groups(rows)
        summary={'campaign_id':str(campaign.id),'eligible_posts':len(rows),
            'sample_window_limit':MAX_SOURCE_ROWS,'source_window_truncated':truncated,
            'proposals':proposals[:MAX_GROUPS_PER_SAVE],
            'proposal_count':len(proposals),'shown_count':min(len(proposals),MAX_GROUPS_PER_SAVE),
            'max_groups_per_save':MAX_GROUPS_PER_SAVE,
            'verification_status':'PROVISIONAL_REQUIRES_HUMAN_REVIEW',
            'paid_provider_called':False,'socialcrawl_credits':0}
        if action=='campaignFindingGroupsPreview':
            return summary
        if not has(p,'review_ai_suggestions'):
            raise PermissionError('Review AI Suggestions permission required to save proposals')
        if data.get('confirm_save') is not True:
            raise ValueError('Explicit confirmation required to save provisional groups')
        existing={row.group_key for row in db.query(CampaignFindingGroup).filter_by(
            campaign_id=campaign.id).all()}
        created=[]
        for item in proposals[:MAX_GROUPS_PER_SAVE]:
            key=group_key(campaign.id,item)
            if key in existing:continue
            row=CampaignFindingGroup(campaign_id=campaign.id,
                group_key=key,group_type=item['type'],label=item['label'][:255],
                source_ids_json=json.dumps(item['source_ids']),
                review_status='PROPOSED',created_by=str(p.get('id') or ''))
            db.add(row);existing.add(key);created.append(row)
        db.commit()
        for item in created:db.refresh(item)
        if created:audit(db,p,'CampaignFindingGroup',str(campaign.id),
            'PROVISIONAL_GROUPS_SAVED',{'count':len(created),
                'source_window_truncated':truncated})
        return {**summary,'newly_saved':len(created),
                'already_saved':len(proposals[:MAX_GROUPS_PER_SAVE])-len(created),
                'saved_group_ids':[str(row.id) for row in created]}
    if action=='campaignFindingGroupsReview':
        if not has(p,'human_validation'):
            raise PermissionError('Human Validation permission required')
        raw=data.get('group_id')
        if not str(raw or '').isdigit():raise ValueError('Valid group ID required')
        group=db.get(CampaignFindingGroup,int(raw))
        if not group or group.campaign_id!=campaign.id:
            raise PermissionError('Group unavailable')
        decision=str(data.get('decision') or '')
        if decision not in ('ACCEPTED','REJECTED'):
            raise ValueError('Choose ACCEPTED or REJECTED')
        reason=' '.join(str(data.get('rationale') or '').split())
        if not 10<=len(reason)<=1200:
            raise ValueError('Provide 10-1200 characters of human review rationale')
        if group.review_status!='PROPOSED':
            raise ValueError('Reviewed grouping is immutable; create a new proposal for changes')
        # Recheck source-level authorization before returning or reviewing group.
        visible={row['id'] for row in visible_saved_groups(db,p,campaign)}
        if str(group.id) not in visible:
            raise PermissionError('Source scope changed; group cannot be reviewed')
        group.review_status=decision
        group.review_rationale=reason
        group.reviewed_by=str(p.get('id') or '')
        group.reviewed_at=datetime.utcnow()
        db.commit()
        audit(db,p,'CampaignFindingGroup',group.id,'GROUP_REVIEWED',
            {'decision':decision,'campaign_id':campaign.id,
             'group_type':group.group_type})
        return {'saved':True,'group':serialize_group(group),
                'paid_provider_called':False}
    raise ValueError('Unknown campaign grouping action')
