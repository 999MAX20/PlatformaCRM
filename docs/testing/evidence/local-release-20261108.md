# Local release candidate — 08 November 2026

Owner scope: prepare a coherent CRM candidate locally, alongside a separate Market form/draft fix. Preserve accumulated work; no deployment or publication. Canonical checkout remains `codex/ui-testing-toolkit` at `6a8af190b0701158b2a7b187547bf6ba1a2f5567`.

**State: local candidate packaged with explicit performance-gate gaps; not deployment-ready.** The owner approved restoring Task `relations` on 08 November. The proposed patch was applied, retaining all other CRM-card optimizations. Access checks pass. The archive contains an acceptance report that records two exceeded performance budgets; no thresholds were raised.

## Completed integration work

- Fixed the personal notification feed's rejection of current `/app/appointments/ID` links. The parser now recognizes the canonical record URL and sanitizes its output. Existing Business, membership, capability and current Appointment read scope still decide visibility before list/count/read operations. Legacy calendar links retain their behavior.
- Updated synthetic runtime checking to prove internal-feed visibility instead of pretending SYSTEM notifications are externally delivered. Updated transport regression fixtures to EMAIL with mocked providers. Task reminder tests prove one visible personal notification with no transport attempt.
- Aligned the existing mobile owner/manager smoke with the approved record-first navigation, current booking button and company settings section. No UI implementation was changed. Reachability, overflow, drawer/Escape and booking-dialog checks remain.
- Built the frontend with same-origin API configuration for eventual deployment, separately from the ephemeral-loopback quality-gate build.

The task-owned source patch and exact initial/current hashes cover ten files; the pre-existing edits in the notification test file and selector are preserved. The original source manifest, Git inventory and index hash remain intact. No staging, commit, push, CI, lock removal, working-DB change, provider activation or server action occurred.

## Evidence

All logs and machine-readable results are in `output/local-release-20261108/`.

| Check | Result and boundary |
| --- | --- |
| Original full Django run | 3075 tests; FAIL: 3 failures, 19 errors, 64 SQLite skips. This historical failure remains visible. |
| Restored card access | Original isolated reproduction had 13 errors across 12 tests. After the approved restoration: 12 PASS. Combined card/access/performance PostgreSQL run: 76 tests, 74 PASS and two performance-budget failures; no access failures or skips. |
| Notification and dependent suites after fixes | PostgreSQL: 145 PASS, zero skips; includes six new canonical-link/access regressions, transport, settings cancellation/revocation, task reminders, bot pipeline and notification migration/concurrency tests. System and migration drift PASS. |
| Initial PostgreSQL boundaries | 29 PASS for changed scheduling/branch/import/voice/personal-feed boundaries. |
| Other SQLite-skipped checks | 53 PASS on PostgreSQL. Together with the selected concurrency cases in the 29-test run, every one of the original 64 skips has PostgreSQL evidence. |
| Frontend | Gate environment, types/i18n/build and bundle PASS; final mobile owner/manager smoke 2 PASS. Separate same-origin build PASS. |
| Dependencies | Both Python lock installability dry-runs, pip-audit and npm moderate audit PASS. Existing installation reused; lock inputs unchanged. |
| Source preservation | Own patch reconstructed against exact initial hashes; unrelated source unchanged. Git index preserved. Final source/runtime manifests identify the candidate; neither manifest certifies deployment. |

The first notification recheck exposed the previously untested canonical-link rejection. The two new-test setup mistakes (required appointment fixtures, then pre-created capability) were corrected; the final 145-test PostgreSQL run includes those tests. The initial browser run expected retired Leads navigation; follow-ups exposed old booking-button and settings-heading selectors. Final smoke passes on current approved UI. Logs of these failed attempts were retained.

## Candidate composition and release limits

The initial 06 November server manifest is only a baseline: the server subsequently received separate security, SMTP, internal-feed and landing overlays. Offline comparison confirms the saved SMTP/internal-feed replacement blocks remain present. Four security-overlay files are byte-identical; differences in the other two are the existing initial-location initialization, expired-token schedule and Sentry privacy helper. The original full suite passed their relevant tests. All 112 landing payload files match the saved deployed archive by content: 35 byte-identical, 77 differ only in line endings.

No claim is made about the currently stopped server. Four pre-existing release acceptance items remain outside this local packet: live/server smoke, broader browser acceptance, recorded restore acceptance and support access. Voice/pilot/load and money milestones are not closed by these checks.

The candidate includes four already-existing new migrations versus the initial deployment: `bots.0014`, `integrations.0009`, `branches.0003` and `scheduling.0012`. Existing migration files were not changed. Applying them to working/server data remains outside this task. Before any eventual deployment, obtain current server state and backup, compare the composed release, and perform the separately authorized release procedure.

## Approved restoration and performance comparison

The owner authorized applying the proposed patch, checking access/performance and producing a local archive. `crm_cards.py` now serializes tasks through the existing `TaskSerializer`, preserving request actor and the rest of the pre-existing query/projection optimizations. The combined PostgreSQL run covers task-preview context, core cards, CRM projection access, client PII projections and B301 performance; system/migration drift also pass.

Two required gates remain **FAIL**, without changing their limits:

- Representative card response: **152,195 bytes**, budget **150,000**.
- Maximum SQL text: **15,068 characters**, budget **15,000**. Increasing related rows from60 to300 keeps this length unchanged and increases query count only36→37.

A separate PostgreSQL comparison uses identical fixtures and changes only the old omission of `relations` in memory, without modifying source files. Before/restored: **36/36 queries**, **15,011/15,011 maximum SQL characters**, **139,328/150,762 response bytes**. The additional **11,434 bytes** are exactly the restored relations; every other response field is identical. This proves the SQL-budget overage exists before this patch and that restored required data increases payload. It does not waive either gate or certify production latency/capacity.

Logs: `card-restored-focused.log`, `card-restored-dependent-postgres.log`, `card-comparison.log`; exact measurements: `card-same-fixture-comparison.json`. Historical failed checks remain present. Unaffected earlier PASS results are reused, not reported as a fresh green full-project run.

## Local artifact

`output/local-release-20261108/crm-candidate-20261108.tar.gz` contains the runtime payload, same-origin frontend build, `RELEASE-MANIFEST.json`, `RELEASE-ACCEPTANCE.json` and `RELEASE-README.txt`. The companion `.sha256` and `archive-verification.json` record its checksum and complete member/hash verification. No secrets, environment files, working databases, media or caches are packaged. The build is an accumulated canonical snapshot, not a committed/published release.

The local packaging request is complete. Remaining release work: resolve or explicitly revise the two measured performance budgets under the product's acceptance rules, then complete the pre-existing live/server acceptance separately. No deployment, migration of working data, Git staging/commit/push or CI run was performed.
