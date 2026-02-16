from sqlmodel import Session, create_engine, select

from app import crud
from app.core.config import settings
from app.models import (
    ActionTemplate,
    ActionType,
    Campaign,
    CampaignCreate,
    CampaignStatus,
    OfficeType,
    RepresentativeTarget,
    User,
    UserCreate,
)

engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI))


# make sure all SQLModel models are imported (app.models) before initializing DB
# otherwise, SQLModel might fail to initialize relationships properly
# for more details: https://github.com/fastapi/full-stack-fastapi-template/issues/28


def init_db(session: Session) -> None:
    # Tables should be created with Alembic migrations
    # But if you don't want to use migrations, create
    # the tables un-commenting the next lines
    # from sqlmodel import SQLModel

    # This works because the models are already imported and registered from app.models
    # SQLModel.metadata.create_all(engine)

    user = session.exec(
        select(User).where(User.email == settings.FIRST_SUPERUSER)
    ).first()
    if not user:
        user_in = UserCreate(
            email=settings.FIRST_SUPERUSER,
            password=settings.FIRST_SUPERUSER_PASSWORD,
            is_superuser=True,
        )
        user = crud.create_user(session=session, user_create=user_in)

    campaign = session.exec(
        select(Campaign).where(Campaign.slug == "defend-democracy-now")
    ).first()
    if campaign:
        return

    campaign = Campaign.model_validate(
        CampaignCreate(
            slug="defend-democracy-now",
            title="Defend Democracy Now",
            description=(
                "Daily constituent outreach campaign focused on protecting free and "
                "fair elections and voting rights."
            ),
            policy_topic="election-integrity",
            status=CampaignStatus.ACTIVE,
        )
    )
    session.add(campaign)
    session.commit()
    session.refresh(campaign)

    senate_target = RepresentativeTarget(
        campaign_id=campaign.id,
        office_type=OfficeType.SENATE,
        office_name="U.S. Senator (State Seat A)",
        state_code="TX",
        contact_phone="202-224-3121",
        contact_email="seat-a@example-senate.gov",
    )
    house_target = RepresentativeTarget(
        campaign_id=campaign.id,
        office_type=OfficeType.HOUSE,
        office_name="U.S. House Representative (District 01)",
        state_code="TX",
        district_code="01",
        contact_phone="202-225-3121",
        contact_email="district-01@example-house.gov",
    )
    session.add(senate_target)
    session.add(house_target)
    session.commit()
    session.refresh(senate_target)
    session.refresh(house_target)

    call_template = ActionTemplate(
        campaign_id=campaign.id,
        target_id=senate_target.id,
        action_type=ActionType.CALL,
        title="Call Script: Election Protections",
        script_text=(
            "Hello, I am a constituent asking for strong protections for voting "
            "access and election integrity. Please support upcoming legislation."
        ),
        estimated_minutes=3,
    )
    email_template = ActionTemplate(
        campaign_id=campaign.id,
        target_id=house_target.id,
        action_type=ActionType.EMAIL,
        title="Email Template: Protect Voting Rights",
        script_text=(
            "Use this template to send a concise message asking your representative "
            "to publicly support election protection legislation."
        ),
        email_subject="Constituent request: protect voting rights",
        email_body=(
            "I am your constituent and I urge you to support strong protections "
            "for voting rights and free and fair elections."
        ),
        estimated_minutes=4,
    )
    session.add(call_template)
    session.add(email_template)
    session.commit()
