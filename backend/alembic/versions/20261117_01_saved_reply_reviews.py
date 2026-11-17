"""Persistent Assistant review records. Revision ID: 20261117_01; Revises: 20261116_01."""
from alembic import op
import sqlalchemy as sa
revision="20261117_01"
down_revision="20261116_01"
branch_labels=None
depends_on=None

def upgrade():
 tables=set(sa.inspect(op.get_bind()).get_table_names())
 if "assistant_saved_reply_reviews" not in tables:
  op.create_table("assistant_saved_reply_reviews",
   sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
   sa.Column("owner_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
   sa.Column("thread_id",sa.String(36),nullable=False),
   sa.Column("answer_message_index",sa.Integer(),nullable=False),
   sa.Column("reply_fingerprint",sa.String(64),nullable=False),
   sa.Column("review_state",sa.String(60),nullable=False),
   sa.Column("evidence_checked",sa.Boolean(),nullable=False),
   sa.Column("reviewer_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
   sa.Column("review_route",sa.String(80),nullable=False),
   sa.Column("version",sa.Integer(),nullable=False),
   sa.Column("created_at",sa.DateTime(),server_default=sa.text("CURRENT_TIMESTAMP"),nullable=False),
   sa.Column("updated_at",sa.DateTime(),server_default=sa.text("CURRENT_TIMESTAMP"),nullable=False),
   sa.UniqueConstraint("owner_id","thread_id","answer_message_index",name="uq_saved_reply_review_owner_turn"))
  op.create_index("ix_saved_review_owner","assistant_saved_reply_reviews",["owner_id"])
 if "assistant_saved_reply_review_events" not in tables:
  op.create_table("assistant_saved_reply_review_events",
   sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
   sa.Column("review_id",sa.Integer(),sa.ForeignKey("assistant_saved_reply_reviews.id"),nullable=False),
   sa.Column("actor_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
   sa.Column("from_state",sa.String(60),nullable=False),
   sa.Column("to_state",sa.String(60),nullable=False),
   sa.Column("version",sa.Integer(),nullable=False),
   sa.Column("at",sa.DateTime(),server_default=sa.text("CURRENT_TIMESTAMP"),nullable=False))
  op.create_index("ix_saved_review_events_review","assistant_saved_reply_review_events",["review_id"])
 if op.get_bind().dialect.name=="postgresql":
  for name in ("assistant_saved_reply_reviews","assistant_saved_reply_review_events"):
   op.execute("ALTER TABLE "+name+" ENABLE ROW LEVEL SECURITY")
   op.execute("REVOKE ALL ON TABLE "+name+" FROM PUBLIC, anon, authenticated")
   op.execute("REVOKE ALL ON SEQUENCE "+name+"_id_seq FROM PUBLIC, anon, authenticated")

def downgrade():
 pass
