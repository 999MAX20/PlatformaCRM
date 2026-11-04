# C03 / PAID-BETA-BROKER / EXCEPTION-SECRET-LOGGING

Owner explicitly starts C03 only. Canonical PlatformaCRM, codex/ui-testing-toolkit,
base121d5e53b9b2f39bf9b1f42ef8026e613a2e6a81.233 foreign WIP entries preserved.
Target logging/sanitization/paid_beta_gate/provider test clean at start; foreign
production_audit/rules/config.settings unchanged. No push/merge/deploy, dev off.
Result: paid-beta readiness reports configured/TLS metadata, no broker credentials;
configured JSON console masks recognized credential forms in message/args/chained
exceptions/allowlisted context without losing type/stack/correlation. Reuse core
sanitization, strengthen quoted credential values if reproduced. Do not scan live
secrets or emit real telemetry; arbitrary unlabeled strings are not inferable secrets.
Risk: shared log sink and shared sanitizer; focused synthetic before/after, actual
configured console handler and text/JSON CLI tests; provider public/persisted error
regression, dependent connector/sanitization/readiness/observability tests plus isolated
system/migration drift. No UI/build/full-E2E/concurrency gate for formatting/read-only
projection. Optional Sentry reviewed separately, not certified by console tests.
No business/permissions/schema/notification/BusinessEvent/AI behavior changes.
