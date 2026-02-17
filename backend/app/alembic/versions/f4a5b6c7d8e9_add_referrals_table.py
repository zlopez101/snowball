"""add referrals table

Revision ID: f4a5b6c7d8e9
Revises: d3e4f5a6b7c8
Create Date: 2026-02-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "f4a5b6c7d8e9"
down_revision: str | None = "d3e4f5a6b7c8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


referral_channel_enum = postgresql.ENUM(
    "LINK",
    "QR",
    "SOCIAL",
    name="referralchannel",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'referralchannel') THEN
                CREATE TYPE referralchannel AS ENUM ('LINK', 'QR', 'SOCIAL');
            END IF;
        END $$;
        """
    )
    op.create_table(
        "referral",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("referrer_user_id", sa.Uuid(), nullable=False),
        sa.Column("referred_user_id", sa.Uuid(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("channel", referral_channel_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["referrer_user_id"],
            ["user.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["referred_user_id"],
            ["user.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_referral_code"), "referral", ["code"], unique=True)
    op.create_index(
        op.f("ix_referral_referred_user_id"),
        "referral",
        ["referred_user_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_referral_referrer_user_id"),
        "referral",
        ["referrer_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_referral_referrer_user_id"), table_name="referral")
    op.drop_index(op.f("ix_referral_referred_user_id"), table_name="referral")
    op.drop_index(op.f("ix_referral_code"), table_name="referral")
    op.drop_table("referral")
    op.execute("DROP TYPE IF EXISTS referralchannel")
