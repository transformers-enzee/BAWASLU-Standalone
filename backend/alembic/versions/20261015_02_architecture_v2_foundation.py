"""Architecture v2 foundation - additive, legacy-data-safe tables.

Revision ID: 20261015_02
Revises: 20260930_01
This migration creates new tables only. It does not alter or delete legacy rows.
"""
from alembic import op
import sqlalchemy as sa

revision='20261015_02'
down_revision='20260930_01'
branch_labels=None
depends_on=None

def upgrade():
    bind=op.get_bind()
    existing=set(sa.inspect(bind).get_table_names())
    if 'issue_category_phrases' not in existing:
        op.create_table('issue_category_phrases',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('category_id',sa.Integer(),sa.ForeignKey('issue_categories.id'),nullable=False),
            sa.Column('phrase',sa.String(160),nullable=False),
            sa.Column('normalized_phrase',sa.String(160),nullable=False),
            sa.Column('active',sa.Boolean(),nullable=False),
            sa.Column('created_at',sa.DateTime(),nullable=False),
            sa.Column('updated_at',sa.DateTime(),nullable=False),
            sa.UniqueConstraint('category_id','normalized_phrase',name='uq_issue_category_phrase'))
        op.create_index('ix_issue_category_phrases_category_id','issue_category_phrases',['category_id'])
    if 'monitoring_campaigns' not in existing:
        op.create_table('monitoring_campaigns',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('name',sa.String(255),nullable=False),
            sa.Column('description',sa.Text(),nullable=False),
            sa.Column('primary_keywords_json',sa.Text(),nullable=False),
            sa.Column('secondary_keywords_json',sa.Text(),nullable=False),
            sa.Column('excluded_keywords_json',sa.Text(),nullable=False),
            sa.Column('platforms_json',sa.Text(),nullable=False),
            sa.Column('language',sa.String(32),nullable=False),
            sa.Column('date_from',sa.String(32),nullable=False),
            sa.Column('date_to',sa.String(32),nullable=False),
            sa.Column('province',sa.String(128),nullable=False),
            sa.Column('regency_city',sa.String(128),nullable=False),
            sa.Column('status',sa.String(24),nullable=False),
            sa.Column('interval_minutes',sa.Integer(),nullable=False),
            sa.Column('next_run_at',sa.DateTime(),nullable=True),
            sa.Column('last_success_at',sa.DateTime(),nullable=True),
            sa.Column('created_by',sa.String(128),nullable=False),
            sa.Column('created_at',sa.DateTime(),nullable=False),
            sa.Column('updated_at',sa.DateTime(),nullable=False))
        for col in ('name','created_by','next_run_at'):
            op.create_index('ix_monitoring_campaigns_'+col,'monitoring_campaigns',[col])
    if 'campaign_runs' not in existing:
        op.create_table('campaign_runs',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('campaign_id',sa.Integer(),sa.ForeignKey('monitoring_campaigns.id'),nullable=False),
            sa.Column('social_listening_run_id',sa.Integer(),sa.ForeignKey('social_listening_runs.id'),nullable=False,unique=True),
            sa.Column('triggered_by',sa.String(32),nullable=False),
            sa.Column('created_at',sa.DateTime(),nullable=False))
        op.create_index('ix_campaign_runs_campaign_id','campaign_runs',['campaign_id'])
    if 'campaign_evidence' not in existing:
        op.create_table('campaign_evidence',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('campaign_id',sa.Integer(),sa.ForeignKey('monitoring_campaigns.id'),nullable=False),
            sa.Column('result_id',sa.Integer(),sa.ForeignKey('social_listening_results.id'),nullable=False),
            sa.Column('match_method',sa.String(48),nullable=False),
            sa.Column('matched_fields_json',sa.Text(),nullable=False),
            sa.Column('added_at',sa.DateTime(),nullable=False),
            sa.UniqueConstraint('campaign_id','result_id',name='uq_campaign_evidence'))
        op.create_index('ix_campaign_evidence_campaign_id','campaign_evidence',['campaign_id'])
        op.create_index('ix_campaign_evidence_result_id','campaign_evidence',['result_id'])
    if 'evidence_assessments' not in existing:
        op.create_table('evidence_assessments',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('campaign_id',sa.Integer(),sa.ForeignKey('monitoring_campaigns.id'),nullable=False),
            sa.Column('result_id',sa.Integer(),sa.ForeignKey('social_listening_results.id'),nullable=False),
            sa.Column('assessment_version',sa.Integer(),nullable=False),
            sa.Column('model_version',sa.String(100),nullable=False),
            sa.Column('relevance_label',sa.String(32),nullable=False),
            sa.Column('relevance_confidence',sa.String(32),nullable=False),
            sa.Column('sentiment',sa.String(32),nullable=False),
            sa.Column('candidate_signals_json',sa.Text(),nullable=False),
            sa.Column('geographic_signals_json',sa.Text(),nullable=False),
            sa.Column('potential_issue_signals_json',sa.Text(),nullable=False),
            sa.Column('explanation',sa.Text(),nullable=False),
            sa.Column('created_at',sa.DateTime(),nullable=False),
            sa.UniqueConstraint('campaign_id','result_id','assessment_version',name='uq_evidence_assessment_version'))
        op.create_index('ix_evidence_assessments_campaign_id','evidence_assessments',['campaign_id'])
        op.create_index('ix_evidence_assessments_result_id','evidence_assessments',['result_id'])
    if 'evidence_reviews' not in existing:
        op.create_table('evidence_reviews',
            sa.Column('id',sa.Integer(),primary_key=True),
            sa.Column('assessment_id',sa.Integer(),sa.ForeignKey('evidence_assessments.id'),nullable=False),
            sa.Column('reviewer_id',sa.String(128),nullable=False),
            sa.Column('decision',sa.String(40),nullable=False),
            sa.Column('rationale',sa.Text(),nullable=False),
            sa.Column('created_at',sa.DateTime(),nullable=False))
        op.create_index('ix_evidence_reviews_assessment_id','evidence_reviews',['assessment_id'])
        op.create_index('ix_evidence_reviews_reviewer_id','evidence_reviews',['reviewer_id'])

def downgrade():
    # Do not silently delete campaign, evidence, assessments or audit history.
    raise RuntimeError('Architecture v2 rollback requires an approved backup/restore procedure; automatic downgrade is deliberately disabled.')
