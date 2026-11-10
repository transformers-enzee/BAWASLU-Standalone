"""Hybrid private PDF search and officer document governance.

Revision ID: 20261110_02
Revises: 20261110_01
"""
from alembic import op
import sqlalchemy as sa

revision="20261110_02"
down_revision="20261110_01"
branch_labels=None
depends_on=None

def upgrade():
    connection=op.get_bind()
    # Supabase installs pgvector into extensions; never expose a privileged
    # document-search function to public Data API roles.
    if connection.dialect.name=="postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS vector WITH SCHEMA extensions")
    inspector=sa.inspect(connection)
    columns={col["name"] for col in inspector.get_columns("assistant_knowledge_pdfs")}
    additions=[
        ("document_type",sa.Column("document_type",sa.String(24),nullable=False,
                                   server_default="OTHER")),
        ("issuer",sa.Column("issuer",sa.String(220),nullable=False,server_default="")),
        ("review_status",sa.Column("review_status",sa.String(24),nullable=False,
                                  server_default="UNREVIEWED")),
        ("review_notes",sa.Column("review_notes",sa.Text(),nullable=False,server_default="")),
        ("reviewed_by",sa.Column("reviewed_by",sa.Integer(),nullable=True)),
        ("reviewed_at",sa.Column("reviewed_at",sa.DateTime(),nullable=True)),
        ("embedding_status",sa.Column("embedding_status",sa.String(24),
                                     nullable=False,server_default="NOT_INDEXED")),
        ("embedding_model",sa.Column("embedding_model",sa.String(64),
                                    nullable=False,server_default="")),
    ]
    for name,column in additions:
        if name not in columns:
            op.add_column("assistant_knowledge_pdfs",column)
    # Optional human review is recorded independently of upload.
    foreign_keys={key["name"] for key in sa.inspect(connection).get_foreign_keys(
        "assistant_knowledge_pdfs") if key.get("name")}
    if connection.dialect.name=="postgresql":
        op.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname='fk_assistant_pdf_reviewed_by'
                ) THEN
                    ALTER TABLE public.assistant_knowledge_pdfs
                    ADD CONSTRAINT fk_assistant_pdf_reviewed_by
                    FOREIGN KEY (reviewed_by) REFERENCES public.users(id);
                END IF;
            END $$;
        """)
        cols={col["name"] for col in sa.inspect(connection).get_columns(
            "assistant_knowledge_chunks")}
        if "embedding" not in cols:
            op.execute("""
                ALTER TABLE public.assistant_knowledge_chunks
                ADD COLUMN embedding extensions.vector(1536)
            """)
        op.execute("""
            CREATE INDEX IF NOT EXISTS ix_assistant_knowledge_embedding_cosine
            ON public.assistant_knowledge_chunks
            USING hnsw (embedding extensions.vector_cosine_ops)
            WHERE embedding IS NOT NULL
        """)
        for table in ("assistant_knowledge_pdfs","assistant_knowledge_chunks"):
            op.execute("ALTER TABLE public."+table+" ENABLE ROW LEVEL SECURITY")
            op.execute("REVOKE ALL ON TABLE public."+table+
                       " FROM PUBLIC, anon, authenticated")

def downgrade():
    # Preserve original documents, embedding indexes and review history.
    # Data removal must be a separately approved governance action.
    pass
