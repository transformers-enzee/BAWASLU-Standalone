"""Audited national/provincial case routing and report review.

Revision ID: 20261105_01
Revises: 20261029_05
"""
from alembic import op
import sqlalchemy as sa

revision="20261105_01"
down_revision="20261029_05"
branch_labels=None
depends_on=None

def upgrade():
    inspect=sa.inspect(op.get_bind())
    names=set(inspect.get_table_names())
    if "case_assignments" not in names:
        op.create_table("case_assignments",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("title",sa.String(240),nullable=False),
            sa.Column("source_type",sa.String(24),nullable=False),
            sa.Column("source_id",sa.String(72),nullable=False),
            sa.Column("campaign_id",sa.Integer(),nullable=True),
            sa.Column("source_url",sa.Text(),nullable=False,server_default=""),
            sa.Column("source_excerpt",sa.Text(),nullable=False,server_default=""),
            sa.Column("tags_json",sa.Text(),nullable=False,server_default="[]"),
            sa.Column("suggested_provinces_json",sa.Text(),nullable=False,server_default="[]"),
            sa.Column("verified_province",sa.String(128),nullable=False,server_default=""),
            sa.Column("originating_scope",sa.String(16),nullable=False),
            sa.Column("originating_province",sa.String(128),nullable=False,server_default=""),
            sa.Column("target_scope",sa.String(16),nullable=False),
            sa.Column("target_province",sa.String(128),nullable=False,server_default=""),
            sa.Column("target_department",sa.String(120),nullable=False),
            sa.Column("assignee_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=True),
            sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
            sa.Column("status",sa.String(32),nullable=False,server_default="OPEN"),
            sa.Column("notes",sa.Text(),nullable=False,server_default=""),
            sa.Column("created_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_case_assignments_target", "case_assignments",["target_scope","target_province","status"])
        op.create_index("ix_case_assignments_source", "case_assignments",["source_type","source_id"])
    if "case_transitions" not in names:
        op.create_table("case_transitions",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("case_id",sa.Integer(),sa.ForeignKey("case_assignments.id"),nullable=False),
            sa.Column("actor_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
            sa.Column("action",sa.String(48),nullable=False),
            sa.Column("details_json",sa.Text(),nullable=False,server_default="{}"),
            sa.Column("happened_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_case_transitions_case_id","case_transitions",["case_id"])
    if "case_reports" not in names:
        op.create_table("case_reports",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("case_id",sa.Integer(),sa.ForeignKey("case_assignments.id"),nullable=False),
            sa.Column("title",sa.String(240),nullable=False),
            sa.Column("executive_summary",sa.Text(),nullable=False,server_default=""),
            sa.Column("findings",sa.Text(),nullable=False,server_default=""),
            sa.Column("verification_notes",sa.Text(),nullable=False,server_default=""),
            sa.Column("recommendations",sa.Text(),nullable=False,server_default=""),
            sa.Column("source_snapshot_json",sa.Text(),nullable=False,server_default="{}"),
            sa.Column("status",sa.String(32),nullable=False,server_default="DRAFT"),
            sa.Column("created_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
            sa.Column("reviewed_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=True),
            sa.Column("review_comment",sa.Text(),nullable=False,server_default=""),
            sa.Column("created_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_case_reports_case_id","case_reports",["case_id"])
    if op.get_bind().dialect.name=="postgresql":
        for name in ("case_assignments","case_transitions","case_reports"):
            op.execute("ALTER TABLE "+name+" ENABLE ROW LEVEL SECURITY")
            op.execute("REVOKE ALL ON TABLE "+name+" FROM PUBLIC, anon, authenticated")
            op.execute("REVOKE ALL ON SEQUENCE "+name+"_id_seq FROM PUBLIC, anon, authenticated")

def downgrade():
    # Case histories should never be silently destroyed by application rollback.
    # Explicit data migration and governance approval required for removal.
    pass
