"""Read-only AI processing coverage, failures, token usage and cost availability."""
import json
from decimal import Decimal, InvalidOperation
from .models import (MonitoringCampaign,CampaignEvidence,SocialListeningResult,
    EvidenceAssessment,AIAssessmentJob,AIBudgetReservation,AssessmentAIUsage)
from .access import allowed,has
from .socialcrawl import _result_in_scope

def campaign_usage_diagnostics(db,p,raw_campaign_id):
    if not has(p,'view_intelligence'):
        raise PermissionError('Intelligence access is required')
    if not str(raw_campaign_id or '').isdigit():
        raise ValueError('Select a valid campaign')
    campaign=db.get(MonitoringCampaign,int(raw_campaign_id))
    if not campaign or not allowed(p,campaign):
        raise PermissionError('Campaign unavailable')
    links=(db.query(CampaignEvidence).filter_by(campaign_id=campaign.id)
           .order_by(CampaignEvidence.id.asc()).limit(301).all())
    missing={'content':0,'source_url':0,'published_at':0,'author':0,'platform':0}
    relevant_post_ids=set()
    assessed=0
    latest=[]
    for link in links[:300]:
        post=db.get(SocialListeningResult,link.result_id)
        if not post or not _result_in_scope(db,p,post):continue
        relevant_post_ids.add(post.id)
        if not str(post.text_content or '').strip():missing['content']+=1
        if not str(post.canonical_url or '').strip():missing['source_url']+=1
        if not str(post.published_at or '').strip():missing['published_at']+=1
        if not str(post.author_name or '').strip():missing['author']+=1
        if not str(post.platform or '').strip():missing['platform']+=1
        latest_assessment=(db.query(EvidenceAssessment).filter_by(
            campaign_id=campaign.id,result_id=post.id).order_by(
            EvidenceAssessment.assessment_version.desc(),EvidenceAssessment.id.desc()).first())
        if latest_assessment:
            assessed+=1
            latest.append(latest_assessment)
    jobs=db.query(AIAssessmentJob).filter_by(campaign_id=campaign.id).all()
    states={'PENDING':0,'PROCESSING':0,'COMPLETED':0,'FAILED':0}
    for job in jobs:
        if job.result_id in relevant_post_ids and job.state in states:
            states[job.state]+=1
    usage_rows=db.query(AssessmentAIUsage).filter_by(campaign_id=campaign.id).all()
    # Only user-scoped source IDs count, so a campaign cannot expose a
    # result that the current officer lacks authority to view.
    versions_by_id=db.query(EvidenceAssessment.id,EvidenceAssessment.result_id).filter(
        EvidenceAssessment.campaign_id==campaign.id).all()
    allowed_assessment_ids={aid for aid,rid in versions_by_id
                            if rid in relevant_post_ids}
    usage=[u for u in usage_rows if u.assessment_id in allowed_assessment_ids]
    reservations=db.query(AIBudgetReservation).filter_by(
        campaign_id=campaign.id).limit(400).all()
    known_costs=[]
    unknown_costs=0
    for entry in usage:
        if entry.cost_status!='REPORTED':
            unknown_costs+=1
            continue
        try:
            amount=Decimal(str(entry.cost_usd or ''))
            if not amount.is_finite() or amount<0:
                raise InvalidOperation
            known_costs.append(amount)
        except (InvalidOperation,ValueError):
            unknown_costs+=1
    reported_cost=sum(known_costs,Decimal('0'))
    cost_status=('COMPLETE_REPORTED' if usage and not unknown_costs
                 else 'PARTIAL_REPORTED' if known_costs
                 else 'NOT_AVAILABLE_FROM_PROVIDER')
    return {'campaign_id':str(campaign.id),'source_window_limit':300,
        'source_window_truncated':len(links)>300,
        'authorized_source_posts':len(relevant_post_ids),
        'posts_with_assessment_version':assessed,
        'posts_missing_assessment':len(relevant_post_ids)-assessed,
        'missing_fields':missing,'job_states':states,
        'failed_jobs':states['FAILED'],
        'ai_usage':{'tracked_assessment_requests':len(usage),
            'requests_with_provider_token_counts':sum(bool(x.usage_reported) for x in usage),
            'input_tokens_reported':sum(x.input_tokens for x in usage if x.usage_reported),
            'output_tokens_reported':sum(x.output_tokens for x in usage if x.usage_reported),
            'request_costs_unknown':unknown_costs,
            'requests_with_reported_cost':len(known_costs),
            'reported_cost_subtotal_usd':str(reported_cost) if known_costs else None,
            'actual_total_usd':str(reported_cost) if cost_status=='COMPLETE_REPORTED' else None,
            'cost_status':cost_status},
        'budget_reservations':{'lifetime':sum(x.reserved_requests for x in reservations
                                             if x.budget_period=='lifetime'),
            'daily_periods_recorded':len([x for x in reservations
                                           if x.budget_period!='lifetime'])},
        'scope':'AUTHORIZED_EXISTING_CAMPAIGN_POSTS_ONLY',
        'paid_provider_called':False,'socialcrawl_credits':0}
