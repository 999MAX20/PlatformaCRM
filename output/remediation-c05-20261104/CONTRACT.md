# C05 contract — 2026-11-04
Owner: explicit «Приступаем к с05» in current chat. Scope UI13 only.
Root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
base 112358d77dae0c0d148e9d9bc87e2cc782d90f91. Starting status/db receipt retained.
Behavior: logout waits for cookie revocation; failure remains authenticated with
persistent localized error/retry; successful logout clears token/identity/offline
state and propagates to sibling tabs. Serialized cookie operations and generation
guards prevent stale responses affecting a changed session. No backend policy change.
Risk: shared authentication high impact. Reuse cookie queue, tokenStorage,
AuthProvider and StatusNotice. No redesign, working DB, other cycles, push/deploy.
Focused: Node executable cookie/API race and failure tests; browser real isolated
server login/logout, 503/network/reload/retry, double-click, sibling tab, platform
and invite callers, desktop/mobile and RU/KK/EN. Completion: affected auth tests,
frontend safe build/types/i18n, diff/docs/links. No full project gate; backend
unchanged. Preserve foreign AccountPage/i18n roots and all other WIP.
