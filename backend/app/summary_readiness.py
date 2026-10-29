"""No-credit summary readiness from existing, authorized saved assessments."""
import hashlib
from .access import has
from .finding_groups import campaign_for
from .campaigns import campaign_action

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
        digest=hashlib.sha256(body.encode('utf-8')).hexdigest()
        drafts=[draft for draft in (post.get('player_summaries') or [])
            if isinstance(draft,dict)
            and draft.get('status')=='AI_DRAFT_REQUIRES_HUMAN_REVIEW'
            and 10<=len(str(draft.get('summary') or '').strip())<=500
            and len(str(draft.get('source_quote') or '').strip())>=15
            and str(draft.get('source_quote') or '').strip().casefold()
                in body.casefold()
            and (not draft.get('source_text_sha256')
                 or draft['source_text_sha256']==digest)]
        chatgpt_samples=[draft for draft in drafts if
            draft.get('provenance')=='GPT6_CHAT_GENERATED_QA_SAMPLE']
        pipeline_drafts=[draft for draft in drafts if
            draft.get('provenance')!='GPT6_CHAT_GENERATED_QA_SAMPLE']
        rows.append({'result_id':str(post['id']),
            'campaign_id':str(campaign.id),
            'has_saved_ai_summary':bool(drafts),
            'valid_summary_drafts':len(drafts),
            'development_chatgpt_drafts':len(chatgpt_samples),
            'pipeline_ai_drafts':len(pipeline_drafts),
            'summaries_require_human_review':True,
            'source_excerpt':body[:260],
            'source_excerpt_is_ai_summary':False,
            'requires_paid_ai_for_new_draft':not bool(drafts)})
    no_draft=[row for row in rows if not row['has_saved_ai_summary']]
    return {'campaign_id':str(campaign.id),
        'visible_relevant_posts':len(rows),
        'posts_with_valid_saved_ai_drafts':len(rows)-len(no_draft),
        'posts_with_development_chatgpt_samples':sum(
            bool(x['development_chatgpt_drafts']) for x in rows),
        'posts_with_pipeline_ai_drafts':sum(
            bool(x['pipeline_ai_drafts']) for x in rows),
        'posts_needing_ai_drafts':len(no_draft),
        'source_fingerprints_checked':True,
        'human_approved_summary_count':0,
        'manual_sample_is_not_pipeline_acceptance':True,
        'suggested_small_pilot_ids':[x['result_id'] for x in no_draft[:5]
            if x['source_excerpt']],
        'sources':rows[:100],
        'readiness_not_completion':True,
        'next_step':'Run a small explicitly approved AI pilot, then verify verbatim source quotes',
        'no_new_ai_called':True,'paid_provider_called':False}
