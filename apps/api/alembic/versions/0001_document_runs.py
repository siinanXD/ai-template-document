"""document_runs

Revision ID: 0001
Revises:
Create Date: 2026-08-30
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "document_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("document_type", sa.String(length=64), nullable=True),
        sa.Column("reference_number", sa.String(length=128), nullable=True),
        sa.Column("extracted_date", sa.String(length=32), nullable=True),
        sa.Column("amount", sa.Float(), nullable=True),
        sa.Column("currency", sa.String(length=8), nullable=True),
        sa.Column("company_name", sa.String(length=256), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("requires_review", sa.Boolean(), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("estimated_cost_usd", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_document_runs_file_hash", "document_runs", ["file_hash"])


def downgrade() -> None:
    op.drop_index("ix_document_runs_file_hash", table_name="document_runs")
    op.drop_table("document_runs")
