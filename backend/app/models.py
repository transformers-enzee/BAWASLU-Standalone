from datetime import datetime
from sqlalchemy import String, Text, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base

class User(Base):
    __tablename__='users'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255), default='')
    password_hash: Mapped[str] = mapped_column(Text)
    platform_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SessionToken(Base):
    __tablename__='session_tokens'
    token: Mapped[str] = mapped_column(String(128), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AccessGrant(Base):
    __tablename__='access_grants'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), unique=True, index=True)
    access_role: Mapped[str] = mapped_column(String(100), default='Viewer')
    province: Mapped[str] = mapped_column(String(128), default='')
    regency_city: Mapped[str] = mapped_column(String(128), default='')
    geographic_scope: Mapped[str] = mapped_column(String(32), default='Province')
    permissions_json: Mapped[str] = mapped_column(Text, default='{}')
    status: Mapped[str] = mapped_column(String(20), default='Active')
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class IntelligenceItem(Base):
    __tablename__='intelligence_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True, index=True)
    intelligence_id: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    title: Mapped[str] = mapped_column(Text, default='')
    original_content: Mapped[str] = mapped_column(Text, default='')
    original_language: Mapped[str] = mapped_column(String(100), default='')
    original_language_code: Mapped[str] = mapped_column(String(20), default='')
    english_translation: Mapped[str] = mapped_column(Text, default='')
    future_indonesian_translation: Mapped[str] = mapped_column(Text, default='')
    ai_summary: Mapped[str] = mapped_column(Text, default='')
    ai_analysis: Mapped[str] = mapped_column(Text, default='')
    ai_suggestions_json: Mapped[str] = mapped_column(Text, default='{}')
    ai_geography_json: Mapped[str] = mapped_column(Text, default='{}')
    proposed_geography_json: Mapped[str] = mapped_column(Text, default='{}')
    geographic_mismatch_review_json: Mapped[str] = mapped_column(Text, default='{}')
    source_type: Mapped[str] = mapped_column(String(64), default='')
    ingestion_method: Mapped[str] = mapped_column(String(64), default='MANUAL_ENTRY')
    observed_publisher_handle: Mapped[str] = mapped_column(String(255), default='')
    provider_source_metadata_json: Mapped[str] = mapped_column(Text, default='{}')
    source_identity_json: Mapped[str] = mapped_column(Text, default='{}')
    entity_relationships_json: Mapped[str] = mapped_column(Text, default='[]')
    source_id: Mapped[str] = mapped_column(String(255), default='')
    source_url: Mapped[str] = mapped_column(Text, default='')
    source_name: Mapped[str] = mapped_column(String(255), default='')
    platform: Mapped[str] = mapped_column(String(100), default='')
    author: Mapped[str] = mapped_column(String(255), default='')
    publication_datetime: Mapped[str] = mapped_column(String(64), default='')
    publication_date: Mapped[str] = mapped_column(String(32), default='')
    publication_time_precision: Mapped[str] = mapped_column(String(32), default='UNKNOWN')
    collection_datetime: Mapped[str] = mapped_column(String(64), default='')
    owned_channel_json: Mapped[str] = mapped_column(Text, default='{}')
    related_entities_json: Mapped[str] = mapped_column(Text, default='[]')
    related_topics_json: Mapped[str] = mapped_column(Text, default='[]')
    jurisdiction_type: Mapped[str] = mapped_column(String(32), default='Unresolved')
    jurisdiction_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    jurisdiction_confirmed_by: Mapped[str] = mapped_column(String(255), default='')
    jurisdiction_confirmed_at: Mapped[str] = mapped_column(String(64), default='')
    jurisdiction_source: Mapped[str] = mapped_column(String(128), default='')
    province: Mapped[str] = mapped_column(String(128), default='')
    regency_city: Mapped[str] = mapped_column(String(128), default='')
    province_code: Mapped[str] = mapped_column(String(32), default='')
    regency_city_code: Mapped[str] = mapped_column(String(32), default='')
    geographic_assignments_json: Mapped[str] = mapped_column(Text, default='[]')
    location_text: Mapped[str] = mapped_column(Text, default='')
    potential_issue_category: Mapped[str] = mapped_column(String(255), default='')
    analyst_notes: Mapped[str] = mapped_column(Text, default='')
    reason: Mapped[str] = mapped_column(Text, default='')
    evidence_state: Mapped[str] = mapped_column(String(32), default='UNVERIFIED')
    evidence_type: Mapped[str] = mapped_column(String(32), default='OBSERVED')
    verification_status: Mapped[str] = mapped_column(String(32), default='UNVERIFIED')
    intelligence_extraction_json: Mapped[str] = mapped_column(Text, default='{}')
    supervision_screening_json: Mapped[str] = mapped_column(Text, default='{}')
    review_status: Mapped[str] = mapped_column(String(128), default='Pending Review')
    confidence: Mapped[str] = mapped_column(String(64), default='')
    priority: Mapped[str] = mapped_column(String(64), default='Medium')
    assigned_reviewer: Mapped[str] = mapped_column(String(255), default='')
    review_notes: Mapped[str] = mapped_column(Text, default='')
    validated_at: Mapped[str] = mapped_column(String(64), default='')
    duplicate_of: Mapped[str] = mapped_column(String(255), default='')
    duplicate_resolution: Mapped[str] = mapped_column(String(64), default='')
    merged_into: Mapped[str] = mapped_column(String(255), default='')
    watchlist_id: Mapped[str] = mapped_column(String(255), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class IntelligenceSequence(Base):
    __tablename__='intelligence_sequences'
    year: Mapped[int] = mapped_column(Integer, primary_key=True)
    sequence: Mapped[int] = mapped_column(Integer, default=0)

class WatchlistItem(Base):
    __tablename__='watchlist_items'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    type: Mapped[str] = mapped_column(String(100), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    province: Mapped[str] = mapped_column(String(128), default='')
    regency_city: Mapped[str] = mapped_column(String(128), default='')
    related_election: Mapped[str] = mapped_column(String(255), default='')
    related_entity: Mapped[str] = mapped_column(String(255), default='')
    related_topics_json: Mapped[str] = mapped_column(Text, default='[]')
    priority: Mapped[str] = mapped_column(String(64), default='Medium')
    status: Mapped[str] = mapped_column(String(64), default='Active')
    notes: Mapped[str] = mapped_column(Text, default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SourceAccount(Base):
    __tablename__='source_accounts'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    watchlist_id: Mapped[int] = mapped_column(ForeignKey('watchlist_items.id'), index=True)
    platform: Mapped[str] = mapped_column(String(100), default='')
    url: Mapped[str] = mapped_column(Text)
    handle: Mapped[str] = mapped_column(String(255), default='')
    province: Mapped[str] = mapped_column(String(128), default='')
    regency_city: Mapped[str] = mapped_column(String(128), default='')

class EntityRelationship(Base):
    __tablename__='entity_relationships'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    from_id: Mapped[int] = mapped_column(ForeignKey('watchlist_items.id'), index=True)
    to_id: Mapped[int] = mapped_column(ForeignKey('watchlist_items.id'), index=True)
    relationship_type: Mapped[str] = mapped_column(String(128))
    province: Mapped[str] = mapped_column(String(128), default='')

class TriageGeneration(Base):
    __tablename__='triage_generations'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    triage_run_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    intelligence_item_id: Mapped[int|None] = mapped_column(ForeignKey('intelligence_items.id'), nullable=True, index=True)
    initiated_by_id: Mapped[str] = mapped_column(String(128), default='')
    source_fingerprint: Mapped[str] = mapped_column(String(128), default='')
    proposal_fingerprint: Mapped[str] = mapped_column(String(128), default='')
    triage_schema_version: Mapped[int] = mapped_column(Integer, default=3)
    generator: Mapped[str] = mapped_column(String(128), default='')
    generator_version: Mapped[str] = mapped_column(String(128), default='')
    service_action: Mapped[str] = mapped_column(String(128), default='')
    attempt_started_at: Mapped[str] = mapped_column(String(64), default='')
    attempt_ended_at: Mapped[str] = mapped_column(String(64), default='')
    generated_at: Mapped[str] = mapped_column(String(64), default='')
    validation_outcome: Mapped[str] = mapped_column(String(32), default='PENDING')
    rejected_fields_json: Mapped[str] = mapped_column(Text, default='[]')
    proposal_field_names_json: Mapped[str] = mapped_column(Text, default='[]')

class EvidenceFile(Base):
    __tablename__='evidence_files'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    intelligence_item_id: Mapped[int] = mapped_column(ForeignKey('intelligence_items.id'), index=True)
    file_uri: Mapped[str] = mapped_column(Text)
    original_filename: Mapped[str] = mapped_column(String(500))
    file_type: Mapped[str] = mapped_column(String(32), default='')
    uploaded_by: Mapped[str] = mapped_column(String(255), default='')
    uploaded_at: Mapped[str] = mapped_column(String(64), default='')
    related_entity: Mapped[str] = mapped_column(String(255), default='')
    related_location: Mapped[str] = mapped_column(String(255), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    evidence_state: Mapped[str] = mapped_column(String(32), default='UNVERIFIED')

class IssueCategory(Base):
    __tablename__='issue_categories'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

class DataSource(Base):
    __tablename__='data_sources'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str] = mapped_column(String(255), default='')
    source_type: Mapped[str] = mapped_column(String(100), default='')
    description: Mapped[str] = mapped_column(Text, default='')
    status: Mapped[str] = mapped_column(String(64), default='Active')
    province: Mapped[str] = mapped_column(String(128), default='')
    regency_city: Mapped[str] = mapped_column(String(128), default='')

class ExternalDataConnector(Base):
    __tablename__='external_data_connectors'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    connector_id: Mapped[str] = mapped_column(String(255), unique=True)
    provider_name: Mapped[str] = mapped_column(String(255), default='')
    connector_type: Mapped[str] = mapped_column(String(128), default='')
    status: Mapped[str] = mapped_column(String(64), default='DISABLED')
    supported_sources_json: Mapped[str] = mapped_column(Text, default='[]')
    configuration_json: Mapped[str] = mapped_column(Text, default='{}')
    last_sync: Mapped[str] = mapped_column(String(64), default='')
    health_status: Mapped[str] = mapped_column(String(64), default='')

class AuditEvent(Base):
    __tablename__='audit_events'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    external_id: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    subject_type: Mapped[str] = mapped_column(String(128), index=True)
    subject_id: Mapped[str] = mapped_column(String(255), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    actor_id: Mapped[str] = mapped_column(String(128), default='system')
    actor_name: Mapped[str] = mapped_column(String(255), default='system')
    changes_json: Mapped[str] = mapped_column(Text, default='{}')
    occurred_at: Mapped[str] = mapped_column(String(64), default='')

class MigrationBatch(Base):
    __tablename__='migration_batches'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_label: Mapped[str] = mapped_column(String(255), default='base44')
    dry_run: Mapped[bool] = mapped_column(Boolean, default=True)
    status: Mapped[str] = mapped_column(String(32), default='staged')
    record_count: Mapped[int] = mapped_column(Integer, default=0)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    summary_json: Mapped[str] = mapped_column(Text, default='{}')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class MigrationStagingRecord(Base):
    __tablename__='migration_staging_records'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey('migration_batches.id'), index=True)
    source_entity: Mapped[str] = mapped_column(String(128))
    source_record_id: Mapped[str] = mapped_column(String(255), default='')
    target_kind: Mapped[str] = mapped_column(String(128))
    payload_json: Mapped[str] = mapped_column(Text)
    validation_status: Mapped[str] = mapped_column(String(32), default='pending')
    validation_errors_json: Mapped[str] = mapped_column(Text, default='[]')
    committed_entity_id: Mapped[str] = mapped_column(String(128), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    __table_args__=(UniqueConstraint('batch_id','source_entity','source_record_id',name='uq_migration_record'),)

class SocialListeningRule(Base):
    __tablename__='social_listening_rules'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text, default='')
    provider: Mapped[str] = mapped_column(String(64), default='SOCIALCRAWL')
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    filters_json: Mapped[str] = mapped_column(Text, default='{}')
    created_by: Mapped[str] = mapped_column(String(128), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SocialListeningRun(Base):
    __tablename__='social_listening_runs'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    rule_id: Mapped[int|None] = mapped_column(ForeignKey('social_listening_rules.id'), nullable=True, index=True)
    provider: Mapped[str] = mapped_column(String(64), default='SOCIALCRAWL')
    query_json: Mapped[str] = mapped_column(Text, default='{}')
    provider_request_id: Mapped[str] = mapped_column(String(255), default='')
    credits_used: Mapped[int] = mapped_column(Integer, default=0)
    credits_remaining: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default='COMPLETED')
    error_text: Mapped[str] = mapped_column(Text, default='')
    executed_by: Mapped[str] = mapped_column(String(128), default='')
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SocialListeningResult(Base):
    __tablename__='social_listening_results'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    run_id: Mapped[int] = mapped_column(ForeignKey('social_listening_runs.id'), index=True)
    provider: Mapped[str] = mapped_column(String(64), default='SOCIALCRAWL')
    provider_result_id: Mapped[str] = mapped_column(String(255), default='', index=True)
    platform: Mapped[str] = mapped_column(String(100), default='')
    content_type: Mapped[str] = mapped_column(String(100), default='')
    canonical_url: Mapped[str] = mapped_column(Text, default='')
    author_name: Mapped[str] = mapped_column(String(255), default='')
    observed_handle: Mapped[str] = mapped_column(String(255), default='')
    published_at: Mapped[str] = mapped_column(String(64), default='')
    text_content: Mapped[str] = mapped_column(Text, default='')
    language: Mapped[str] = mapped_column(String(32), default='')
    relevance_score: Mapped[str] = mapped_column(String(32), default='')
    engagement_json: Mapped[str] = mapped_column(Text, default='{}')
    geography_json: Mapped[str] = mapped_column(Text, default='{}')
    source_identity_json: Mapped[str] = mapped_column(Text, default='{}')
    watchlist_matches_json: Mapped[str] = mapped_column(Text, default='[]')
    review_state: Mapped[str] = mapped_column(String(32), default='DISCOVERED')
    review_notes: Mapped[str] = mapped_column(Text, default='')
    promoted_intelligence_id: Mapped[int|None] = mapped_column(ForeignKey('intelligence_items.id'), nullable=True, index=True)
    raw_payload_json: Mapped[str] = mapped_column(Text, default='{}')
    content_fingerprint: Mapped[str] = mapped_column(String(128), default='', index=True)
    collected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class SocialListeningProviderUsage(Base):
    __tablename__='social_listening_provider_usage'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    provider: Mapped[str] = mapped_column(String(64), default='SOCIALCRAWL')
    endpoint: Mapped[str] = mapped_column(String(255), default='')
    provider_request_id: Mapped[str] = mapped_column(String(255), default='')
    credits_used: Mapped[int] = mapped_column(Integer, default=0)
    credits_remaining: Mapped[int] = mapped_column(Integer, default=0)
    cached: Mapped[bool] = mapped_column(Boolean, default=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0)
    user_id: Mapped[str] = mapped_column(String(128), default='')
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
