# Snowball MVP Build Backlog

This document translates the project proposal into an implementation backlog for the current FastAPI full-stack template.

## Scope Baseline

- Product objective: validate that users will complete repeatable political actions, invite others, and respond to aggregate impact visibility.
- Success criteria (MVP):
- `>=35%` weekly active users complete at least 1 action/day for 3+ days in week 4.
- `>=0.6` average recruits per active user by week 6.
- `>=40%` of active users view impact dashboard at least 2 times/week.
- Non-goals (defer): robust public social graph, complex moderation automation, full SMS infrastructure.

## Architecture Decisions (MVP)

- Keep stack as-is: FastAPI + SQLModel + Postgres + React/TanStack.
- Keep auth flow from template, extend with verification and privacy settings.
- Replace generic `Item` workflow with `Campaign` and `ActionLog` workflows.
- Use aggregate-first analytics responses (no public per-action detail exposure).

## Proposed Data Model (Draft v1)

Add these models in `/Users/zachlopez/Documents/snowball/backend/app/models.py` and corresponding migrations.

1. `UserProfile`
- `user_id (FK user.id, PK)`
- `username (unique, indexed)`
- `state_code (nullable, char(2))`
- `district_code (nullable, string)`
- `timezone (default "America/Chicago")`
- `visibility_mode (enum: private, community, public_opt_in)`

2. `UserPrivacySettings`
- `user_id (FK user.id, PK)`
- `show_on_leaderboard (bool, default false)`
- `show_streaks (bool, default false)`
- `show_badges (bool, default true)`
- `allow_shareable_card (bool, default false)`
- `allow_referral_tracking (bool, default true)`

3. `Campaign`
- `id (uuid, PK)`
- `slug (unique, indexed)`
- `title`
- `description`
- `policy_topic` (e.g., voting-rights, gun-safety)
- `status (enum: draft, active, paused, archived)`
- `start_date`, `end_date (nullable)`
- `created_at`

4. `RepresentativeTarget`
- `id (uuid, PK)`
- `campaign_id (FK campaign.id, indexed)`
- `office_type (enum: senate, house, governor, institution)`
- `office_name`
- `state_code (nullable)`
- `district_code (nullable)`
- `contact_phone (nullable)`
- `contact_email (nullable)`
- `is_active (bool, default true)`

5. `ActionTemplate`
- `id (uuid, PK)`
- `campaign_id (FK campaign.id, indexed)`
- `target_id (FK representative_target.id, nullable)`
- `action_type (enum: call, email, boycott, event)`
- `title`
- `script_text`
- `email_subject (nullable)`
- `email_body (nullable)`
- `estimated_minutes (int, default 3)`

6. `UserActionLog`
- `id (uuid, PK)`
- `user_id (FK user.id, indexed)`
- `campaign_id (FK campaign.id, indexed)`
- `target_id (FK representative_target.id, nullable)`
- `template_id (FK action_template.id, nullable)`
- `action_type (enum: call, email, boycott, event)`
- `status (enum: completed, skipped)`
- `outcome (enum: answered, voicemail, sent, attended, unknown)`
- `confidence_score (int, 1-5, nullable)`
- `created_at (bucketed for display; exact timestamp not publicly exposed)`

7. `DailyActionPlan`
- `id (uuid, PK)`
- `user_id (FK user.id, indexed)`
- `campaign_id (FK campaign.id, indexed)`
- `target_actions_per_day (int, default 3)`
- `active_weekdays_mask (string, e.g. "1111100")`
- `is_active (bool, default true)`

8. `Referral`
- `id (uuid, PK)`
- `referrer_user_id (FK user.id, indexed)`
- `referred_user_id (FK user.id, unique, indexed)`
- `channel (enum: link, qr, social)`
- `created_at`

9. `BadgeDefinition`
- `id (uuid, PK)`
- `key (unique)` (e.g., `first_action`, `7_day_streak`)
- `name`
- `description`
- `criteria_json`

10. `UserBadge`
- `id (uuid, PK)`
- `user_id (FK user.id, indexed)`
- `badge_id (FK badge_definition.id, indexed)`
- `awarded_at`

11. `NotificationPreference`
- `user_id (FK user.id, PK)`
- `email_enabled (bool, default true)`
- `milestone_enabled (bool, default true)`
- `reminder_enabled (bool, default true)`
- `digest_frequency (enum: daily, weekly, off)`
- `quiet_hours_start`, `quiet_hours_end` (nullable)

12. `ForumPost` (MVP-lite)
- `id (uuid, PK)`
- `campaign_id (FK campaign.id, indexed)`
- `author_user_id (FK user.id, indexed)`
- `title`
- `body`
- `score (int, default 0)`
- `status (enum: active, removed)`
- `created_at`

13. `ForumVote`
- `id (uuid, PK)`
- `post_id (FK forum_post.id, indexed)`
- `user_id (FK user.id, indexed)`
- `vote (enum: up, down)`
- unique index on `(post_id, user_id)`

14. `ForumReport`
- `id (uuid, PK)`
- `post_id (FK forum_post.id, indexed)`
- `reporter_user_id (FK user.id, indexed)`
- `reason`
- `status (enum: open, reviewed, dismissed)`
- `created_at`

## API Contract (MVP Endpoints)

Add new routers under `/Users/zachlopez/Documents/snowball/backend/app/api/routes/`.

1. Onboarding and profile
- `POST /onboarding/complete`
- `GET /profile/me`
- `PATCH /profile/me`
- `GET /privacy/me`
- `PATCH /privacy/me`

2. Campaigns and templates
- `GET /campaigns?status=active&topic=...`
- `GET /campaigns/{campaign_id}`
- `GET /campaigns/{campaign_id}/targets`
- `GET /campaigns/{campaign_id}/templates`

3. Daily plan and action logging
- `GET /actions/today`
- `POST /actions/log`
- `GET /actions/me?from=YYYY-MM-DD&to=YYYY-MM-DD`
- `GET /actions/me/stats?window=7d`

4. Impact dashboards
- `GET /impact/platform?window=7d`
- `GET /impact/campaign/{campaign_id}?window=30d`
- `GET /impact/representative/{target_id}?window=30d`
- `GET /impact/me/share-card?window=7d`

5. Referrals and assists
- `POST /referrals/link`
- `POST /referrals/claim`
- `GET /referrals/me`
- `GET /referrals/me/assists?window=7d`

6. Gamification and leaderboard
- `GET /leaderboard?window=7d&scope=community`
- `GET /badges/me`
- `GET /streaks/me`

7. Notifications
- `GET /notifications/preferences`
- `PATCH /notifications/preferences`
- `POST /notifications/test`

8. Forum (optional in MVP, feature flag)
- `GET /forum/posts?campaign_id=...`
- `POST /forum/posts`
- `POST /forum/posts/{post_id}/vote`
- `POST /forum/posts/{post_id}/report`

## Frontend Route Map (Replace Template Pages)

Refactor routes under `/Users/zachlopez/Documents/snowball/frontend/src/routes/`.

1. `/_layout/` -> Home dashboard (personal + aggregate summary)
2. `/_layout/actions` -> daily checklist + quick logging
3. `/_layout/campaigns` -> campaign explorer + scripts/templates
4. `/_layout/impact` -> charts and shareable cards
5. `/_layout/referrals` -> invite links, QR, assist metrics
6. `/_layout/community` -> forum (feature flagged)
7. `/_layout/settings` -> privacy + notification controls
8. Remove or repurpose `/_layout/items` and `/_layout/admin`

Update sidebar in `/Users/zachlopez/Documents/snowball/frontend/src/components/Sidebar/AppSidebar.tsx`.

## Prioritized Ticket Backlog

## P0 (Must Ship for MVP Validation)

1. `P0-01` Domain schema migration
- Replace `Item` dependency in business flows.
- Add core tables: `Campaign`, `RepresentativeTarget`, `ActionTemplate`, `UserActionLog`, `Referral`, `UserPrivacySettings`.
- Deliverable: Alembic migrations + seed script.

2. `P0-02` Action logging API
- Build `GET /actions/today`, `POST /actions/log`, `GET /actions/me/stats`.
- Include action outcome and confidence.
- Add rate limiting for logs.

3. `P0-03` Campaign API
- Build campaign list/details + template retrieval.
- Seed at least 2 campaigns and 3 representative targets each.

4. `P0-04` Privacy controls
- Build privacy settings endpoints and enforce response-level redaction.
- Default all users to private mode.

5. `P0-05` Dashboard v1
- Personal metrics: streak, completed actions this week, campaign progress.
- Aggregate metrics: platform totals and campaign totals.

6. `P0-06` Referral attribution
- Generate referral links, claim flow on signup, assists rollup metric.

7. `P0-07` Onboarding flow
- Username + state/district + privacy selection + campaign selection + daily plan.

8. `P0-08` QA gates
- Backend API tests for action logging/privacy/referrals.
- Frontend e2e: signup -> onboarding -> log action -> view impact.

## P1 (Should Ship Soon After MVP Launch)

1. `P1-01` Badges and streak engine
2. `P1-02` Leaderboard (opt-in only)
3. `P1-03` Shareable impact cards export
4. `P1-04` Reminder emails and milestone emails
5. `P1-05` Admin campaign management screens
6. `P1-06` Verification hardening (email verify gate before action logging)

## P2 (Later / V2)

1. `P2-01` Forum + moderation queue
2. `P2-02` Geographic organizer roles and validation workflow
3. `P2-03` SMS/WhatsApp channel support
4. `P2-04` External integrations (Action Network sync)
5. `P2-05` Advanced anti-abuse anomaly detection

## Sprint Plan (6 x 1-week sprints)

1. Sprint 1: Foundations
- `P0-01`, `P0-03` (core models, migrations, seed data, base routers)
- Exit criteria: campaign and template APIs return seeded data.

2. Sprint 2: Action loop
- `P0-02`, `P0-07` backend + frontend initial screens.
- Exit criteria: user can complete onboarding and log one action.

3. Sprint 3: Impact and privacy
- `P0-04`, `P0-05`
- Exit criteria: dashboard shows personal + aggregate stats with privacy-safe output.

4. Sprint 4: Growth loop
- `P0-06` + basic invite UI + attribution tests.
- Exit criteria: recruiter sees assist stats from at least one referred signup.

5. Sprint 5: Stabilization
- `P0-08`, bug fixes, perf tuning, production checklist.
- Exit criteria: CI green on backend tests + e2e critical paths.

6. Sprint 6: Engagement layer
- `P1-01`, `P1-02`, `P1-04` (minimal implementations).
- Exit criteria: badges and reminders running for pilot cohort.

## Detailed Implementation Mapping

1. Backend files
- `/Users/zachlopez/Documents/snowball/backend/app/models.py`: add new models and public schemas.
- `/Users/zachlopez/Documents/snowball/backend/app/api/main.py`: register new routers.
- `/Users/zachlopez/Documents/snowball/backend/app/api/routes/`: add `campaigns.py`, `actions.py`, `impact.py`, `privacy.py`, `referrals.py`, `notifications.py`, `onboarding.py`.
- `/Users/zachlopez/Documents/snowball/backend/app/crud.py`: split by domain modules or expand with action/campaign/referral methods.
- `/Users/zachlopez/Documents/snowball/backend/app/initial_data.py`: seed campaigns/targets/templates.

2. Frontend files
- `/Users/zachlopez/Documents/snowball/frontend/src/components/Sidebar/AppSidebar.tsx`: replace nav items.
- `/Users/zachlopez/Documents/snowball/frontend/src/routes/_layout/index.tsx`: replace dashboard.
- `/Users/zachlopez/Documents/snowball/frontend/src/routes/_layout/actions.tsx`: new.
- `/Users/zachlopez/Documents/snowball/frontend/src/routes/_layout/campaigns.tsx`: new.
- `/Users/zachlopez/Documents/snowball/frontend/src/routes/_layout/impact.tsx`: new.
- `/Users/zachlopez/Documents/snowball/frontend/src/routes/_layout/referrals.tsx`: new.
- `/Users/zachlopez/Documents/snowball/frontend/src/routes/_layout/settings.tsx`: privacy + notifications.

3. Test coverage targets
- `/Users/zachlopez/Documents/snowball/backend/tests/api/routes/`: add route tests for campaigns/actions/impact/referrals/privacy.
- `/Users/zachlopez/Documents/snowball/frontend/tests/`: add e2e for onboarding/action logging/impact/referrals.

## Risks and Mitigations

1. Self-reported action integrity risk
- Mitigation: behavioral rate limits, anomaly detection rules, confidence/outcome metadata, random auditing prompts.

2. Privacy trust risk
- Mitigation: strict private defaults, aggregate-only public data, no public user directory, redaction checks in tests.

3. Scope creep risk (forum/admin complexity)
- Mitigation: forum behind feature flag; ship without it if P0 quality is at risk.

4. Data model churn risk
- Mitigation: freeze MVP schema after sprint 2 and use additive migrations only.

## Definition of Done (MVP)

- User can sign up, complete onboarding, and set a daily action plan.
- User can complete and log calls/emails with minimal friction.
- Dashboard shows personal and aggregate impact metrics with privacy-safe defaults.
- Referral link produces measurable assists.
- Core API and e2e tests pass in CI.
