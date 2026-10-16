# Регрессионные правила PlatformaCRM

Действующая выжимка проверяемых прецедентов; срез 07.10.2026.
Исторический defect catalogue сохранён побайтно в
[архиве](../archive_docs/2026-10-07/actual_docs/DEFECT_KNOWLEDGE_BASE.md).
Его прежние «uncommitted/blocked» относятся к прежним snapshot и не доказывают
текущее состояние. Не переоткрывать closed defect без regression evidence.

| Правило | Проверка | Применение |
| --- | --- | --- |
| ZR-001 Stable typing | Enter at least 5 characters quickly; assert text, caret and focus survive async requests | Every internal/global search, filter text field and autocomplete |
| ZR-002 Cancel invariance | Open and cancel an action; assert entity, tab, draft, scroll context and focus remain usable | File picker, modal, drawer, share/print, OAuth and permission flows |
| ZR-003 Shared-layer blast radius | When one shared component fails, enumerate and test all consumers | CRM drawer, tables, filters, overlays, forms, notifications and API hooks |
| ZR-004 No technical leakage | Force provider/API failure; assert safe merchant copy and absence of raw errors/secrets | Inbox, integrations, automations, AI and imports |
| ZR-005 Recovery action placement | Assert retry/recovery appears once, is permission-aware and is shown only when actionable | Messages, integrations, imports, background jobs and sync states |
| ZR-006 Overlay continuity | Exercise Escape, backdrop, focus return, native dialogs and viewport changes | Drawers, dialogs, popovers, command palette and mobile navigation |
| ZR-007 Success-path preservation | After a defect fix, prove the original normal action still completes | Every remediated interaction |
| ZR-008 Canonical route and information budget | Assert one canonical URL, safe aliases and one unique decision per dashboard surface | Dashboard, overview and landing workspaces |
| ZR-009 Server-owned connector authority | Reject foreign bindings and forged verification; delayed writes/results must not overwrite newer setup; verify allowed dedicated setup | Channel/connector APIs, credential rotation, OAuth and provider webhook resolution |
| ZR-010 Session recovery continuity | Distinguish network/429/5xx from invalid credentials; retain drafts, serialize tab cookie changes, reject old-account continuations and verify current-device logout | Shared auth/API client, startup, account security and every authenticated form |
| ZR-011 PostgreSQL row-lock scope | Nullable JOINs, including reverse blacklist filters, cannot be locked by an unrestricted FOR UPDATE; lock the intended entity explicitly and prove concurrency, revocation and rollback on PostgreSQL | Invitation acceptance [regressions](../apps/businesses/tests_invitation_concurrency.py); session revocation during ownership transfer [regressions](../apps/businesses/tests_ownership.py). ADMIN-01/02 snapshots and evidence in PRIMARY-SESSION |

Охват shared-layer выбирать по затронутым callers и риску; не запускать все
страницы только из-за правки Markdown или локальной косметики. Сохранять исходный
success path, действующие permissions и tenant isolation.

16.10, stage6: после добавления ADMIN02–05 новые audit resource IDs не имели
UI-подписей в общей истории. Сквозной переход воспроизвёл `clinicCrm.kind.*` вместо
названий разделов. Исправлено отображение через существующие переводы вкладок;
[регрессия](../frontend/e2e/platform-details.spec.ts) проверяет все четыре подписи,
RU/KK/EN, mobile и переход история → обращение → Business. Это применение ZR-004
к техническим ключам, без изменения backend identifiers или разрешений.

Общие FC/UX/FB и backend обязательства остаются в
[acceptance](../docs/current/acceptance.md). Неизвестная полнота старого dedicated
regression test (включая ZD-001) — evidence gap для целевой проверки, не команда
переписывать реализацию. Новый defect требует snapshot, reproducer, impact,
минимального исправления и применимого regression gate.
