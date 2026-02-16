"""add campaign foundation tables

Revision ID: c1a2b3d4e5f6
Revises: fe56fa70289e
Create Date: 2026-02-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = "c1a2b3d4e5f6"
down_revision: str | Sequence[str] | None = "fe56fa70289e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


campaign_status_enum = ENUM(
    "DRAFT",
    "ACTIVE",
    "PAUSED",
    "ARCHIVED",
    name="campaignstatus",
    create_type=False,
)
office_type_enum = ENUM(
    "SENATE",
    "HOUSE",
    "GOVERNOR",
    "INSTITUTION",
    name="officetype",
    create_type=False,
)
action_type_enum = ENUM(
    "CALL",
    "EMAIL",
    "BOYCOTT",
    "EVENT",
    name="actiontype",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE campaignstatus AS ENUM ('DRAFT', 'ACTIVE', 'PAUSED', 'ARCHIVED');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE officetype AS ENUM ('SENATE', 'HOUSE', 'GOVERNOR', 'INSTITUTION');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE actiontype AS ENUM ('CALL', 'EMAIL', 'BOYCOTT', 'EVENT');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "campaign",
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.String(length=4000), nullable=False),
        sa.Column("policy_topic", sa.String(length=100), nullable=False),
        sa.Column("status", campaign_status_enum, nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_campaign_slug"), "campaign", ["slug"], unique=True)

    op.create_table(
        "representativetarget",
        sa.Column("office_type", office_type_enum, nullable=False),
        sa.Column("office_name", sa.String(length=255), nullable=False),
        sa.Column("state_code", sa.String(length=2), nullable=True),
        sa.Column("district_code", sa.String(length=10), nullable=True),
        sa.Column("contact_phone", sa.String(length=30), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaign.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_representativetarget_campaign_id"),
        "representativetarget",
        ["campaign_id"],
        unique=False,
    )

    op.create_table(
        "actiontemplate",
        sa.Column("action_type", action_type_enum, nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("script_text", sa.String(length=10000), nullable=False),
        sa.Column("email_subject", sa.String(length=255), nullable=True),
        sa.Column("email_body", sa.String(length=10000), nullable=True),
        sa.Column("estimated_minutes", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["campaign_id"],
            ["campaign.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_id"],
            ["representativetarget.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_actiontemplate_campaign_id"),
        "actiontemplate",
        ["campaign_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_actiontemplate_target_id"),
        "actiontemplate",
        ["target_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_actiontemplate_target_id"), table_name="actiontemplate")
    op.drop_index(op.f("ix_actiontemplate_campaign_id"), table_name="actiontemplate")
    op.drop_table("actiontemplate")

    op.drop_index(
        op.f("ix_representativetarget_campaign_id"), table_name="representativetarget"
    )
    op.drop_table("representativetarget")

    op.drop_index(op.f("ix_campaign_slug"), table_name="campaign")
    op.drop_table("campaign")

    op.execute("DROP TYPE IF EXISTS actiontype")
    op.execute("DROP TYPE IF EXISTS officetype")
    op.execute("DROP TYPE IF EXISTS campaignstatus")
