# Маршруты общей проверки — 12.11.2026

[Отчёт](crm-global-run-20261112.md), [покрытие сценариев](crm-global-run-20261112-coverage.md).
Исходный inventory:98 declarations; в текущем source100, добавлены company/staff.
Ни посещение URL, ни отсутствие overflow не доказывают функциональный PASS.
Таблица сопоставляет declarations с сохранённым route-ledger; отдельные ранние
ручные сценарии есть только в browser-observations и B-протоколе. «Нет строки»
означает отсутствие структурированного route evidence, а не отсутствие реализации.
Загрузка/редирект/неизвестный ID не выдаются за проверку успешной страницы.

| Declaration | Записей ledger | Наблюдавшиеся локали | Граница |
| --- | --- | --- | --- |
| `/documents` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/documents/:documentId` | 8 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/pricing` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/bots` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/crm` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/contacts` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/login` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/signup` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/mfa` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/forgot-password` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/reset-password/:uid/:token` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/recover-account` | 2 | ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/invite/:token` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/app/voice/history` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/settings/voice` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/integrations/import` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/appointments` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/appointments/:id` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/support` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/support/:id` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/dashboard` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/account` | 1 | ru | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/leads` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/app/leads/:id` | 2 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/deals` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/deals/:id` | 2 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/clients` | 4 | en, kk, ru | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/clients/:id` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/tasks` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/tasks/:id` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/calendar` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/calendar/:id` | 2 | kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/conversations` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/conversations/:id` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/app/timeline` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/bots` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/bots/:id` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/integrations` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/pricing` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/ai-assistant` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/ai` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/assistant` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/inbox` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/ai-agents` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/app/ai-agents/:id` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/app/ai-agents/:id/:section` | 10 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/automations` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/business` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/business/services` | 3 | en, kk, ru | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/business/branches` | 3 | en, kk, ru | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/business/resources` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/business/working-hours` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/services` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/resources` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/working-hours` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/analytics` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/settings` | 22 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/billing` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/platform` | 1 | ru | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/platform/operations` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/platform/merchants` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/platform/merchants/:id` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/platform/account` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/platform/support` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/platform/support/:id` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/platform/merchants/:id/incidents/:component/:episode` | 0 | — | Нет отдельной строки ledger; NOT PROVEN в сплошной матрице. |
| `/platform/prospects` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/platform/landings` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/platform/billing` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/platform/analytics` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/platform/settings` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/leads` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/account` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/deals` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/clients` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/tasks` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/calendar` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/conversations` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/timeline` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/crm-bots` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/integrations` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/ai-assistant` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/ai` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/assistant` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/inbox` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/ai-agents` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/automations` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/services` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/resources` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/working-hours` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/analytics` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/settings` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/billing` | 1 | не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/notifications` | 3 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/dashboard/*` | 1 | en | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `*` | 170 | en, kk, ru, не записана | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/business/company` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
| `/app/business/staff` | 2 | en, kk | Есть snapshots; только описанные B-варианты, не полный route PASS. |
