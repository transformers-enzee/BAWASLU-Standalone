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
    from .summary_readiness import validated_summary_buckets
    summary_buckets=[validated_summary_buckets(x) for x in rows]
    development_count=sum(bool(x['development']) for x in summary_buckets)
    pipeline_count=sum(bool(x['pipeline']) for x in summary_buckets)
    unattributed_count=sum(bool(x['unattributed']) for x in summary_buckets)
    draft_count=sum(bool(any(x.values())) for x in summary_buckets)
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
        if coverage['unassessed_posts'] or relevant_truncated or duplicate_truncated:
            return 'ASSESSMENT_COVERAGE_INCOMPLETE'
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
       item(12,'AI player summaries',
            'PIPELINE_DRAFTS_PENDING_HUMAN_REVIEW' if pipeline_count else
            'DEVELOPMENT_SAMPLES_NOT_PIPELINE_ACCEPTANCE' if development_count else
            'UNTAGGED_LEGACY_DRAFTS_NOT_PIPELINE_VERIFIED' if unattributed_count else
            'NEEDS_SAVED_AI_SUMMARIES',draft_count,
            'Only source-fingerprinted pipeline drafts count as pipeline evidence; no automatic officer acceptance'),
       item(13,'Cross-module reuse','SOCIAL_SOURCE_CONTRACT_READY_PILOT_CROSSWALK_UNVERIFIED'
            if rows else 'NO_RELEVANT_SAVED_ASSESSMENTS',len(rows),
            'Inbox/Watchlist canonical social source reuse verified; independent Radar pilot IDs have no verified crosswalk'),
       item(14,'Shahrin classification accuracy','TARGET_NOT_MET',0,
            'Historical accuracy below target; human labels await signoff'),
       item(15,'Processing diagnostics','COVERAGE_AVAILABLE',
            coverage['authorized_posts'],'No paid requests or assumed zero cost'),
    ]
    # One explicit release-level acceptance matrix for Batch 1. This is
    # evidence readiness, never an implied human signoff.
    batch1={
      '6': {'workflow_tested':True,
            'production_state':'OFFICER_VERIFIED' if verified_locations else 'REVIEW_REQUIRED',
            'officer_accepted':bool(verified_locations),
            'blocker':None if verified_locations else 'No independently officer-confirmed incident geography'},
      '8': {'workflow_tested':True,
            'production_state':'OFFICER_REVIEWED' if reviewed['EXACT_DUPLICATE']
                else 'SAVED_PENDING_REVIEW' if stored['EXACT_DUPLICATE']
                else 'PROPOSAL_READY' if candidate_counts['EXACT_DUPLICATE']
                else 'NO_EXACT_DUPLICATE_EVIDENCE',
            'officer_accepted':bool(reviewed['EXACT_DUPLICATE']),
            'blocker':None if reviewed['EXACT_DUPLICATE'] else
                'Officer acceptance of saved duplicate evidence not recorded'},
      '9': {'workflow_tested':True,
            'production_state':group_state('NARRATIVE_CANDIDATE'),
            'officer_accepted':bool(reviewed['NARRATIVE_CANDIDATE']),
            'blocker':None if reviewed['NARRATIVE_CANDIDATE'] else
                'Independent-source narrative evidence and officer decision not complete'},
      '11':{'workflow_tested':True,
            'production_state':'SAVED_TRIAGE_EVIDENCE' if players.get('Needs Attention',{}).get('count')
                else 'NO_QUALIFYING_SAVED_TRIAGE',
            'officer_accepted':False,
            'blocker':'Saved attention candidates are not independent officer triage approval'
                if players.get('Needs Attention',{}).get('count') else
                'No qualifying saved Needs Attention evidence to verify positive production path'}
    }
    # Next actions are honest evidence gates, not inferred DONE statuses.
    next_actions=[]
    if candidate_counts['EXACT_DUPLICATE'] and not stored['EXACT_DUPLICATE']:
        next_actions.append({'item':8,'kind':'OFFICER_WORKFLOW',
            'status':'READY_FOR_OFFICER_TO_SAVE',
            'instruction':'Inspect the exact duplicate source texts; save the provisional group and record an independent officer decision.',
            'source_groups':candidate_counts['EXACT_DUPLICATE'],
            'permission_required':'review_ai_suggestions'})
    elif stored['EXACT_DUPLICATE'] and not reviewed['EXACT_DUPLICATE']:
        next_actions.append({'item':8,'kind':'OFFICER_WORKFLOW',
            'status':'PENDING_OFFICER_REVIEW',
            'instruction':'Inspect the saved duplicate source records before accepting or rejecting.',
            'source_groups':stored['EXACT_DUPLICATE'],
            'permission_required':'human_validation'})
    if candidate_counts['NARRATIVE_CANDIDATE'] and not reviewed['NARRATIVE_CANDIDATE']:
        next_actions.append({'item':9,'kind':'OFFICER_WORKFLOW',
            'status':'READY_FOR_REVIEW' if stored['NARRATIVE_CANDIDATE'] else 'READY_FOR_OFFICER_TO_SAVE',
            'instruction':'Inspect recurring independent sources and determine if they truly form a narrative.',
            'source_groups':candidate_counts['NARRATIVE_CANDIDATE'],
            'permission_required':'human_validation'})
    elif not candidate_counts['NARRATIVE_CANDIDATE']:
        incomplete=bool(coverage['unassessed_posts'] or relevant_truncated or duplicate_truncated)
        next_actions.append({'item':9,'kind':'DATA_DEPENDENCY',
            'status':'ASSESSMENT_COVERAGE_INCOMPLETE' if incomplete else 'NO_QUALIFYING_NARRATIVE_SOURCES',
            'instruction':('Finish or disposition unassessed posts before calling absence of narratives conclusive.' if incomplete else
                           'No qualifying recent independent-source narrative in the assessed evidence; do not fabricate one.'),
            'source_groups':0})
    if not pipeline_count:
        next_actions.append({'item':12,'kind':'PAID_AI_DEPENDENCY',
            'status':('DEVELOPMENT_SAMPLES_NOT_PIPELINE_ACCEPTANCE' if development_count
                      else 'LEGACY_DRAFT_PROVENANCE_UNVERIFIED' if unattributed_count
                      else 'NO_SAVED_AI_SUMMARIES'),
            'instruction':'Run a small explicitly authorized production-pipeline sample; development and untagged legacy drafts cannot establish pipeline acceptance.',
            'source_groups':0})
    else:
        next_actions.append({'item':12,'kind':'OFFICER_WORKFLOW',
            'status':'PIPELINE_SUMMARIES_PENDING_HUMAN_QA',
            'instruction':'Independently verify source quotes and summary accuracy; pipeline output alone is not signoff.',
            'source_groups':pipeline_count,'permission_required':'human_validation'})
    if not verified_locations:
        next_actions.append({'item':6,'kind':'OFFICER_WORKFLOW',
            'status':'JURISDICTION_REVIEW_REQUIRED',
            'instruction':'Only confirm incident geography after checking explicit source context; never derive it from profile location.',
            'source_groups':0,'permission_required':'human_validation'})
    if not players.get('Needs Attention',{}).get('count'):
        next_actions.append({'item':11,'kind':'EVIDENCE_DEPENDENCY',
            'status':'NO_QUALIFYING_ATTENTION_EVIDENCE',
            'instruction':'Keep urgency unassigned until supported saved signals or officer follow-up warrant triage.',
            'source_groups':0})
    next_actions.append({'item':13,'kind':'SOURCE_IDENTITY_DEPENDENCY',
        'status':'PILOT_CROSSWALK_UNVERIFIED',
        'instruction':'Confirm persisted source identity before reusing Social Listening assessments in separate Radar pilot records; canonical social IDs are already supported.',
        'source_groups':0})
    next_actions.append({'item':14,'kind':'QA_AND_HUMAN_DEPENDENCY',
        'status':'REFERENCE_SIGNOFF_AND_MEASURED_EVALUATION_REQUIRED',
        'instruction':'An analyst must reconcile reference labels; the unvalidated V18 draft requires a separate authorized measured test.',
        'source_groups':0})
    return {'campaign_id':str(campaign.id),'campaign_name':campaign.name,
        'batch1_acceptance':batch1,
        'batch1_all_officer_accepted':all(row['officer_accepted'] for row in batch1.values()),
        'batch1_paid_provider_called':False,
        'next_actions':next_actions,
        'fully_completed_items_not_inferred':True,
        'items':ledger,'linked_posts':coverage['linked_posts'],
        'authorized_posts':coverage['authorized_posts'],
        'relevant_posts':coverage['relevant_posts'],
        'unassessed_posts':coverage['unassessed_posts'],
        'group_proposals_by_type':candidate_counts,
        'summary_evidence':{'development_only_posts':development_count,
            'pipeline_posts':pipeline_count,'legacy_unattributed_posts':unattributed_count,
            'no_officer_summary_approval_inferred':True},
        'saved_groups_count':len(saved),
        'officer_accepted_groups':sum(reviewed.values()),
        'assessment_window_truncated':relevant_truncated or duplicate_truncated,
        'does_not_record_formal_signoff':True,
        'engineering_acceptance_and_officer_signoff_are_distinct':True,
        'paid_provider_called':False,'socialcrawl_credits':0}
