# NOTIFICATION-QUEUE-20261113

Scope: protect active ordinary notifications from overflow and align AppError
colors, retaining the approved card design. Canonical checkout
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`, base
`1421a111`. Existing unrelated WIP is excluded. No domain/API/permission,
BusinessEvent/AI, migration, working DB, environment or external-send changes.

## Behavior

- Four ordinary notices remain visible. Pending notices enter FIFO after a slot
  frees; visible cards keep their identity, hover, focus and running action.
- Pending cards are not mounted and do not expire unseen. Dedupe includes pending
  and visible notices, preserving explicit event/request identity and independent
  actionable operations. Visible ordering remains newest-first.
- Inline, direct AppError toast and notifyError share the existing error mapping:
  not_found info; authentication/permission/conflict/rate_limit/offline/provider
  warning; validation/temporary/internal danger. Explicit tone overrides remain.
- Saturated tokens, typography, spacing, close control, portal, undo, session and
  connectivity behavior retain their established design and responsibilities.

## Evidence boundary

Local scoped acceptance PASS on13Nov. Existing installed dependencies reused with
unchanged package/lock inputs; Node24.18.0. Build and Node checks used the repository
`isolated_runtime`; Chromium served the real shared components from canonical
Vite on dedicated port56938, with synthetic operations and intercepted network.
No working backend, database or provider was used.

- Browser: `node node_modules/@playwright/test/cli.js test --config=playwright.alerts.config.ts`
  with `ALERT_TEST_PORT=56938`, `ALERT_EVIDENCE_DIR=../output/notification-queue-20261113`
  and task-local `--output`: **37 PASS**. Final targeted `--grep 'queue retains|original opener|enlarged notification'`
  **3 PASS** after preserving the removed-opener regression separately and checking
  the bottom of scrollable enlarged text. **38 distinct scenarios**, not40.
- Node: `node --test scripts/tests/notification-dedupe.test.mjs scripts/tests/action-feedback-policy.test.mjs scripts/tests/fallback-surface-policy.test.mjs scripts/tests/app-error-normalization.test.mjs`:
  **22 PASS**.
- `npm run build`: **PASS** (i18n, TypeScript, app and widget).
  `npm run check:bundle`: **PASS**; app shell352.3kB below400kB budget. Existing
  lazy RU/KK dictionaries remain above500kB (563.9/565.5kB); no dictionary or
  dependency expansion belongs to this task. `npm audit --audit-level=moderate`:
  **0 vulnerabilities**.
- Whole intended diff, new file and local links reviewed; diff hygiene PASS.

Reproduction failed on old code because Queue0 disappeared at overflow. Initial
new tests also exposed two fixture errors: passing normalized AppError into a hook
expecting raw errors, and advancing the fake clock without flushing the exit phase.
Both corrected with the same acceptance. The policy source guard was updated to
follow the extracted pure mapping and verify its compatibility re-export. Failed
logs are retained; no assertion was weakened to accept a product failure.

## Scoped UI delivery gate

- PASS geometry/design: existing padding16px, radius12px, text14/21px, icon20px,
  close32px and notification colors confirmed by browser at1440/768/390/320px,
  RU/KK/EN. Approved32px close control retained per owner contract.
- PASS meaning/content: all ten error categories checked across inline/direct
  toast/notifyError and explicit override in all locales; no new product copy,
  assets, decorative content or translated keys. Color also has text and icon.
- PASS behavior: overflow during hover/focus/pending action, one action execution,
  failed retry, FIFO admission, pending dedupe and full reading interval; source
  delays, undo recovery, reconnect/draft retention and support-copy recovery pass.
- PASS keyboard: close/Enter, focus return including removed opener, portal actions
  inside modal/drawer/nested dialogs, forced colors and reduced motion pass.
- PASS responsive reading: long unbroken text and200% text at320px remain within
  width; host scroll reaches the final description, close remains keyboard reachable.
- PASS visual inspection: `stack-ru-1440.png`, `stack-kk-768.png`, `stack-en-320.png`,
  `error-ru.png`, `error-kk.png`, `error-en.png`, `text200-320.png`,
  `text200-bottom-320.png` reviewed in the task output directory. Contrast checker:
  white/danger6.49, white/info6.90, dark/warning10.23 (all normal-text AA PASS).
- PASS scope/purpose/craft: approved status-card identity retained; no page
  composition, media, navigation, theme, business data or backend redesign. React
  review confirms stable keys/callbacks, functional state updates, no new effects,
  network requests or dependencies. Loading is the existing pending-action state;
  empty queue renders no cards. Full WCAG certification is not claimed.

No code or local-evidence remainder in the accepted scope. Product/CRM/access/AI/
integration/operations contracts, roadmap and README need no change: no domain,
permission, setup, provider or roadmap-phase change. Frontend contract and evidence
registry updated; previous historical evidence retained without rewriting it.
Backend/full-project/live gates are not required for this bounded frontend fix.
Detailed command logs, snapshots and publication/CI receipt are in
`output/notification-queue-20261113/CHECKPOINT.md`. Local acceptance does not claim
deployment or full-project certification.
