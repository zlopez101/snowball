"""add onboarding and action log tables

Revision ID: d3e4f5a6b7c8
Revises: c1a2b3d4e5f6
Create Date: 2026-02-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM

# revision identifiers, used by Alembic.
revision: str = "d3e4f5a6b7c8"
down_revision: str | Sequence[str] | None = "c1a2b3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


visibility_mode_enum = ENUM(
    "PRIVATE",
    "COMMUNITY",
    "PUBLIC_OPT_IN",
    name="visibilitymode",
    create_type=False,
)
action_log_status_enum = ENUM(
    "COMPLETED",
    "SKIPPED",
    name="actionlogstatus",
    create_type=False,
)
action_outcome_enum = ENUM(
    "ANSWERED",
    "VOICEMAIL",
    "SENT",
    "ATTENDED",
    "UNKNOWN",
    name="actionoutcome",
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
            CREATE TYPE visibilitymode AS ENUM ('PRIVATE', 'COMMUNITY', 'PUBLIC_OPT_IN');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE actionlogstatus AS ENUM ('COMPLETED', 'SKIPPED');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            CREATE TYPE actionoutcome AS ENUM ('ANSWERED', 'VOICEMAIL', 'SENT', 'ATTENDED', 'UNKNOWN');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "userprofile",
        sa.Column("username", sa.String(length=50), nullable=False),
        sa.Column("state_code", sa.String(length=2), nullable=True),
        sa.Column("district_code", sa.String(length=10), nullable=True),
        sa.Column("timezone", sa.String(length=100), nullable=False),
        sa.Column("visibility_mode", visibility_mode_enum, nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )
    op.create_index(op.f("ix_userprofile_username"), "userprofile", ["username"], unique=True)

    op.create_table(
        "userprivacysettings",
        sa.Column("show_on_leaderboard", sa.Boolean(), nullable=False),
        sa.Column("show_streaks", sa.Boolean(), nullable=False),
        sa.Column("show_badges", sa.Boolean(), nullable=False),
        sa.Column("allow_shareable_card", sa.Boolean(), nullable=False),
        sa.Column("allow_referral_tracking", sa.Boolean(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("user_id"),
    )

    op.create_table(
        "dailyactionplan",
        sa.Column("target_actions_per_day", sa.Integer(), nullable=False),
        sa.Column("active_weekdays_mask", sa.String(length=7), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_dailyactionplan_user_id"), "dailyactionplan", ["user_id"], unique=False
    )
    op.create_index(
        op.f("ix_dailyactionplan_campaign_id"),
        "dailyactionplan",
        ["campaign_id"],
        unique=False,
    )

    op.create_table(
        "useractionlog",
        sa.Column("action_type", action_type_enum, nullable=False),
        sa.Column("status", action_log_status_enum, nullable=False),
        sa.Column("outcome", action_outcome_enum, nullable=False),
        sa.Column("confidence_score", sa.Integer(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("campaign_id", sa.Uuid(), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["campaign_id"], ["campaign.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_id"], ["representativetarget.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["actiontemplate.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_useractionlog_user_id"), "useractionlog", ["user_id"], unique=False)
    op.create_index(
        op.f("ix_useractionlog_campaign_id"), "useractionlog", ["campaign_id"], unique=False
    )
    op.create_index(
        op.f("ix_useractionlog_target_id"), "useractionlog", ["target_id"], unique=False
    )
    op.create_index(
        op.f("ix_useractionlog_template_id"), "useractionlog", ["template_id"], unique=False
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_useractionlog_template_id"), table_name="useractionlog")
    op.drop_index(op.f("ix_useractionlog_target_id"), table_name="useractionlog")
    op.drop_index(op.f("ix_useractionlog_campaign_id"), table_name="useractionlog")
    op.drop_index(op.f("ix_useractionlog_user_id"), table_name="useractionlog")
    op.drop_table("useractionlog")

    op.drop_index(op.f("ix_dailyactionplan_campaign_id"), table_name="dailyactionplan")
    op.drop_index(op.f("ix_dailyactionplan_user_id"), table_name="dailyactionplan")
    op.drop_table("dailyactionplan")

    op.drop_table("userprivacysettings")

    op.drop_index(op.f("ix_userprofile_username"), table_name="userprofile")
    op.drop_table("userprofile")

    op.execute("DROP TYPE IF EXISTS actionoutcome")
    op.execute("DROP TYPE IF EXISTS actionlogstatus")
    op.execute("DROP TYPE IF EXISTS visibilitymode")
