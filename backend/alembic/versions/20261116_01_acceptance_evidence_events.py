"""Separate acceptance evidence submissions from casework and external signoff.

Revision ID: 20261116_01
Revises: 20261110_02
"""
from alembic import op
import sqlalchemy as sa

revision="20261116_01"
down_revision="20261110_02"
branch_labels=None
depends_on=None

def upgrade():
    tables=set(sa.inspect(op.get_bind()).get_table_names())
    if "assistant_acceptance_evidence" not in tables:
        op.create_table("assistant_acceptance_evidence",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("track",sa.String(64),nullable=False),
            sa.Column("reference",sa.String(160),nullable=False),
            sa.Column("submitted_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
            sa.Column("submitted_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_assistant_acceptance_evidence_track","assistant_acceptance_evidence",["track"])
    if "assistant_acceptance_evidence_events" not in tables:
        op.create_table("assistant_acceptance_evidence_events",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("evidence_id",sa.Integer(),sa.ForeignKey("assistant_acceptance_evidence.id"),nullable=False),
            sa.Column("actor_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
            sa.Column("action",sa.String(32),nullable=False),
            sa.Column("created_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_assistant_acceptance_evidence_events_evidence_id",
                        "assistant_acceptance_evidence_events",["evidence_id"])
    if op.get_bind().dialect.name=="postgresql":
        for table in ("assistant_acceptance_evidence","assistant_acceptance_evidence_events"):
            op.execute("ALTER TABLE "+table+" ENABLE ROW LEVEL SECURITY")
            op.execute("REVOKE ALL ON TABLE "+table+" FROM PUBLIC, anon, authenticated")
            op.execute("REVOKE ALL ON SEQUENCE "+table+"_id_seq FROM PUBLIC, anon, authenticated")

def downgrade():
    # Preserve signed or rejected review trails until explicitly governed removal.
    pass
