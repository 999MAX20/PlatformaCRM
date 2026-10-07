# AI-AGENT-ISOLATION-20261005

Owner-approved implementation: independent agent knowledge/settings, explicit shared
material connections, no legacy-profile fallback, retained deletion history.
Canonical root: `C:/Users/user/Desktop/PlatformaCRM`; branch
`codex/ui-testing-toolkit`, base HEAD `9ff366207e73472cda71ca3b9113ca4f9f305af9`.
Existing 145 dirty paths were retained; starting patch/status are in
`output/ai-agent-isolation-20261005`. This report covers the incremental change.

## Behavior and boundaries

- Knowledge belongs either to one agent or to the business shared library.
  An agent sees its own records plus explicitly connected shared records.
- Existing ownerless records stay in the shared library, with no automatic links.
  The editor creates private records and provides explicit connect/disconnect.
- API enforces business membership, existing permissions, immutable ownership,
  available agents and shared-only connections. Writes include transactional audit
  and activity; repeated connection requests are idempotent.
- Actual AI context and readiness use the same scoped selector. A changed knowledge
  context during provider execution rejects the stale answer. Unbound old profiles
  cannot supply instructions or automatic tool permissions to a replacement agent.
- Agent deletion retains historical records; replacement agents get no old profile,
  channel, knowledge or private settings. Standard creation defaults still apply.
- No new role framework, notification, BusinessEvent or external provider policy.
  Migration `ai_core.0006_agent_knowledge_isolation` adds ownership/link fields only.

## Verification

All database/browser tests use the existing `.venv` and
`scripts.codex_verify.isolated_runtime`; no installation, live provider or ordinary
database seed/reset. Logs and screenshots are under the output directory above.

- Focused isolation suite: 8 PASS; affected regression set: 142 PASS.
- Migration executor rehearsal 0005 → 0006 → 0005 → 0006: PASS, legacy content,
  active state and business retained; no ownership/connections assigned; integrity OK.
- Desktop and mobile browser isolation and RU/KK/EN keyboard/empty states: 4 PASS.
- Existing knowledge validation, failed save/draft retention and retry: 1 PASS.
- Build, TypeScript, RU/KK/EN dictionaries (5263 keys), widget and bundle budgets: PASS.
- Working/index diff hygiene: PASS; index empty, no committed task range.
- Completion affected/dependent backend: 295 PASS; Django system check and
  migration drift check PASS (`backend-final.log`).

Commands:

```text
# Within isolated_runtime, each with its isolated environment:
python manage.py check
python manage.py makemigrations --check --dry-run
python manage.py test apps.ai_core apps.bots apps.conversations.tests_ai_confirmation apps.automations -v 1
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-migration.py
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-ui.py desktop-chromium ai-agent-isolation.spec.ts --output=../output/ai-agent-isolation-20261005/desktop-final
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-ui.py mobile-chromium ai-agent-isolation.spec.ts
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-ui.py desktop-chromium ai-agents-ux.spec.ts --grep "knowledge explains"
# frontend:
npm run build
npm run check:bundle
```

Initial backend failures exposed fixtures relying on implicit business knowledge or
unbound profiles; fixtures now create explicit ownership/profile capabilities and
retain their original assertions. Initial desktop failure was a selector trying to
choose an agent before opening the collapsed picker; corrected and rerun. Original
failed logs remain available; they are not claimed as passing runs.

## Delivery

Owner authorized the concrete backup/migration operation on 06.10. Only ai_core.0006
was applied to canonical `db.sqlite3` after plan verification and SQLite backup.
Original rows/columns in 113 tables remain unchanged, no knowledge was linked
automatically, and integrity/foreign-key checks pass. Both existing knowledge
records remain shared. Owned canonical servers were started and HTTP readback
returned 200. No seed/reset/deletion. Details and backup location:
[certification report](ai-agents-certification-20261006.md#working-database-operation).

Changes remain local/uncommitted. Prior dependency CI run 37312854122 for 9ff3662
failed (braces/DOMPurify), and continues to block publication. No dependency changes,
full release certification, deployment or new provider checks are in this scope.
