# C06 — происхождение черновиков Inbox

**Исправлено и проверено локально**, FU-FE-01, 04.11.2026. C07 не начат.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
base`13862c6d68eb315dca2fff5a1c86fd9532ff65f3` + preserved233 foreign WIP entries. После остановки и
явного возобновления владельцем starting/resumed snapshots совпали.
[Контракт до изменений](../../../output/remediation-c06-20261104/CONTRACT.md).

## Результат и граница

`useInboxDraft` читает только `user:business:conversation` key. Удалены lookup,
копирование и удаление ownerless `business:conversation` legacy key. Старый текст
без автора не показывается в редакторе и не становится черновиком текущего аккаунта.
Legacy значения оставлены нетронутыми, автоматического восстановления/удаления нет.
Правильные scoped drafts, редактирование, reload, переключения account/business/
conversation, in-memory fallback и условная очистка позднего send сохранены.

Это исправление локальной приватности: тот же browser tab/profile, старые данные
и законный доступ разных аккаунтов к одной беседе. Не remote или cross-Business
permission bypass. Уже ранее мигрированные scoped значения неотличимы от настоящих
собственных черновиков и не удаляются; исправление предотвращает новые присвоения.

Изменены hook, actual-hook regression tests, expectation в существующем browser
late-send тесте и новый browser provenance test. Единственный production caller
ConversationsPage передаёт реальные user/business/conversation IDs; sending сохраняет
captured draftKey. Два независимых read-only прохода: boundary investigation и
candidate bypass/regression review; actionable проблем в кандидате не найдено.
Managed security artifacts: target PlatformaCRM, `artifacts/c06/patch-contract.md`,
`independent-review.md`, `fix-report.md`; source review hook SHA256
`7cd120b826211530825f035e122e281cd07108bbb714197b7e4c62fbb4e24df1`.

## Проверки

- BEFORE `node --test frontend/scripts/tests/inbox-draft.test.mjs`:8 tests,
  **2 FAIL/6 PASS** — legacy import и resurrection после очистки/remount.
- AFTER `node --test frontend/scripts/tests/inbox-draft.test.mjs frontend/scripts/tests/inbox-sending-model.test.mjs frontend/scripts/tests/inbox-delivery-policy.test.mjs`: **14 PASS**.
  Legacy negative + existing positive, blank scoped key, missing identity,
  user/business/conversation switch/remount, unavailable storage, changed/late send,
  failed send/idempotent retry, no dispatch for forbidden/empty/closed/pending.
- `.venv/Scripts/python.exe output/remediation-c06-20261104/run_browser.py`:
  **4 PASS**, desktop1280x720/mobile412x839 Chromium; no skips.
  Real isolated login/logout and Inbox for owner/administrator sharing lawful access;
  own draft survives reload and return login, another user's scoped draft stays
  separate, legacy key stays unimported/unchanged. Existing conversation switching
  and late-send test retained (its conversation/message fixtures are synthetic).
  No real provider delivery; tests never send the legacy text.
- `.venv/Scripts/python.exe output/remediation-c06-20261104/run_build.py`:
  safe `npm run build` PASS: TypeScript, i18n6682, app/widget bundles.
- Scoped working/index/actual committed-range hygiene, new paths, links/registry
  and intended content/secret-pattern review PASS. Exact source/log/image hashes:
  `output/remediation-c06-20261104/source-manifest.json`.

isolated_runtime + guarded browser bootstrap: unique temporary SQLite and loopback
ports, dotenv/external sockets/providers suppressed. No workingDB change; dev stays
off; own test processes stopped and successful runtimes cleaned. Dependencies reused.
No UI labels/layout, backend/API/schema/permission/BusinessEvent/notification/AI
behavior changed. No backend/PG/full-project/native/live tests for this client-only
boundary; no claim of release readiness. Earlier failures outside C06 remain open.

## Closure

Plan/frontend contract/Inbox passport/evidence updated consistently; other domain,
access/AI/operations/integrations contracts and README unchanged because server
rules/setup/public APIs are unchanged. Historical audit receipts retained unchanged.
C06 has no code/evidence/environment/owner-decision remainder. Own local commit only,
no push/merge/deploy/newCI. Two C05 interrupted temp folders remain as previously
reported; this cycle did not retry their policy-blocked deletion. Final receipt:
`output/remediation-c06-20261104/final-validation.json`. Next C07 unstarted.
