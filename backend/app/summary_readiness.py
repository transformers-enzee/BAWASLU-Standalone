"""No-credit summary readiness from existing, authorized saved assessments."""
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
        drafts=[draft for draft in (post.get('player_summaries') or [])
            if isinstance(draft,dict)
            and draft.get('status')=='AI_DRAFT_REQUIRES_HUMAN_REVIEW'
            and len(str(draft.get('source_quote') or '').strip())>=15
            and str(draft.get('source_quote') or '').strip().casefold()
                in body.casefold()]
        rows.append({'result_id':str(post['id']),
            'campaign_id':str(campaign.id),
            'has_saved_ai_summary':bool(drafts),
            'valid_summary_drafts':len(drafts),
            'source_excerpt':body[:260],
            'source_excerpt_is_ai_summary':False,
            'requires_paid_ai_for_new_draft':not bool(drafts)})
    no_draft=[row for row in rows if not row['has_saved_ai_summary']]
    return {'campaign_id':str(campaign.id),
        'visible_relevant_posts':len(rows),
        'posts_with_valid_saved_ai_drafts':len(rows)-len(no_draft),
        'posts_needing_ai_drafts':len(no_draft),
        'suggested_small_pilot_ids':[x['result_id'] for x in no_draft[:5]
            if x['source_excerpt']],
        'sources':rows[:100],
        'readiness_not_completion':True,
        'next_step':'Run a small explicitly approved AI pilot, then verify verbatim source quotes',
        'no_new_ai_called':True,'paid_provider_called':False}
