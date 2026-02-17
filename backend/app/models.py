import uuid
from datetime import datetime, timezone
from enum import Enum

from pydantic import EmailStr
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel


def get_datetime_utc() -> datetime:
    return datetime.now(timezone.utc)


# Shared properties
class UserBase(SQLModel):
    email: EmailStr = Field(unique=True, index=True, max_length=255)
    is_active: bool = True
    is_superuser: bool = False
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on creation
class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserRegister(SQLModel):
    email: EmailStr = Field(max_length=255)
    password: str = Field(min_length=8, max_length=128)
    full_name: str | None = Field(default=None, max_length=255)


# Properties to receive via API on update, all are optional
class UserUpdate(UserBase):
    email: EmailStr | None = Field(default=None, max_length=255)  # type: ignore
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserUpdateMe(SQLModel):
    full_name: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = Field(default=None, max_length=255)


class UpdatePassword(SQLModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


# Database model, database table inferred from class name
class User(UserBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    hashed_password: str
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    items: list["Item"] = Relationship(back_populates="owner", cascade_delete=True)


# Properties to return via API, id is always required
class UserPublic(UserBase):
    id: uuid.UUID
    created_at: datetime | None = None


class UsersPublic(SQLModel):
    data: list[UserPublic]
    count: int


# Shared properties
class ItemBase(SQLModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=255)


# Properties to receive on item creation
class ItemCreate(ItemBase):
    pass


# Properties to receive on item update
class ItemUpdate(ItemBase):
    title: str | None = Field(default=None, min_length=1, max_length=255)  # type: ignore


# Database model, database table inferred from class name
class Item(ItemBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )
    owner_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE"
    )
    owner: User | None = Relationship(back_populates="items")


# Properties to return via API, id is always required
class ItemPublic(ItemBase):
    id: uuid.UUID
    owner_id: uuid.UUID
    created_at: datetime | None = None


class ItemsPublic(SQLModel):
    data: list[ItemPublic]
    count: int


class CampaignStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class OfficeType(str, Enum):
    SENATE = "senate"
    HOUSE = "house"
    GOVERNOR = "governor"
    INSTITUTION = "institution"


class ActionType(str, Enum):
    CALL = "call"
    EMAIL = "email"
    BOYCOTT = "boycott"
    EVENT = "event"


class ReferralChannel(str, Enum):
    LINK = "link"
    QR = "qr"
    SOCIAL = "social"


class VisibilityMode(str, Enum):
    PRIVATE = "private"
    COMMUNITY = "community"
    PUBLIC_OPT_IN = "public_opt_in"


class ActionLogStatus(str, Enum):
    COMPLETED = "completed"
    SKIPPED = "skipped"


class ActionOutcome(str, Enum):
    ANSWERED = "answered"
    VOICEMAIL = "voicemail"
    SENT = "sent"
    ATTENDED = "attended"
    UNKNOWN = "unknown"


class CampaignBase(SQLModel):
    slug: str = Field(unique=True, index=True, min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=4000)
    policy_topic: str = Field(min_length=1, max_length=100)
    status: CampaignStatus = CampaignStatus.DRAFT


class CampaignCreate(CampaignBase):
    pass


class Campaign(CampaignBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class CampaignPublic(CampaignBase):
    id: uuid.UUID
    created_at: datetime | None = None


class CampaignsPublic(SQLModel):
    data: list[CampaignPublic]
    count: int


class RepresentativeTargetBase(SQLModel):
    office_type: OfficeType
    office_name: str = Field(min_length=1, max_length=255)
    state_code: str | None = Field(default=None, min_length=2, max_length=2)
    district_code: str | None = Field(default=None, max_length=10)
    contact_phone: str | None = Field(default=None, max_length=30)
    contact_email: EmailStr | None = Field(default=None, max_length=255)
    is_active: bool = True


class RepresentativeTargetCreate(RepresentativeTargetBase):
    campaign_id: uuid.UUID


class RepresentativeTarget(RepresentativeTargetBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: uuid.UUID = Field(
        foreign_key="campaign.id", nullable=False, ondelete="CASCADE", index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class RepresentativeTargetPublic(RepresentativeTargetBase):
    id: uuid.UUID
    campaign_id: uuid.UUID
    created_at: datetime | None = None


class RepresentativeTargetsPublic(SQLModel):
    data: list[RepresentativeTargetPublic]
    count: int


class ActionTemplateBase(SQLModel):
    action_type: ActionType
    title: str = Field(min_length=1, max_length=255)
    script_text: str = Field(min_length=1, max_length=10000)
    email_subject: str | None = Field(default=None, max_length=255)
    email_body: str | None = Field(default=None, max_length=10000)
    estimated_minutes: int = Field(default=3, ge=1, le=60)


class ActionTemplateCreate(ActionTemplateBase):
    campaign_id: uuid.UUID
    target_id: uuid.UUID | None = None


class ActionTemplate(ActionTemplateBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    campaign_id: uuid.UUID = Field(
        foreign_key="campaign.id", nullable=False, ondelete="CASCADE", index=True
    )
    target_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="representativetarget.id",
        nullable=True,
        ondelete="SET NULL",
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ActionTemplatePublic(ActionTemplateBase):
    id: uuid.UUID
    campaign_id: uuid.UUID
    target_id: uuid.UUID | None = None
    created_at: datetime | None = None


class ActionTemplatesPublic(SQLModel):
    data: list[ActionTemplatePublic]
    count: int


class UserProfileBase(SQLModel):
    username: str = Field(unique=True, index=True, min_length=3, max_length=50)
    state_code: str | None = Field(default=None, min_length=2, max_length=2)
    district_code: str | None = Field(default=None, max_length=10)
    timezone: str = Field(default="America/Chicago", min_length=2, max_length=100)
    visibility_mode: VisibilityMode = VisibilityMode.PRIVATE


class UserProfileCreate(UserProfileBase):
    user_id: uuid.UUID


class UserProfileUpdate(SQLModel):
    username: str | None = Field(default=None, min_length=3, max_length=50)
    state_code: str | None = Field(default=None, min_length=2, max_length=2)
    district_code: str | None = Field(default=None, max_length=10)
    timezone: str | None = Field(default=None, min_length=2, max_length=100)
    visibility_mode: VisibilityMode | None = None


class UserProfile(UserProfileBase, table=True):
    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, nullable=False, ondelete="CASCADE"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UserProfilePublic(UserProfileBase):
    user_id: uuid.UUID
    created_at: datetime | None = None


class UserPrivacySettingsBase(SQLModel):
    show_on_leaderboard: bool = False
    show_streaks: bool = False
    show_badges: bool = True
    allow_shareable_card: bool = False
    allow_referral_tracking: bool = True


class UserPrivacySettingsUpdate(SQLModel):
    show_on_leaderboard: bool | None = None
    show_streaks: bool | None = None
    show_badges: bool | None = None
    allow_shareable_card: bool | None = None
    allow_referral_tracking: bool | None = None


class UserPrivacySettings(UserPrivacySettingsBase, table=True):
    user_id: uuid.UUID = Field(
        foreign_key="user.id", primary_key=True, nullable=False, ondelete="CASCADE"
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UserPrivacySettingsPublic(UserPrivacySettingsBase):
    user_id: uuid.UUID
    created_at: datetime | None = None


class DailyActionPlanBase(SQLModel):
    target_actions_per_day: int = Field(default=3, ge=1, le=20)
    active_weekdays_mask: str = Field(default="1111100", min_length=7, max_length=7)
    is_active: bool = True


class DailyActionPlanCreate(DailyActionPlanBase):
    user_id: uuid.UUID
    campaign_id: uuid.UUID


class DailyActionPlan(DailyActionPlanBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    campaign_id: uuid.UUID = Field(
        foreign_key="campaign.id", nullable=False, ondelete="CASCADE", index=True
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class DailyActionPlanPublic(DailyActionPlanBase):
    id: uuid.UUID
    user_id: uuid.UUID
    campaign_id: uuid.UUID
    created_at: datetime | None = None


class UserActionLogBase(SQLModel):
    campaign_id: uuid.UUID
    target_id: uuid.UUID | None = None
    template_id: uuid.UUID | None = None
    action_type: ActionType
    status: ActionLogStatus
    outcome: ActionOutcome = ActionOutcome.UNKNOWN
    confidence_score: int | None = Field(default=None, ge=1, le=5)


class UserActionLogCreate(UserActionLogBase):
    pass


class UserActionLog(UserActionLogBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    campaign_id: uuid.UUID = Field(
        foreign_key="campaign.id", nullable=False, ondelete="CASCADE", index=True
    )
    target_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="representativetarget.id",
        nullable=True,
        ondelete="SET NULL",
        index=True,
    )
    template_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="actiontemplate.id",
        nullable=True,
        ondelete="SET NULL",
        index=True,
    )
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class UserActionLogPublic(UserActionLogBase):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime | None = None


class UserActionLogsPublic(SQLModel):
    data: list[UserActionLogPublic]
    count: int


class TodayActionPublic(SQLModel):
    campaign_id: uuid.UUID
    campaign_title: str
    template_id: uuid.UUID
    target_id: uuid.UUID | None = None
    action_type: ActionType
    title: str
    estimated_minutes: int


class TodayActionsPublic(SQLModel):
    data: list[TodayActionPublic]
    count: int


class ActionStatsPublic(SQLModel):
    window_days: int
    total_actions: int
    completed_actions: int
    skipped_actions: int
    calls: int
    emails: int
    boycotts: int
    events: int
    last_action_at: datetime | None = None


class ImpactPublic(SQLModel):
    window_days: int
    total_actions: int
    completed_actions: int
    skipped_actions: int
    calls: int
    emails: int
    boycotts: int
    events: int
    unique_participants: int
    participant_range: str
    last_action_at: datetime | None = None
    campaign_id: uuid.UUID | None = None
    campaign_title: str | None = None


class ImpactShareCardPublic(SQLModel):
    window_days: int
    shareable: bool
    visibility_mode: VisibilityMode
    display_name: str | None = None
    period_label: str
    total_actions: int
    completed_actions: int
    calls: int
    emails: int
    message: str


class ReferralLinkCreate(SQLModel):
    channel: ReferralChannel = ReferralChannel.LINK


class ReferralClaimCreate(SQLModel):
    code: str = Field(min_length=6, max_length=64)


class Referral(SQLModel, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    referrer_user_id: uuid.UUID = Field(
        foreign_key="user.id", nullable=False, ondelete="CASCADE", index=True
    )
    referred_user_id: uuid.UUID | None = Field(
        default=None,
        foreign_key="user.id",
        nullable=True,
        ondelete="SET NULL",
        index=True,
        unique=True,
    )
    code: str = Field(min_length=6, max_length=64, unique=True, index=True)
    channel: ReferralChannel = ReferralChannel.LINK
    created_at: datetime | None = Field(
        default_factory=get_datetime_utc,
        sa_type=DateTime(timezone=True),  # type: ignore
    )


class ReferralPublic(SQLModel):
    id: uuid.UUID
    referrer_user_id: uuid.UUID
    referred_user_id: uuid.UUID | None = None
    code: str
    channel: ReferralChannel
    invite_url: str
    created_at: datetime | None = None


class ReferralsPublic(SQLModel):
    data: list[ReferralPublic]
    count: int


class ReferralAssistsPublic(SQLModel):
    window_days: int
    recruited_users: int
    assisted_actions: int


class OnboardingComplete(SQLModel):
    username: str = Field(min_length=3, max_length=50)
    state_code: str | None = Field(default=None, min_length=2, max_length=2)
    district_code: str | None = Field(default=None, max_length=10)
    timezone: str = Field(default="America/Chicago", min_length=2, max_length=100)
    visibility_mode: VisibilityMode = VisibilityMode.PRIVATE
    campaign_ids: list[uuid.UUID] = Field(default_factory=list)
    target_actions_per_day: int = Field(default=3, ge=1, le=20)
    active_weekdays_mask: str = Field(default="1111100", min_length=7, max_length=7)


class OnboardingCompletePublic(SQLModel):
    profile: UserProfilePublic
    privacy: UserPrivacySettingsPublic
    daily_plans_count: int


# Generic message
class Message(SQLModel):
    message: str


# JSON payload containing access token
class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"


# Contents of JWT token
class TokenPayload(SQLModel):
    sub: str | None = None


class NewPassword(SQLModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)
