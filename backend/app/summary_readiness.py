"""No-credit summary readiness from existing, authorized saved assessments."""
import hashlib
from .access import has
from .finding_groups import campaign_for
from .campaigns import campaign_action

def validated_summary_buckets(post):
    """Source-anchored drafts; untagged legacy drafts are NOT pipeline proof."""
    body=str(post.get('text_content') or '').strip()
    digest=hashlib.sha256(body.encode('utf-8')).hexdigest()
    buckets={'development':[],'pipeline':[],'unattributed':[]}
    for draft in post.get('player_summaries') or []:
        if not isinstance(draft,dict):continue
        if draft.get('status')!='AI_DRAFT_REQUIRES_HUMAN_REVIEW':continue
        if not 10<=len(str(draft.get('summary') or '').strip())<=500:continue
        quote=str(draft.get('source_quote') or '').strip()
        if len(quote)<15 or quote.casefold() not in body.casefold():continue
        fingerprint=draft.get('source_text_sha256')
        if fingerprint and fingerprint!=digest:continue
        provenance=draft.get('provenance')
        if provenance=='GPT6_CHAT_GENERATED_QA_SAMPLE':
            buckets['development'].append(draft)
        elif provenance=='PRODUCTION_AI_PIPELINE' and fingerprint==digest:
            buckets['pipeline'].append(draft)
        else:
            buckets['unattributed'].append(draft)
    return buckets

def campaign_summary_readiness(db,p,campaign_id):
    if not has(p,'view_intelligence'):
        raise PermissionError('Intelligence view permission required')
    campaign=campaign_for(db,p,campaign_id)
    response=campaign_action(db,p,'campaignIntelligenceInbox',
        {'campaign_id':str(campaign.id)})
    findings=response.get('findings') or []
    rows=[]
    for post in findings:
        body=str(post.get('text_content') or '').strip()
        buckets=validated_summary_buckets(post)
        drafts=sum((len(v) for v in buckets.values()),0)
        rows.append({'result_id':str(post['id']),
            'campaign_id':str(campaign.id),
            'has_saved_ai_summary':bool(drafts),
            'valid_summary_drafts':drafts,
            'development_chatgpt_drafts':len(buckets['development']),
            'pipeline_ai_drafts':len(buckets['pipeline']),
            'legacy_unattributed_drafts':len(buckets['unattributed']),
            'summaries_require_human_review':True,
            'source_excerpt':body[:260],
            'source_excerpt_is_ai_summary':False,
            'requires_paid_ai_for_new_draft':not bool(buckets['pipeline'])})
    no_draft=[row for row in rows if not row['has_saved_ai_summary']]
    no_pipeline=[row for row in rows if not row['pipeline_ai_drafts']]
    return {'campaign_id':str(campaign.id),
        'visible_relevant_posts':len(rows),
        'posts_with_valid_saved_ai_drafts':len(rows)-len(no_draft),
        'posts_with_development_chatgpt_samples':sum(
            bool(x['development_chatgpt_drafts']) for x in rows),
        'posts_with_pipeline_ai_drafts':len(rows)-len(no_pipeline),
        'posts_with_legacy_unattributed_drafts':sum(
            bool(x['legacy_unattributed_drafts']) for x in rows),
        'posts_needing_ai_drafts':len(no_draft),
        'posts_needing_pipeline_ai_drafts':len(no_pipeline),
        'source_fingerprints_checked':True,
        'human_approved_summary_count':0,
        'manual_sample_is_not_pipeline_acceptance':True,
        'suggested_small_pilot_ids':[x['result_id'] for x in no_pipeline[:5]
            if x['source_excerpt']],
        'sources':rows[:100],
        'readiness_not_completion':True,
        'next_step':'Run a small explicitly approved AI pilot, then obtain independent officer review of source quotes',
        'no_new_ai_called':True,'paid_provider_called':False}
