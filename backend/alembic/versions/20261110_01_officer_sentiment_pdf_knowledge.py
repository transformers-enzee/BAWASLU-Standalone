"""Human sentiment history and private PDF knowledge.

Revision ID: 20261110_01
Revises: 20261105_01
"""
from alembic import op
import sqlalchemy as sa

revision="20261110_01"
down_revision="20261105_01"
branch_labels=None
depends_on=None

def upgrade():
    conn=op.get_bind()
    names=set(sa.inspect(conn).get_table_names())
    if "officer_sentiment_corrections" not in names:
        op.create_table("officer_sentiment_corrections",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("campaign_id",sa.Integer(),sa.ForeignKey("monitoring_campaigns.id"),nullable=False),
            sa.Column("result_id",sa.Integer(),sa.ForeignKey("social_listening_results.id"),nullable=False),
            sa.Column("sentiment",sa.String(16),nullable=False),
            sa.Column("rationale",sa.Text(),nullable=False),
            sa.Column("actor_id",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
            sa.Column("created_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")))
        op.create_index("ix_sentiment_correction_campaign_result","officer_sentiment_corrections",
                        ["campaign_id","result_id","id"])
    if "assistant_knowledge_pdfs" not in names:
        op.create_table("assistant_knowledge_pdfs",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("title",sa.String(240),nullable=False),
            sa.Column("filename",sa.String(220),nullable=False),
            sa.Column("scope",sa.String(20),nullable=False),
            sa.Column("province",sa.String(128),nullable=False,server_default=""),
            sa.Column("content_sha256",sa.String(64),nullable=False),
            sa.Column("content_bytes",sa.LargeBinary(),nullable=False),
            sa.Column("pages",sa.Integer(),nullable=False),
            sa.Column("extracted_chars",sa.Integer(),nullable=False),
            sa.Column("uploaded_by",sa.Integer(),sa.ForeignKey("users.id"),nullable=False),
            sa.Column("uploaded_at",sa.DateTime(),nullable=False,server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("active",sa.Boolean(),nullable=False,server_default=sa.text("TRUE")))
        op.create_index("ix_assistant_pdf_digest","assistant_knowledge_pdfs",["content_sha256"])
    if "assistant_knowledge_chunks" not in names:
        op.create_table("assistant_knowledge_chunks",
            sa.Column("id",sa.Integer(),primary_key=True,autoincrement=True),
            sa.Column("document_id",sa.Integer(),sa.ForeignKey("assistant_knowledge_pdfs.id"),nullable=False),
            sa.Column("page",sa.Integer(),nullable=False),
            sa.Column("sequence",sa.Integer(),nullable=False),
            sa.Column("text_content",sa.Text(),nullable=False))
        op.create_index("ix_assistant_knowledge_chunks_doc","assistant_knowledge_chunks",["document_id","page"])
    if conn.dialect.name=="postgresql":
        for table in ("officer_sentiment_corrections","assistant_knowledge_pdfs",
                      "assistant_knowledge_chunks"):
            op.execute("ALTER TABLE "+table+" ENABLE ROW LEVEL SECURITY")
            op.execute("REVOKE ALL ON TABLE "+table+" FROM PUBLIC, anon, authenticated")
            op.execute("REVOKE ALL ON SEQUENCE "+table+"_id_seq FROM PUBLIC, anon, authenticated")

def downgrade():
    # Knowledge evidence and signed officer corrections must not be dropped
    # automatically on application rollback.
    pass
