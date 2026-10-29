"""Read-only production evidence for the 15-point BAWASLU checklist.

Not a signing or review operation: this must never fabricate an officer
decision, invoke a provider, or count engineering tests as officer acceptance.
"""
from .access import has
from .finding_groups import (campaign_for,grouping_readiness,
    eligible_source_rows,duplicate_source_rows,propose_groups,visible_saved_groups)

def campaign_acceptance_snapshot(db,p,raw_id):
    if not has(p,'view_intelligence'):
        raise PermissionError('Intelligence permission required')
    campaign=campaign_for(db,p,raw_id)
    coverage=grouping_readiness(db,p,campaign)
    relevant,relevant_truncated=eligible_source_rows(db,p,campaign)
    duplicates,duplicate_truncated=duplicate_source_rows(db,p,campaign)
    proposals=propose_groups(relevant,duplicates)
    group_types=('EXACT_DUPLICATE','INCIDENT_CANDIDATE','NARRATIVE_CANDIDATE')
    candidate_counts={kind:sum(x['type']==kind for x in proposals)
                      for kind in group_types}
    saved=visible_saved_groups(db,p,campaign)
    reviewed={kind:sum(x['group_type']==kind and x['review_status']=='ACCEPTED'
                       for x in saved) for kind in group_types}
    stored={kind:sum(x['group_type']==kind for x in saved) for kind in group_types}
    # Campaign action already enforces row-level scope, latest assessment
    # versions, and validated issue signals for this officer.
    from .campaigns import campaign_action
    inbox=campaign_action(db,p,'campaignIntelligenceInbox',
                          {'campaign_id':str(campaign.id)})
    rows=inbox.get('findings') or []
    summary=inbox.get('classification_processing') or {}
    players=summary.get('intelligence_players') or {}
    total_players=sum(int(x.get('count') or 0) for x in players.values())
    total_topics=sum(bool(x.get('topic_labels')) for x in rows)
    draft_count=sum(bool(x.get('player_summaries')) for x in rows)
    reviews=sum(len(x.get('flag_review_history') or []) for x in rows)
    issue_posts=sum(bool(x.get('potential_issues')) for x in rows)
    verified_locations=sum(bool(x.get('incident_jurisdiction_verified')) for x in rows)
    assessed_sentiment=sum(str(x.get('sentiment') or '').upper() in (
        'POSITIVE','NEGATIVE','NEUTRAL') for x in rows)
    def item(number,name,state,sources,note):
        return {'number':number,'name':name,'production_state':state,
            'supporting_records':int(sources),'note':note,
            'officer_signoff_inferred':False}
    def group_state(kind):
        if reviewed[kind]:return 'OFFICER_REVIEWED'
        if stored[kind]:return 'SAVED_PENDING_OFFICER_REVIEW'
        if candidate_counts[kind]:return 'PROPOSALS_READY_TO_SAVE'
        return 'NO_QUALIFYING_PROPOSALS_IN_SAVED_EVIDENCE'
    ledger=[
       item(1,'Import posts','SAVED_SOURCE_EVIDENCE',
            coverage['authorized_posts'],'Authorized linked posts'),
       item(2,'Relevance filter','SAVED_RELEVANCE_EVIDENCE'
            if coverage['relevant_posts'] else 'NEEDS_RELEVANCE_EVIDENCE',
            coverage['relevant_posts'],'Latest saved relevance only'),
       item(3,'Sentiment','SAVED_SENTIMENT_EVIDENCE'
            if assessed_sentiment else 'NEEDS_SENTIMENT_EVIDENCE',
            assessed_sentiment,'Saved labels, not inferred sentiment'),
       item(4,'Potential violation detection','SAVED_HUMAN_REVIEW'
            if reviews else 'SAVED_ISSUE_SIGNALS' if issue_posts
            else 'NEEDS_ISSUE_EVIDENCE_AND_HUMAN_REVIEW',reviews or issue_posts,
            'Neither keyword cues nor flags prove a legal violation'),
       item(5,'Candidate normalization','ENGINEERING_TESTED_VALID_NO_CANDIDATE',
            len(rows),'Missing or ambiguous identities are valid'),
       item(6,'Incident jurisdiction','VERIFIED_BY_OFFICER'
            if verified_locations else 'NEEDS_OFFICER_LOCATION_EVIDENCE',
            verified_locations,'Source place mentions never grant regional authority'),
       item(7,'Electoral topic labels','SAVED_AI_TOPIC_EVIDENCE'
            if total_topics else 'NEEDS_SAVED_AI_TOPICS',total_topics,
            'Keyword topic hints are separate'),
       item(8,'Exact duplicate grouping',group_state('EXACT_DUPLICATE'),
            candidate_counts['EXACT_DUPLICATE'],
            'Exact duplicates can include unassessed posts'),
       item(9,'Emerging Narratives',group_state('NARRATIVE_CANDIDATE'),
            candidate_counts['NARRATIVE_CANDIDATE'],
            'Independent sources and officer review required'),
       item(10,'Five intelligence players','PROVISIONAL_PLAYER_EVIDENCE'
            if total_players else 'NEEDS_SAVED_PLAYER_EVIDENCE',total_players,
            'No entry is automatically verified'),
       item(11,'Needs Attention','PROVISIONAL_TRIAGE_EVIDENCE'
            if players.get('Needs Attention',{}).get('count') else
            'NO_SAVED_ISSUE_OR_FLAG_FOR_TRIAGE',
            players.get('Needs Attention',{}).get('count') or 0,
            'Human flag or saved issue required'),
       item(12,'AI player summaries','SAVED_DRAFT_EVIDENCE'
            if draft_count else 'NEEDS_SAVED_AI_SUMMARIES',draft_count,
            'Drafts need verbatim source quotes'),
       item(13,'Cross-module reuse','SAVED_ASSESSMENTS_AVAILABLE'
            if rows else 'NO_RELEVANT_SAVED_ASSESSMENTS',len(rows),
            'Reuses saved assessment versions'),
       item(14,'Shahrin classification accuracy','TARGET_NOT_MET',0,
            'Historical accuracy below target; human labels await signoff'),
       item(15,'Processing diagnostics','COVERAGE_AVAILABLE',
            coverage['authorized_posts'],'No paid requests or assumed zero cost'),
    ]
    return {'campaign_id':str(campaign.id),'campaign_name':campaign.name,
        'items':ledger,'linked_posts':coverage['linked_posts'],
        'authorized_posts':coverage['authorized_posts'],
        'relevant_posts':coverage['relevant_posts'],
        'unassessed_posts':coverage['unassessed_posts'],
        'group_proposals_by_type':candidate_counts,
        'saved_groups_count':len(saved),
        'officer_accepted_groups':sum(reviewed.values()),
        'assessment_window_truncated':relevant_truncated or duplicate_truncated,
        'does_not_record_formal_signoff':True,
        'engineering_acceptance_and_officer_signoff_are_distinct':True,
        'paid_provider_called':False,'socialcrawl_credits':0}
