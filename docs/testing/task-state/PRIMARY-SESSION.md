# PRIMARY-SESSION — PlatformaCRM

## INBOX-LIVE-ACCEPTANCE-20261008 — behavioral PASS; publication below

Owner authorized real-model acceptance of ordinary inquiries, booking, protection
and recovery, including fixes for reproduced in-scope defects. Explicit new budget:
USD 1 maximum, stop before exceeding it; prior task budgets are not reused.
Mode verification/targeted fixes; gap evidence. Same generation 4 primary/root/
branch; clean base `00fe0e7c8743a4b84d136db9492e9228e88beecd`.

Reuse `scripts/ai_behavior`, isolated_runtime, current Inbox pipeline, domain
services and existing safety/booking/recovery tests. Synthetic disposable DB,
real configured AI provider only; controlled outbound receipts, never real
customers or messenger delivery. No working DB, migration, deployment, billing,
CRM-agent/analytics development or new integration rollout.

Changed behavior initially none; if a defect reproduces, minimal correction and
focused regression before dependent work. Risks: budget overflow, false booking,
privacy leak, false handoff, duplicate work and stale replies after recovery.
Acceptance checks facts vs fixture, actual records/relationships and timestamps,
no writes without valid consent, denial/tenant boundaries, sensitive context,
limits and replay, provider failure/manual takeover/resume. Review model output
semantically; HTTP success alone is not PASS. Test controls cannot masquerade as
live channel, infrastructure or clinic acceptance.

Focused checks: existing customer safety/state/recovery, automatic booking,
runtime configuration, Inbox continuity and AI job recovery in isolated runtime;
test budget harness before live use. Add explicit USD1 CLI budget and a targeted
Inbox suite if needed, retaining cumulative attempts/reservations across retries.
Completion: affected/dependent backend suites plus system/migration checks if
runtime changes; reachable API flow, relevant UI/build only if changed. No full
project/E2E gate by default. Docs links/registry/diff checks; reviewed commit,
normal HEAD:main push, remote SHA and actual CI. Keep all failed attempts visible.

Initial plan: prepare selected synthetic scenarios and run deterministic baseline, then
bounded live evaluation. Evidence under `output/inbox-live-acceptance-20261008/`.

First results: 53 focused tests/system/migration drift PASS; 6 budget-harness tests
PASS; 4 no-provider safety/API dry cases PASS. First live 27 cases: 25 machine
PASS, 2 harness failures (ambiguous request expectation contradicted permitted
uncertain handoff; held-worker simulation accidentally used eager result backend).
Retain both failures and fix test setup/criteria transparently, not runtime policy.
Semantic review found a real wrong off_topic classification for clinic address,
and busy/denied booking selection led to another model confirmation of an
unavailable/uncommittable time. Appointment writes remained protected.

Bounded fix plan: clarify business-information categories in qualification;
when existing booking service returns requires_staff, call existing handoff
service and, when auto replies enabled, send existing localized handoff copy.
No new booking permission/policy/endpoint/schema/UI. Existing handoff activity,
audit and manager notification apply; pipeline event retains actual decision.
Add failing pipeline regression for busy, staff-only and disabled-tool selection,
verify immediately; strengthen live assertions and retest affected scenarios.
Provider-failure injection reserves cost conservatively; cumulative ledger stays
under the separately approved USD1. No real messenger delivery claimed.

Final behavioral gate: 130 affected/dependent backend PASS, system/migration-drift
PASS (`backend-1791401726512442200.log`); final live run 28/28 machine and semantic
PASS, 57 real calls. Total 55 case attempts retained, 110 received provider calls,
2 injected-failure reservations. Provider-reported USD0.1104668, conservative
charged/reserved USD0.1228916 of USD1. Final source manifest matches current Python
files. No further paid calls needed. Detailed commands, deltas and limitations:
[acceptance report](../inbox-live-acceptance-20261008.md). Next: final docs/source
review and diff gate, commit/push and actual CI. No new phase. Prior docs CI
37667508038 is now confirmed SUCCESS. Working DB/servers/dependencies unchanged.

## DOCS-RESET-20261007 — консолидация документации

Mode docs; gap — устаревшие маршруты/смешение требований и истории. Владелец
разрешил сверку реализации, обновление README и активных источников, архивацию
старых документов. Один writer generation 4 `01a11776-e13a-76c2-9fc0-75d38228f649`.
Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
clean base `f01d22610118e3a24df86257943a8be91314f916`.

### Контракт и план проверок

Результат: компактный реестр current contracts + паспорта + процедуры; агенты
не берут старые технические планы как действующие. Reuse существующих решений,
паспортов, source/tests и evidence; не переписывать продукт. Риск — потеря правил,
открытых обязательств или ложный live PASS. Поэтому оригиналы сохраняются с SHA256,
последние решения сверяются, незакрытое переносится явно.

Нет изменений кода, схемы, runtime, dependencies, ownership, permissions,
notification, BusinessEvent или AI-поведения. Никаких provider calls, миграций,
deployment или новой продуктовой фазы. Формулировки контрактов сохраняют уже
утверждённые границы, не утверждают архивные предложения.

Checks: inventory/classification, source/decision traceability, archive byte
integrity, active links/anchors/plain paths, agent routing/frontmatter/scenarios,
registry invariants, working/index/actual committed-range diff hygiene. Проверка
новых/нетрекнутых файлов обязательна. App tests/build/install/DB/browser — skipped:
документационная задача, программные входы неизменны. CI запускается существующим
push workflow независимо; его результат проверяется отдельно и не выдумывается.

### Сделано

- 198 прежних проектных документов учтены; 137 перенесены из активного дерева,
  20 прежних entrypoint/procedure/passport тел сохранены перед обновлением,
  40 старых архивных тел и один generated inventory сохранены на месте.
- Созданы 9 current контрактов и source-backed карта возможностей. Сохранены
  актуальные паспорта и стабильные пути процедур/реестра владельца.
- Убраны старые competing планы/redirect stubs; обновлены AGENTS, README, маршруты
  skills; архив имеет отдельную инструкцию non-authority и исключение `.rgignore`.
- Открытые FC/BE/UX/FB и бизнес-решения не закрыты переносом. Последние controlled
  AI creation / manual financial source / support-note / deferred billing решения
  отделены от старых предложений. Предыдущая safety live boundary сохранена.

### Проверки и публикация

Состояние: содержательная проверка PASS. `verify.py` в локальном evidence: 198
исходных Git blobs/сохранённых тел, 52 active entries (30 проектных +22 skill),
328 local links, 12 active anchors, 38 plain paths — PASS. Проверены JSON registry
без изменений ownership, skill frontmatter и отсутствие архива в default rg.
Сценарии маршрутизации: новая CRM/AI/UI задача ведёт к current contract;
исторический PASS читается точечно без открытия scope; unresolved acceptance
остаётся открытым; compaction не меняет владельца. Runtime references к
DKB/generated inventory и ZR-001–010 сохранены. Рабочий/index diff hygiene PASS; 198 staged archive blobs совпали с исходными
SHA256, посторонних non-document paths и unstaged diff нет. Зависший пустой
index.lock снят после проверки возраста, отсутствия Git-процессов и exclusive-open;
индекс и HEAD не менялись другим writer. Реальный committed range и remote/CI
проверяются на этапе публикации.
Детальные безопасные результаты: `output/docs-reset-20261007/` (локальные artifacts).
Документальная часть завершена и проверена. Публикация: reviewed explicit paths,
conventional commit, normal HEAD:main push,
remote SHA readback и фактический CI. Итоговый SHA/CI — в ответе задачи и локальной
квитанции; commit не может содержать собственный hash. Следующий продуктовый этап
не назначен. Незакрытые требования — [acceptance](../../current/acceptance.md).

### Сохранённая история

[Исходный checkpoint](../../../archive_docs/2026-10-07/docs/testing/task-state/PRIMARY-SESSION.md)
содержит закрытые scope и evidence до этой консолидации; это не очередь задач.
Передача generation 3 → 4 завершена и опубликована `f01d226`; registry idle,
source archived native readback. Latest safety CI 37653976762 / 37654213713 и
паспортный CI 37657729094 SUCCESS. Latest safety проверен с mocks; предыдущие
21 real-model continuity cases не сертифицируют последующее изменение защиты.
CRM/Analytics development paused; существующий runtime не удалён/не выключен.
HookActivationStatus REQUIRES_REVIEW_AND_TRUST; новой проверки runtime hook нет.
