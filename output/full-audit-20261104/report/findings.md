# Реестр находок

Сводка backend/root/UI проверена:87 канонических находок,29 прежних и58 новых. Записи
не заменяют исходные failures и границы. [Полные поля и доказательства](findings.json).

Severity описывает влияние в указанной границе; priority задаёт порядок работы.
Исторический native и условная утечка не объявляются текущим server exploit.

| ID | Источник | Severity / priority | Наблюдаемое поведение |
| --- | --- | --- | --- |
| REQ01 | prior29 | high / P1 | только неденежный план и receipt/refund Appointment/Deal. Полный денежный сценарий пилота недоступен. |
| REQ02 | prior29 | medium / P1 | текстовые инструменты есть, audio/transcription flow отсутствует. Голосовой критерий не закрыт. |
| REQ03 | prior29 | medium / P1 | автоматический путь оставляет оба поля null. Неполная ответственность/происхождение записи. |
| CRM-TERMS01 | prior29 | high / P1 | создаётся Appointment200/30 либо100/60; fingerprint прежний. Клиент получает не те условия, которые выбрал. Денежного списания в тесте нет. |
| CRM-EVENT01 | prior29 | medium / P2 | manual1successRun/1Task; automatic booked,0Run/0Task. Настроенная задача после автоматической записи не создаётся. |
| OPS-Q01 | prior29 | high / P1 | notifications, automations, reports_exports не имеют Compose consumer. Уведомления/автоматизации/экспорт могут оставаться в очереди в этом профиле. |
| REQ04 | prior29 | medium / P2 | конкретный CRM transport/binding и paired receipts не найдены. Generic integration не закрывает будущий обмен. |
| UI01 | prior29 | medium / P1 | второе исключение useI18n. Нельзя воспользоваться восстановлением при падении дочернего UI. |
| UI02 | prior29 | medium / P2 | фильтрация только загруженной страницы. Пользователь не находит существующую задачу. |
| UI03 | prior29 | medium / P2 | вместе error, No clients yet, Total0. Ложное впечатление отсутствия данных. |
| UI04 | prior29 | medium / P2 | неоднозначная семантика/навигация. Axe severity не security severity. |
| UI05 | prior29 | low / P2 | неверные semantics и одинаковый заголовок вкладки. |
| UI06 | prior29 | medium / P2 | неактуальная форма пароля. |
| UI07 | prior29 | low / P2 | русский месяц в EN. |
| UI08 | prior29 | low / P3 | default dashboard и неподходящий текст. |
| UI11 | prior29 | low / P2 | There are unsaved changes +Cancel/Save. Ложное предупреждение и лишнее действие. |
| UI12 | prior29 | low / P3 | анимация остаётся. |
| UI09 | prior29 | medium / P2 | 222Node tests:215PASS7FAIL; focused rerun воспроизводит7. Часть regex/inventory ожидает старый router/create-lead/fallback shape. Полный gate не зелёный. |
| UI10 | prior29 | medium / P2 | Records toolbar RU/KK/EN ожидают0dialogs, но утверждённый shared CalendarPopover — nonmodal role=dialog;3FAIL. Calendar tests также содержат старое ожидание отсутствия owner client_name. |
| SEC-DEP-01 | prior29 | medium / P2 | pip audit runtime+dev:14advisories в3dev-lock packages; frontend npm audit0. Direct apps/config/scripts use не найден. Удалённая эксплуатация runtime не доказана. |
| PERF01 | prior29 | medium / P2 | B301 fixture, GET /api/work-queues/?limit=10 в legacy workflow:488SQL при бюджете58, полный и focused прогоны. Helpers вызывают per-item client readability без batch context. Измерение appointments workflow и масштаба отдельно в backend report. |
| PERF02 | prior29 | high / P1 в измеренной границе готовности | GET /api/clients/,N=1000сущностей/domain и дополнительных клиентов: SQLite heavy median18.4s/20SQL; distributed single17.26s/20SQL/19KB. PG heavy warmup28.618s200; каждый50request профиль даёт10ClientsTimeout на10s deadline и40успехов прочих API. Несколько annotated COUNT/DISTINCT/summary/page queries занимают3.2–3.7s каждый в SQLite. |
| PERF03 | prior29 | medium / P2 | Client crm-card184SQL на25и1000fixtures, по5samples; существующий budget40. Shapes:51Business,50Client,25Deal fetches. crm_cards.py509 timeline без select_related при serializer, читающем business/client; conversation relation deal также не подгружен. |
| VERIFY01 | prior29 | medium / P2 | Full backend4FAIL: PERF01 плюс AI action-count2<3, multi-Business bell без selected business400, W018 при valid synthetic key. Semantic AI2named/0executed PASS; W018 local-audit key control PASS. |
| VERIFY02 | prior29 | medium / P2 | Штатный S04 drill передаёт _s04_hold/invalid-user fixture, которые нынешняя action_validation отклоняет до ожидаемого fault window. Audit helper использует допустимые данные и отдельную имитацию сбоя. |
| DOC01 | prior29 | low / P2–P3 | Yandex/D01/Records/RPO/старые scoped остатки/миграции/публикация расходились с решениями и receipts. |
| MOB-H01 | prior29 | high / P1 при reuse | A enqueue→logout→B login→actual replay/client; pending A command отправляется с B Authorization. Queue не actor-scoped. Fetch capture, без server mutation/утверждения tenant bypass. |
| MOB-H02 | prior29 | medium / P2 | zani://tasks/42→tasks42; advertised HTTPS /mobile/tasks/42→home из-за hostname parsing. |
| MOB-H03 | prior29 | medium / P2 | 51enqueue→50retained, старейшая команда исчезла из-за slice50. |
| TEAM-ANALYTICS | expanded_audit | high / 1 | Analytics-only manager receives raw lead data despite source-resource denial/module disable. |
| UTF8-PREFIX | expanded_audit | medium / 2 | Strict decoding of the first512 bytes rejects valid multibyte text split at the boundary. |
| IMPORT-NONFINITE | expanded_audit | medium / 2 | Manual sale accepts NaN as amount and zero quantity becomes one; persisted BusinessEvent payload only is proven. |
| IMPORT-DURATION | expanded_audit | medium / 2 | Duration1.9 is truncated to1 and Infinity returns500 with no rows/events. |
| PAID-BETA-BROKER | expanded_audit | high_if_credential_bearing_url / 2 | CLI emits raw broker URL when configured; credential-bearing URLs would enter console/artifact output. No real URL/credential read. |
| HEALTH-QUEUE-WARNING | expanded_audit | medium / 2 | Queue warning is excluded from top-level warning sum: healthy other sources + warning queue yields overall healthy. |
| INVALID-CALENDAR | expanded_audit | medium / 2 | Well-shaped invalid calendar dates produce500 while malformed controls return400. |
| WORKING-HOURS-WEEKDAY | expanded_audit | medium / 2 | Bulk working-hours input with noninteger weekday reaches unhandled type/hash conversion and returns500. |
| LEAD-REOPEN-APPOINTMENT | expanded_audit | medium / 2 | Lost lead remembers previous appointment_created state; reopen chooses it, then central transition table rejects lost→appointment_created. |
| DEAL-REQUIRED-PAYLOAD | expanded_audit | medium / 2 | Required expected_close_at missing rejects stage change; same field supplied in payload accepts change but stored field remains NULL. Positive/negative service controls retained. |
| TASK-INVALID-VERSION | expanded_audit | medium / 2 | Normal-owner Task start with impossible X-Task-Version date returns500 and retains state/version; well-formed stale control409, current control200 moves in_progress. |
| SEGMENT-EMPTY | expanded_audit | medium / 2 | Tag empty/not-empty operator partitions are incorrect. |
| SEGMENT-SCOPE-SHAPE | expanded_audit | medium / 2 | Owner POST accepts list value_json201; evaluate returns500, corrected object control200. Resource scope remains separate static security candidate. |
| AUTOMATION-OVERDUE-STARVATION | expanded_audit | medium / 2 | Repeated bounded scans revisit the first task whose run already exists and never reach later overdue tasks. |
| NOTIFICATION-APPOINTMENT-URL | expanded_audit | medium / 2 | Real producer creates recipient state but its appointment path is excluded from personal feed; canonical calendar query control succeeds. |
| BOT-ZERO-PRICE | expanded_audit | medium / 2 | Service context serializes zero price as blank, identical to missing; positive10 preserved. |
| MESSAGE-CURSOR | expanded_audit | medium / 2 | Lookahead ID is returned as cursor then excluded by next-page strict comparison, losing a message. |
| PIPELINE-ARCHIVED-TASK | expanded_audit | medium / 2 | Real _ensure_task returns archived open metadata task, creates no replacement; helper used by confirmed conversation pipeline. |
| ATTACHMENT-RETRY | expanded_audit | medium / 2 | Each retry POST creates a new row and fresh UUID blob; no replay key/hash uniqueness. Partial batch retry can duplicate successful files. |
| ATTACHMENT-AUDIT-ROLLBACK | expanded_audit | medium / 2 | Normal rename200; audit fault returns500 after changed filename persists without audit. |
| CONNECTOR-AUDIT | expanded_audit | medium / 2 | Normal config control succeeds; synthetic credential/config mutation persists connected status and credential row after audit raises. |
| ROUTING-STARVATION | expanded_audit | medium / 2 | First policy with unassignable item exhausts checked budget every scan, starving later eligible businesses. |
| ROUTING-STALE-LIFECYCLE | expanded_audit | medium / 2 | Real scanner/service deterministic interleaves assign a task completed after selection and overwrite intervening manual assignment with old fallback decision. |
| PUBLIC-CLIENTS-CAP | expanded_audit | medium / 2 | 105 owned clients yield bare100-row response; page2/offset100 returns identical IDs through real get body. |
| OUTREACH-BATCH | expanded_audit | medium / 2 | Campaign larger than batch cannot continue through launch/refresh; no continuation worker registered. |
| OUTREACH-REPREPARE | expanded_audit | medium / 2 | Manual audience reprepare retains deselected recipients. |
| OUTBOUND-STALE-FINISH | expanded_audit | medium / 2 | Generic old worker completion overwrites new sent result after stale recovery/reclaim. Ycloud adapter path has separate fencing. |
| EXPORT-STALE-FINISH | expanded_audit | medium / 2 | Stale worker can overwrite newer completed export because completion lacks claim ownership token. |
| EXPORT-LIMIT-AND-ROWS | expanded_audit | medium / 2 | Data growth after enqueue exceeds configured row cap; newline-based row_count counts embedded quoted newlines as records. |
| IDEMPOTENCY-PRUNE | expanded_audit | medium / 2 | Expired IDs selected before renewal are deleted after real begin_crm_command reclaims the row. |
| TEMPLATE-ATOMICITY | expanded_audit | medium / 2 | Failure on second template field leaves first field/form; analogous pipeline template failure leaves pipeline+first stage. |
| INVITE-MALFORMED | expanded_audit | medium / 2 | Non-UUID route token reaches UUID ORM conversion without mapped DRF validation. |
| ARCHIVE-SENSITIVE-ARTIFACTS | expanded_audit | high conditional on archive distribution and sensitive local artifacts / 2 | Actual rsync selection includes nested backup SQLite, issuer env and browser storage-state/session files; root env/database controls are excluded. |
| EXCEPTION-SECRET-LOGGING | expanded_audit | medium conditional on secret-bearing exception and log access / 2 | Provider logger.exception retains raw exception; JsonLogFormatter serializes message and formatted exception without redaction. Existing synthetic connector test expects raw token marker in captured logs. |
| UI13 | expanded_audit_ui | medium / P2 | Injected logout503 shows Login, but reload restores the same cookie-backed authenticated session. |
| UI15 | expanded_audit_ui | medium / P2 | Segment201 followed by filter503 leaves an empty active segment; repeating creation receives duplicate400. |
| UI16 | expanded_audit_ui | medium / P2 | A503, successful B201, return to restored A draft and retry produces a new Idempotency-Key. |
| UI17 | expanded_audit_ui | medium / P2 | Late first lookup overwrites duplicate warnings for a newer or cleared Client contact (the current phone input is unchanged); Lead form says current client has prior client leads and switches to Create anyway. |
| UI18 | expanded_audit_ui | medium / P2 | Client drawer26→25, Inbox59→50 and pricing history51→50 have no continuation. Full client page shows all26 and is excluded from drawer truncation. |
| UI19 | expanded_audit_ui | medium / P2 | Drawer notes/custom fields tab switches, resource/service/hour browserBack and resource create Escape discard draft. The intercepted stale reconnect GET response contains a changed Service updated_at and remounts the dirty form; no server mutation occurred. |
| UI20 | expanded_audit_ui | medium / P2 | Resource PATCH of A permits typing B then resets to A; pricing create201 clears newer name B. |
| UI21 | expanded_audit_ui | medium / P2 | Exception save for Dec1 pending; change to Dec2 resets mutation and reenables save; Dec1 success opens review for Dec2. |
| UI22 | expanded_audit_ui | medium / P2 | Client card503 has no inline Retry/Back; initial KK locale chunk503 stays loading; platform page999 Retry repeats404 without page reset, although search recovers. |
| UI23 | expanded_audit_ui | medium / P2 | SummaryItem0 becomes dash; nullable catalog price becomes0; failed pricing-control read displays active and Stop. |
| UI24 | expanded_audit_ui | medium / P2 | Blank service duration sends no request and no visible error; new no-branch resource requires an unnecessary schedule change before Save enables. |
| UI25 | expanded_audit_ui | medium / P2 | Ctrl+K opens unnamed non-dialog overlay; Tab escapes into background and close icon lacks name. Escape works. |
| UI26 | expanded_audit_ui | medium / P2 | Default Select End activates off-scroll item with scrollTop0; Inbox13-item menu clips below320x480, while320x568 fits. |
| UI27 | expanded_audit_ui | medium / P2 | View-only specialist sees enabled Edit/Add tag/Archive; manager Archive confirmation makes real isolated request that correctly returns403. |
| UI28 | expanded_audit_ui | medium / P2 | UTC browser groups Jan1 20:30Z under Jan1 while Asia/Almaty display is Jan2 01:30. |
| UI29 | expanded_audit_ui | medium / P2 | With30closed and29open fixtures status=open shows Closed0 and All29, while paused/unassigned remain global. |
| UI30 | expanded_audit_ui | low / P3 | Appointments empty state says Client tasks; full client conversations show website; timeline labels raw Crm/Client Created. Conditional platform history and provider/automation vocabulary remain source-confirmed only. |
| UI31 | expanded_audit_ui | medium / P2 | Default server preparation can migrate/seed ordinary db.sqlite3 before isolated guard; actual gate predicates omit missing actions or non-auth503. Helpers were not started against working database. |
| UI32 | expanded_audit_ui | medium / P2 | 503 leaves text only in bubble without retry; denied localStorage fails before fetch; growing history clips header above320x480; RU/EN mixed labels. Two-way chat remains optional, not a defect. |
| UI33 | expanded_audit_ui | low / P3 | Full client page renders26 task display cards but no task link/button, unlike other related entity lists. |
| MOB-H04 | expanded_audit_ui | medium / P2 | Actual retained client clears session on refresh503; concurrent refresh emits two requests. Server rotation outcome for concurrency is not proved. |
| MOB-H05 | expanded_audit_ui | medium / P2 | Retained actual SQLite ORM receipt expires logically but unique tuple remains causing IntegrityError; successful task command retry gets stale_state409 before receipt replay. |
| FU-FE-01 | expanded_audit_ui | Low / P3 | Ownerless legacy sessionStorage draft is adopted by the currently authenticated user without owner provenance. Properly namespaced current drafts remain isolated. |
| FU-FE-02 | expanded_audit_ui | Conditional Medium / P2 | Optional Sentry init has no sensitive URL scrubbing; current publicRoutes retains bearer path for reset/invitation and main initializes monitoring before Router. |

Прежние raw rows/versions и normalization gaps сохранены внутри JSON; текущие
restatements помечены отдельно. Combined acceptance/impact — сохранённый текст,
не новая политика. Неустановленные security/policy кандидаты остаются в
[candidate applicability](../backend/candidate-applicability-review.json),
а реальные ограничения среды — в [coverage-gaps.md](coverage-gaps.md).
