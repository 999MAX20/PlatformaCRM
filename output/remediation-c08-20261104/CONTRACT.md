# C08 — current automatic booking terms

Owner «продолжпем» authorizes C08 only: CRM-TERMS01/BOT-ZERO-PRICE.
Canonical PlatformaCRM, codex/ui-testing-toolkit, base64e9f2ce8147001c3c99c1f87fab84d80e065531;
233 foreign WIP entries preserved. Booking/context/automatic test targets clean.
Behavior: a delivered offer binds price/duration; changed/missing terms cannot create
a new appointment or creation effects. Existing successful replay remains idempotent.
No-branch offers include terms; zero price stays explicit in AI context.
Reuse booking_terms/appointment_snapshot, Business transaction, automatic actor guards,
requires_staff/handoff and current caller contracts. No C09 effects/context redesign.
Risk: stale confirmation, branch/no-branch parity, null/zero, replay/permissions.
Focused BEFORE/AFTER tests per service slice; completion automatic booking/branch bot/
scheduling context and related service suites plus isolated system/migration checks.
Test actual pipeline with mocked AI/provider only; no live messages/models. No frontend
change or build required. Lock/recheck terms at appointment creation, preserve legacy
manual callers lacking expected fields; reject incomplete automatic offers safely.
No schema/env/permission policy changes, workingDB connection/write, push/merge/deploy.
Record evidence/contracts/passports/plan and own local commit after checks.
