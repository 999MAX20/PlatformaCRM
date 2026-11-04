# C11 — export attempt ownership

Owner «продолжаем» authorizes C11 EXPORT-STALE-FINISH only, not C12/C26.
Canonical PlatformaCRM/current codex/ui-testing-toolkit/base080da13450c91113f2ed292af48f21ffc383d0a9;
233 foreign WIP retained. core/export_jobs.py, models.py and migration target clean.
Code gap: stale worker may overwrite newer terminal state and publish obsolete file.
Reuse ExportJob, claim/reclaim, private storage, current permission/fingerprint checks.
UUID claim token per attempt; success/failure conditional on current RUNNING token;
unique attempt filenames, delete only unpublished output owned by losing attempt.
No new retry policy, row-count/limits fix (C26), UI, permissions, queues or providers.
Nullable internal token migration; existing rows retain null until next claim.
Only disposable DB migrations; workingDB/dev remain unchanged/off. No live storage.
Focused BEFORE/AFTER stale success/failure/retry and cleanup after save/DB failure;
real PG interleaved attempts. Affected export/access/history suites, system/drift,
isolated migration preservation and API download of winning bytes. No full-project.
Update integrations/operations/passport/evidence/plan; own local commit, no push/deploy.
