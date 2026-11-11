# Функциональная матрица

**DRAFT / все строки NOT RUN.** [План, роли, среды и критерии](README.md).
Статическое основание и существующие test-файлы по каждому коду группы:
[inventory](inventory.md). Наличие тестового файла не означает, что каждый вариант
ниже уже автоматизирован. Перед исполнением связать case с конкретным test method
или ручным протоколом; отсутствие связи остаётся coverage gap.

Обозначения метода: A = service/API/DB автоматическая проверка; C = реальные
конкурентные транзакции PostgreSQL; W = worker/storage/transport; B = пользовательский
сценарий через «Компьютер»; L = отдельно разрешённый live provider/human-assisted.
Приоритет P0/P1/P2 указан для сценария. Роли O/A/M/OP/SP/RO/BR/MB/X/PA/PS/AN
определены в плане. Каждая перечисленная вариация имеет свой result suffix `.a/.b/...`.

Для всех merchant write/read путей обязательна X-ACCESS ниже, даже когда она
не повторена в строке. Для каждой UI-формы применяется X-UX; утверждать PASS
только после relevant variants, а не после одного happy path.

## AUTH: вход и восстановление

Основа: [auth](../../../apps/accounts/auth_views.py), [MFA](../../../apps/accounts/mfa_views.py),
[routes](../../../frontend/src/app/publicRoutes.tsx). Роли AN/O/M/X/PA. B01–B03.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| AUTH-01 | P0 | Верный/неверный пароль; неизвестный email; заблокированный пользователь | Успешный вход только допустимому аккаунту, без раскрытия существования чужого аккаунта в ошибках | A+B |
| AUTH-02 | P0 | Access refresh, logout, повтор старого refresh, истёкший токен | Logout/revocation исключают повторный доступ; UI переводит ко входу без раскрытия прежнего Business | A+B |
| AUTH-03 | P0 | MFA enrollment/verify; неверный, просроченный и повторный код; recovery code дважды | Вход не завершён до MFA; recovery одноразовый; секрет/коды не попадают в логи и чужую сессию | A+B |
| AUTH-04 | P0 | Сброс пароля через письмо; invalid/expired/used token; смена пароля | Правильный пароль работает; старые сессии по действующей policy отозваны; повтор токена отвергнут | A+B+L |
| AUTH-05 | P0 | Много login/reset/MFA/password-change запросов; разные workers | Shared quota/throttle работает без bypass сменой worker; безопасная ошибка и retry-after, без блокировки чужого аккаунта по произвольному ID | A+W |
| AUTH-06 | P0 | Cookies/CSRF/origin/CORS, /admin/ без MFA и после step-up | Нельзя обойти auth/MFA через альтернативный вход, unsafe request или открытый redirect | A+B |
| AUTH-07 | P1 | Потеря сети во время входа/refresh, новая вкладка, reload | Нет бесконечного spinner/двойного входа; сессия восстанавливается или честно просит вход | A+B |
| AUTH-08 | P0 | Существующий social-auth endpoint: configured/unconfigured provider, неверный provider token | Нет входа по произвольным claims; выключенный provider честно недоступен; UI-кнопка только если реально подключена | A+L |

## ACCESS: общая отрицательная матрица X-ACCESS

Основа: [access](../../../apps/businesses/access.py), [permissions](../../../apps/core/permissions.py),
[contract](../../current/access.md). Все merchant-группы, B04/B05/B08/B35.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| ACCESS-01 | P0 | Для каждого ресурса list/detail/create/update/action/options/history/export с ID Business B | Ни строк, ни counts/имён/файлов, ни побочной записи B; код отказа соответствует контракту, без утечки существования | A+B |
| ACCESS-02 | P0 | OWN/TEAM/BUSINESS/NONE, явный deny, manage fallback, смешанные memberships | Один effective scope на список/объект/счётчик/command; deny не обходится fallback | A+B |
| ACCESS-03 | P0 | BR запрашивает A2 и shared каталог; меняет branch/client/assignee в payload | Branch guard и same-Business links сохранены, shared объекты разрешены только по их policy | A+B |
| ACCESS-04 | P0 | Отозвать права/членство после открытия карточки, preview, export, approval | Следующий request/execute/download проверяет актуальный доступ; старое UI разрешение недостаточно | A+B+W |
| ACCESS-05 | P0 | RO/OP/SP пытаются запрещённый command через прямой API и deep link | Backend отказывает независимо от видимости кнопки; данные/история не меняются | A+B |
| ACCESS-06 | P0 | Запрет notes/money/contact fields на list/card/search/export/AI/timeline | Чувствительные поля маскируются в каждом projection, не только основной форме | A+B |
| ACCESS-07 | P0 | Отключённая capability, неактивный assignee, чужой role/team/resource | Запрет до domain side effects, нет assignment на неактивного участника | A |
| ACCESS-08 | P0 | Запросы A→B→A одним аккаунтом, параллельные вкладки, SSE reconnect | Нет кеша чужих прав/данных; request-local оптимизация не переживает новый запрос | A+B+W |
| ACCESS-09 | P0 | Security center audit/logins/support tabs, failed-only, risk summary и expired grant | Только разрешённый Business/данные, правильные active/expired состояния; просмотр не выдаёт grant | A+B48 |

## ACCOUNT: личный кабинет

Основа: [account](../../../frontend/src/features/account), [accounts](../../../apps/accounts). O/M/PA. B02/B03.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| ACCOUNT-01 | P1 | Изменить профиль, язык, часовые/персональные настройки; reload | Только собственные разрешённые поля сохранены, локаль применена согласованно | A+B |
| ACCOUNT-02 | P1 | Загрузить/заменить/убрать avatar; invalid type/size | Корректное изображение сохраняется; недопустимое отвергнуто, нет чужого avatar path | A+B |
| ACCOUNT-03 | P0 | Запрос/подтверждение смены email; занятый email; чужой/повторный token | Смена только после корректного подтверждения; auth/session policy и история сохранены | A+B+L |
| ACCOUNT-04 | P0 | Просмотр устройств/истории входа; отзыв выбранной и остальных сессий | Другие сессии теряют доступ, действующая не путается с ними; чужие устройства скрыты | A+B |
| ACCOUNT-05 | P1 | Персональные notification preferences и старый settings hash | Настройки действуют для данного пользователя; legacy ссылка ведёт в личный кабинет | A+B |

## ONBOARD: регистрация и начальная настройка

Основа: [signup](../../../apps/accounts/views.py), [onboarding](../../../apps/onboarding/views.py).
AN/O/OP; B01/B06. Onboarding API не означает наличие отдельной страницы-мастера.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| ONBOARD-01 | P0 | Зарегистрировать новый бизнес C; повтор submit; конфликт аккаунта | Создан согласованный owner/Business/membership; повтор не создаёт второй бизнес | A+B+C |
| ONBOARD-02 | P1 | Получить status/templates; явно применить выбранный template | Шаблон только выбранного Business; отрасль не навязывается общему интерфейсу | A |
| ONBOARD-03 | P0 | OP/чужой owner применяет template/demo/setup-channel | Запрещено; capability/demo gate нельзя обойти API | A |
| ONBOARD-04 | P1 | Demo-data при off/on в одноразовой среде; повтор | Off запрещает; on создаёт только документированный набор и не повреждает существующий | A |
| ONBOARD-05 | P1 | Первый website channel/message; неполная конфигурация | Честный status; правильный Inbox/связи, без раскрытия частных совпадений посетителю | A+B |

## BUSINESS: бизнес, точки и каталог

Основа: [branches](../../../apps/branches), [services](../../../apps/services),
[business UI](../../../frontend/src/features/business/BranchesPage.tsx). O/A/BR/RO; B06/B07.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| BUSINESS-01 | P1 | Изменить реквизиты/валюту/часовой пояс допустимым способом; invalid values | Серверная валидация; старые операции не переписаны новым представлением | A+B |
| BUSINESS-02 | P0 | Новый single-location бизнес; повторная и конкурентная инициализация | Одна автоматическая основная точка, без дублирования каталога/часов | A+C+B |
| BUSINESS-03 | P1 | Добавить вторую точку, настроить услуги/цены/длительность | Явные настройки второй точки; shared база клиентов и разные условия услуги работают | A+B |
| BUSINESS-04 | P0 | Архивировать последнюю/непоследнюю активную точку; restore; конкурентный архив | Последняя активная защищена сервером; история/будущая работа не исчезают | A+C+B |
| BUSINESS-05 | P1 | Создать/изменить/архивировать service; неверная цена/длительность | Новые записи используют текущие условия; существующие сохранённые условия не переписаны | A+B |
| BUSINESS-06 | P0 | Физический ресурс A1 и требование ресурса у услуги; чужая точка/архив | Требование реально резервирует доступный ресурс, без подмены Business/branch | A+B+C |
| BUSINESS-07 | P0 | Routing/default booking responsible для manual/AI; неактивный/чужой пользователь | Только допустимый актуальный участник, новая работа использует default, явный override существующей не затирается | A+B |

## TEAM: команда, роли, приглашения

Основа: [businesses](../../../apps/businesses), [settings](../../../frontend/src/features/settings).
O/A/M/SP/X/MB; B08/B09.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| TEAM-01 | P0 | Пригласить; принять правильным/чужим аккаунтом; expiry/revoke/replay | Только целевая личность получает нужный membership; гонка/replay не повышают права | A+C+B+L |
| TEAM-02 | P0 | Создать роль, задать resource/actions/scopes/field grants, явный deny | Effective policy совпадает с каталогом, нет self-escalation обходом payload | A+B |
| TEAM-03 | P1 | Отделы, memberships, ответственный, филиальные разрешения | UI и selectors используют актуальный состав, чужие/неактивные участники исключены | A+B |
| TEAM-04 | P0 | Отключить вход специалиста и затем восстановить | Специалист/визиты/история остаются; работа не передаётся автоматически администратору | A+B |
| TEAM-05 | P0 | Архивировать специалиста с будущими визитами | История сохранена, новые назначения блокируются; дальнейшая работа разбирается вручную | A+B |
| TEAM-06 | P0 | Перенос ownership: инициирование/consent/отмена/expiry/повтор | Только разрешённый target, актуальные guards и audit; не через generic membership update | A+C+B |

## CLIENT: клиенты и карточка

Основа: [client views](../../../apps/clients/views.py), [card UI](../../../frontend/src/components/crm/client-card).
M/RO/OW/TM/BR; B10/B11/B12.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| CLIENT-01 | P1 | Создать/редактировать клиента, invalid contact, длинные/Unicode значения | Однозначная валидация и сохранение после reload; двойной submit не маскируется ложным успехом | A+B |
| CLIENT-02 | P1 | Поиск, quick/custom filters, sort, page1/2/empty, URL back/forward | Состав/count/summary/facets согласованы; нет пропусков/дублей на границе страницы | A+B |
| CLIENT-03 | P0 | Открыть карточку и все доступные связанные вкладки | Настоящие связи; скрытые задачи/записи/деньги не раскрываются через карточку | A+B |
| CLIENT-04 | P0 | Duplicate check → merge dry-run → merge; спорные связи/платежи/планы | Только same-Business разрешённый merge, перенос связей и traceable audit, source история не потеряна | A+C+B |
| CLIENT-05 | P0 | Archive/restore с активной работой/неназначенным планом | Domain guard соблюдён; запрет объяснён; разрешённый архив сохраняет историю | A+B |
| CLIENT-06 | P1 | Notes/tags, связанная задача/запись из карточки | Правильный клиент подставлен, права самостоятельного ресурса проверены | A+B |

## FIELDS: пользовательские поля, теги и сегменты

Основа: [fields](../../../apps/core/custom_field_views.py), [activities](../../../apps/activities/views.py).
O/A/M/RO; B13. Segments API отдельно, полноценная страница не предполагается.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| FIELDS-01 | P1 | Определение поля каждого реально поддержанного типа; required/default/options | Валидация типа/настроек, отображение в соответствующей форме и сохранение значения | A+B |
| FIELDS-02 | P1 | Пустое numeric, multi-select, false/0, даты, удалённая опция | Нет500; точное различие пустого/0/false; invalid option отвергнута | A+B |
| FIELDS-03 | P0 | Чужая field definition/value/entity, запрет поля | Same-Business и field policy до чтения/записи/экспорта | A |
| FIELDS-04 | P1 | Фильтр custom field: no matches → убрать один фильтр → reload | Фильтр остаётся доступен при пустом результате, выборочный reset восстанавливает данные | A+B |
| FIELDS-05 | P1 | Tags/tagged objects: create/link/unlink/duplicate/foreign entity | Связи валидны; tag не раскрывает чужой объект; итоговые фильтры согласованы | A+B |
| FIELDS-06 | P1 | Segments/segment-filters CRUD и вычисление на известном наборе | Только разрешённые записи; unsupported фильтр отвергнут; UI не выдумывается | A |

## RECORD: основной рабочий цикл записей

Основа: [appointments](../../../apps/scheduling/views.py), [workspace](../../../apps/scheduling/record_workspace.py).
M/SP/BR/RO; B14/B15/B16/B17.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| RECORD-01 | P0 | Создать из списка, клиента и Inbox; выбрать ответственного отдельно от специалиста | Один Appointment с точными связями/source provenance, без скрытого Lead/Deal вместо записи | A+B |
| RECORD-02 | P0 | Подтвердить/перенести/завершить/отменить/no-show по допустимым переходам | Status/timestamps/reason/history согласованы, generic PATCH не обходит command | A+B |
| RECORD-03 | P0 | Раннее завершение, терминальная/архивная запись, запретный обратный переход | Действующий state machine; не выдумывать новые corrections без утверждённого контракта | A+B |
| RECORD-04 | P0 | Replay command, конфликтующий idempotency payload, stale revision, два оператора | Один результат или явный конфликт; нет двойного визита/события/резерва | A+C+B |
| RECORD-05 | P1 | List/pipeline/calendar/client card после изменения в одном месте | Один status/время/ответственный; обновление других поверхностей и reload согласованы | A+B |
| RECORD-06 | P1 | Filters по периоду/status/branch/responsible/custom fields, пустые/скрытые значения | Count/состав доступны по текущим правам; сохранённый ID не подписан ошибочно «Все» | A+B |
| RECORD-07 | P0 | Смена цены/длительности услуги до submit или после booking | Stale terms не принимаются молча; сохранённые price/duration прежней записи стабильны | A+C+B |
| RECORD-08 | P0 | Ошибка audit/event/связанных записей в атомарной операции | Откат всей операции; UI не показывает успешное создание | A |

## PLAN: планы посещений

Основа: [plan API](../../../apps/scheduling/plan_views.py), [services](../../../apps/scheduling/plan_services.py).
M/SP/BR/RO; B18.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| PLAN-01 | P0 | Создать план с неназначенными этапами; повтор запроса | Один план, без Appointment для этапа без времени | A+B |
| PLAN-02 | P0 | Назначить время этапу, repeated submit, overlap/stale terms | Один связанный Appointment, обычные booking guards; revision изменяется | A+C+B |
| PLAN-03 | P0 | Revise состав/ответственного; override этапа; stale revision | Explicit согласование поддержанного изменения, история этапа сохраняется, override не затирается | A+B |
| PLAN-04 | P0 | Архив/restore; отмена визита; merge/archive клиента | Не теряется identity/история назначенного этапа; domain constraints сохранены | A+B |
| PLAN-05 | P0 | Частичная видимость, OWN/TEAM, закрытый branch, скрытый этап/history | Нельзя получить права на скрытый этап через видимый план; counts фильтруются до pagination | A+B |
| PLAN-06 | P1 | Открыть план и связанные payments/records | Не обещается несуществующий пакетный debt/payment allocation; организационный результат отделён от денег | A+B |

## SCHEDULE: календарь, рабочие часы и ресурсы

Основа: [schedule](../../../apps/scheduling), [branches](../../../apps/branches).
O/M/SP/BR; B07/B16/B19.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| SCHEDULE-01 | P1 | Общая неделя, интервалы специалиста, исключения/выходной/нерабочее время | Available slots совпадают с настройкой; invalid интервал отвергнут | A+B |
| SCHEDULE-02 | P0 | Два одновременных booking на специалиста/оборудование | Только допустимая ёмкость; конфликт возвращён без частичной записи | A+C |
| SCHEDULE-03 | P0 | Работа в A1/A2 с travel time, пересечение смен/поездки | Недоступный переход между филиалами не предлагается и не сохраняется | A+B+C |
| SCHEDULE-04 | P0 | Одновременный upsert общих часов на один weekday | DB uniqueness и API recovery, без дублирования общего расписания | A+C |
| SCHEDULE-05 | P1 | День/неделя/месяц, фильтры, date range/clear/cancel, TZ полночь | Правильные даты/границы и totals; popover не двигает таблицу, Escape возвращает focus | A+B |
| SCHEDULE-06 | P0 | Ручной/bot/AI/import activation booking с resource requirements | Общие domain guards у всех входов; нельзя обойти резервирование другим каналом | A+C+W |

## MONEY: ручной журнал оплат

Основа: [ledger](../../../apps/payments/services.py), [tests](../../../apps/payments/tests.py).
M/O/RO; B20. Это запись факта, не реальное списание денег.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| MONEY-01 | P0 | Receipt100.00; два частичных receipt; без связи/с записью/сделкой | Неизменяемые отдельные операции, точный Decimal и Business currency, верный client | A+B |
| MONEY-02 | P0 | Refund30.00→70.00; overrefund/нулевой/отрицательный/лишний scale | Остаток0, лишний возврат запрещён; причина обязательна, refund-of-refund запрещён | A+B+C |
| MONEY-03 | P0 | Future time, refund раньше receipt, чужой/неверный client/link/currency | Серверный отказ до записи, никакой автоматической конвертации валют | A+B |
| MONEY-04 | P0 | Same submission replay, changed payload, два concurrent refund | Дубликат не создан, конфликт не маскируется; общая сумма возвратов не превышает receipt | A+C+B |
| MONEY-05 | P0 | Manager refund, RO money view, generic edit/delete, ошибка audit | Запрет по policy; immutable ledger; audit failure откатывает запись/суммы | A+B |
| MONEY-06 | P0 | Client merge/archive и money projection в timeline/export | Ledger/links сохранены; сумма/причина не раскрываются через более широкую activity | A+B |

## TASK: задачи

Основа: [tasks](../../../apps/tasks), [task UI](../../../frontend/src/features/tasks).
M/OP/SP/RO; B21.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| TASK-01 | P1 | Создать/изменить title/description/due/priority/assignee с допустимыми связями | Сохранение после reload; пустой title/чужая связь/неактивный assignee отвергнуты | A+B |
| TASK-02 | P0 | Complete/reopen/archive/restore, повтор/гонка | Lifecycle/timestamps/history согласованы, нет потери исходного завершения | A+C+B |
| TASK-03 | P1 | Mine/team/overdue/no due, search/sort/custom filters/pages | Точные строки/count и timezone; пустое состояние не скрывает reset | A+B |
| TASK-04 | P0 | Создать из записи, Inbox, AI, automation | Права TASKS проверены отдельно от источника, idempotency и ссылка на источник сохранены | A+B+W |
| TASK-05 | P1 | Ограниченный пользователь читает карточку/history/ссылку | Scope и sensitive projection совпадают с list; человекочитаемая история без битой кодировки | A+B |

## INBOX: переписки

Основа: [inbox API](../../../apps/conversations/inbox_views.py), [conversations](../../../apps/conversations).
M/OP/RO; B22/B23.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| INBOX-01 | P1 | Список/поиск/фильтры каналов/unread, открытие длинной переписки | История/пагинация/счётчики точны, новые сообщения не теряются при обновлении | A+B+W |
| INBOX-02 | P0 | Отправка текста, timeout/retry/replay, incoming duplicate | Один исходящий side effect; pending/sent/delivered/failed не подменяются друг другом | A+B+W+L |
| INBOX-03 | P0 | Relink клиента, создать запись/задачу из диалога | Текущие права/Business проверены; draft provenance не сохраняет чужой client | A+B |
| INBOX-04 | P0 | Handoff/pause/resume bot, staff reply, конкурентный AI reply | Автоответ не отправляется после корректного takeover; traceable status/recovery | A+B+W |
| INBOX-05 | P1 | Quick reply, черновик, switch conversation, reload, stale selection | Текст отправлен в выбранный диалог; нет переноса черновика/контекста в чужой чат | A+B |
| INBOX-06 | P0 | Нет send/manage права, закрытое provider window/канал off | Нет отправки; UI объясняет реальное ограничение, не показывает delivered | A+B+W |
| INBOX-07 | P0 | Повторный визит из закрытого обращения; старый draft/изменившиеся условия | Новый Appointment с provenance, без reopen старого Lead/Deal и без переноса старого согласия/override | A+B |

## BOT: клиентские боты и website chat

Основа: [bots](../../../apps/bots), [bot UI](../../../frontend/src/features/bots).
O/AN/M; B24/B37.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| BOT-01 | P1 | Создать/настроить bot/channel, knowledge, preview и enable/disable | Конфигурация сохраняется в своём Business; disabled не обслуживает новые действия | A+B |
| BOT-02 | P0 | Website token/session isolation, неверный/отозванный token | Visitor не читает чужую беседу/внутренние совпадения клиента | A+B |
| BOT-03 | P0 | Диалог записывает клиента/визит; уточняет branch/time/service | Подтверждённый результат существует; booking/resource/current permission guards сохранены | A+W+B+L |
| BOT-04 | P0 | Injection/чужие контакты/медицинские советы/опасное действие | Не раскрывает чужие данные, не выполняет неразрешённое; safety policy сохранена | A+L |
| BOT-05 | P1 | Provider off/timeout/нет knowledge; transfer к сотруднику | Честный fallback/handoff, обычный Inbox продолжает работу | A+B+W |
| BOT-06 | P0 | Readiness при configured profile, но provider unavailable/нет booking actor/responsible | Configuration ready не выдаётся за runtime ready; diagnostics не обходят write-time guards | A+B |

## AI: помощник сотрудника, аналитик и approvals

Основа: [ai_core](../../../apps/ai_core), [contract](../../current/ai.md).
M/O/RO/BR; B25/B26.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| AI-01 | P0 | Read/query/report по известным данным; пустой период/скрытый ресурс | Ответ подтверждён сущностями/источниками, нет выдуманных totals или чужих данных | A+B+L |
| AI-02 | P0 | Обычная команда create task/record; неоднозначное имя/дата | Явные ordinary действия по текущему контракту; нужное уточнение, без лишнего второго подтверждения | A+B+L |
| AI-03 | P0 | Критичная команда/approval: confirm/reject/expire; изменить payload/actor | Исполнение только точного разрешённого immutable intent, current rights и replay guard | A+C+B |
| AI-04 | P0 | Отзыв прав между plan и execute; смена Business/branch/agent | Нельзя выполнить старым approval/контекстом; история/источники изолированы | A+B |
| AI-05 | P1 | Queue job cancel/retry, timeout, reconnect, reset memory | Корректные состояния, отменённая/повторная попытка не создаёт дубль | A+B+W |
| AI-06 | P0 | Prompt injection из клиента/knowledge/message/tool output | Недоверенный текст не даёт дополнительных прав, не раскрывает secrets | A+L |
| AI-07 | P1 | AI полностью выключен/лимит/нет provider key | Обычные CRM сценарии работают; причина недоступности понятна | A+B |
| AI-08 | P1 | Agent profiles/knowledge/history/logs и настройки каждого доступного раздела | Сохранение, отдельные suggest/execute/manage grants и приватность исходных данных | A+B |
| AI-09 | P1 | Status выбранного agent/model против actual provider settings, analytics off | Отображён фактический источник доступности, а не глобальный ключ другого provider; secrets скрыты | A+B |

## VOICE: голосовой ввод

Основа: [speech](../../../apps/ai_core/speech_views.py), [voice UI](../../../frontend/src/features/voice).
M/BR/SP; B27. Реальный микрофон/ASR не заменяется текстовой имитацией.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| VOICE-01 | P1 | Record→Stop→Send; cancel; mic denied/no device/empty/too long | Контролы доступны, поток освобождён, ошибка без ложной отправки | A+B+L |
| VOICE-02 | P0 | RU/KK/EN «создай клиента и запиши…», перефразирование | Клиент+Appointment атомарно; completed только после сохранения реального визита | A+B+L |
| VOICE-03 | P0 | Нет времени/неясный клиент/филиал/нет слота, продолжить ответом | Контекст уточнения сохранён, неправильный объект не создан, причина конкретна | A+B+L |
| VOICE-04 | P0 | Датированный план нескольких посещений, ошибка одного этапа, retry | Атомарность утверждённого workflow, без частичного «успеха» и дублей | A+C+B+L |
| VOICE-05 | P1 | История голоса/ссылки на результаты, языки, шум/паузы | История приватна и соответствует результату; human audio evidence отдельно | A+B+L |
| VOICE-06 | P0 | Одинаковые имена/разные телефоны, normalized phone, телефон изменился до execute | Явное уточнение при конфликте, нет перезаписи контакта или записи не тому клиенту; guards повторены при исполнении | A+B+L |

## AUTO: автоматизации

Основа: [automations](../../../apps/automations), [views](../../../apps/automations/views.py).
O/M/RO; B28.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| AUTO-01 | P1 | Template/manual rule, preview, conditions/actions, save/toggle | Preview не исполняет действие; rule сохраняется с валидной конфигурацией | A+B |
| AUTO-02 | P0 | Реальное локальное событие записи/задачи, repeat event | Одна допустимая цепочка без рекурсии/дублирования, BusinessEvent routing точный | A+W+B |
| AUTO-03 | P0 | Изменённые права/branch/assignee между постановкой и worker | Current authorization и допустимые связи до side effect | A+W |
| AUTO-04 | P1 | Failed run retry/cancel, configuration race, worker crash | Состояние/attempt history честны, отменённый run не исполняется позднее | A+C+W+B |
| AUTO-05 | P0 | Notification/AI action требует approval или provider unavailable | Не обходит подтверждение/отправку; обычная CRM операция не объявляется неуспешной из-за optional AI | A+W |

## NOTIFY: личные уведомления и объявления

Основа: [notifications](../../../apps/notifications), [notifications UI](../../../frontend/src/features/notifications).
O/A/M/SP; B29.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| NOTIFY-01 | P1 | Bell/list read/unread/all-read двумя сотрудниками | Личные состояния независимы, counts совпадают, all-read не означает ознакомление | A+C+B |
| NOTIFY-02 | P0 | Publish announcement с аудиторией; acknowledge; revoke | Только O/A по policy; аудитория фиксируется, отзыв скрывает публикацию с сохранением истории | A+B |
| NOTIFY-03 | P0 | Открыть источник после сужения прав, сменить Business/SSE reconnect | Нет утечки данных источника; feed продолжает проверять текущие права | A+B+W |
| NOTIFY-04 | P1 | Transport pending/failed/retry/cancel, announcement misuse | Внутренняя лента не считается внешней очередью; неверное transport action запрещено | A+W+B |
| NOTIFY-05 | P1 | Appointment message settings, preferences, локальный trigger | Правильное расписание/канал/получатель, без дубля; delivered требует receipt | A+B+W+L |

## IMPORT: перенос данных

Основа: [workspace](../../../apps/core/import_workspace), [import API](../../../apps/core/import_export_views.py).
O/A/M/RO; B30.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| IMPORT-01 | P1 | Новый перенос→file chooser cancel/select; добавить файл/retry | Cancel не создаёт пустой draft; выбранный файл загружен один раз в нужный draft | A+B |
| IMPORT-02 | P0 | CSV/XLSX, несколько листов, mapping, preview, invalid rows | Точная валидация/сопоставление поддержанных сущностей; invalid rows не проходят confirm | A+B+W |
| IMPORT-03 | P0 | Confirm20known rows, повтор confirm/reimport, duplicate decision | Сверка всех полей/связей и counts; не создаёт неожиданные дубли | A+C+B+W |
| IMPORT-04 | P0 | Unsupported/oversize/corrupt/formula/XLSX limits/AV down | Нет bypass quarantine/scan, безопасная ошибка и retry; формула не выполняется сервером | A+B+W |
| IMPORT-05 | P0 | Import clients/records/catalog/custom fields с чужими IDs/правами | Те же domain guards, PII/SETTINGS scope до write; ошибка не оставляет запрещённую запись | A |
| IMPORT-06 | P0 | Исторические/будущие записи и отдельная activation | Импорт сам не отправляет сообщения/не создаёт платежи; activation явная и guarded | A+B+W |
| IMPORT-07 | P1 | Worker crash/timeout/reclaim, stale preview, resume draft/history | Продолжение текущей попытки по контракту, честные counts/errors; не обещать общую атомарность без проверки режима | A+C+W+B |
| IMPORT-08 | P0 | Существующие manual sales/catalog-item API и ImportJob sales/catalog | Normalized event/provenance и SETTINGS/current entity права; metadata update не активирует архивную услугу | A |

## EXPORT: выгрузки

Основа: [export API](../../../apps/core/import_export_views.py), [job tests](../../../apps/core/tests_export_attempts.py).
M/RO/X; B31.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| EXPORT-01 | P1 | Малый CSV и большой asynchronous job по фильтру/периоду | Состав/колонки/количество соответствуют разрешённой выборке, успешное скачивание | A+B+W |
| EXPORT-02 | P0 | Сузить scope/field grants после generation и перед download | Актуальное fingerprint/PII masking или отказ; старый файл не обходит доступ | A+B+W |
| EXPORT-03 | P0 | Чужой job/download URL, expired/failed file | Нет доступа к private файлу, секреты не в URL/errors | A+B |
| EXPORT-04 | P0 | Worker reclaim и поздний completion старой попытки | Claim token не позволяет перезаписать/удалить результат победившей попытки | A+C+W |
| EXPORT-05 | P1 | CSV formula injection, RU/KK/EN, empty result, row/period limit | Безопасные ячейки и кодировка; честная пустая выгрузка/лимит, не обрезанный успех | A+B |

## FILE: вложения и приватные файлы

Основа: [attachments](../../../apps/core/file_attachment_views.py), [private files](../../../apps/core/file_views.py).
M/RO/X; B31/B34.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| FILE-01 | P0 | Upload→quarantine→scan→download; scanner unavailable/infected | Непроверенный файл недоступен, разрешённый скачивается только после проверки | A+B+W |
| FILE-02 | P0 | Чужой attachment, path traversal, revoked membership, guessed URL | Нет обхода private storage/Business/родительского объекта | A+B |
| FILE-03 | P1 | Неверный MIME/extension/size, unicode filename, same name | Валидация/безопасное имя и отсутствие перезаписи чужого файла | A+B |
| FILE-04 | P1 | Storage timeout/retry, cleanup orphan/partial upload | Нет ложного успеха и удаления действующего файла; recovery наблюдаем | A+W |

## INTEGRATION: подключения, API-токены, webhooks

Основа: [integrations](../../../apps/integrations/views.py), [YCloud](../../../apps/integrations/ycloud).
O/A/RO; B32/B33. Каждый provider из capabilities тестируется отдельно, доступность не предполагается.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| INTEGRATION-01 | P1 | Settings→Connections, старые routes/query, connect/check/disconnect | Корректная секция, свои manage права, безопасный статус; секреты masked | A+B |
| INTEGRATION-02 | P0 | Telegram/WhatsApp/Instagram inbound: bad signature/token, duplicate/out-of-order/foreign binding | Ни чужой маршрутизации, ни повторного сообщения; durable обработка по provider contract | A+C+W+L |
| INTEGRATION-03 | P0 | YCloud signup cancel/error/stale attempt, binding номера, reconnect | Только разрешённый Business/channel/номер, актуальный инициатор и статус | A+B+C+L |
| INTEGRATION-04 | P0 | YCloud Business App coexistence echo/replay/app staff reply | Нет resend/unread/продления24h окна; staff reply приостанавливает AI по контракту | A+C+W+L |
| INTEGRATION-05 | P0 | API token issue/rotate/revoke/scope, expiry и PublicApiClients | Secret показан по policy, revoked токен не работает, tenant/field guards сохранены | A+B |
| INTEGRATION-06 | P0 | Webhook endpoints/test/retry: unsafe URL, bad cert, repeated delivery | SSRF/secret guards, signed payload, retry/idempotency и честная история | A+W |
| INTEGRATION-07 | P1 | Kaspi/MoySklad/WB/Ozon/прочие заявленные capabilities: config/test/pull | Только реально поддержанные операции; unsupported явно unavailable, не фиктивный sync | A+B+W+L |
| INTEGRATION-08 | P0 | Sync fail/retry/partial pagination/credentials revoked during job | Stable provenance/идемпотентность, нет дублей и утечки credentials | A+W |

## PRICING: существующий Kaspi pricing

Основа: [pricing](../../../apps/pricing), [UI](../../../frontend/src/features/pricing).
O/RO; B38. Наличие /app/pricing не означает утверждённый live writeback.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| PRICING-01 | P1 | Catalog/rule create, recommendation с известными competitor offers | Цена вычислена по правилу, не ниже min; объяснение соответствует данным | A+B |
| PRICING-02 | P0 | Apply с writeback off, enable autopilot без safety confirm | Simulated не выдаётся за применённое; autopilot требует предусмотренного подтверждения | A+B |
| PRICING-03 | P0 | Daily limit/emergency stop/concurrent apply | Лимит и stop соблюдены, нет повторного изменения цены | A+C+W |
| PRICING-04 | P1 | Missing/stale competitor data, provider timeout, change log | Честный unavailable/stale, видимые попытки, без выдуманной цены | A+B+W |

## ANALYTICS: dashboard и отчёты

Основа: [analytics](../../../apps/analytics), [queues](../../../apps/core/work_queues.py).
O/M/RO/BR; B39.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| ANALYTICS-01 | P0 | Dashboard/queues на известном наборе, preview limit и полный count | Counts distinct, без двойного счёта записей, права до агрегации | A+B |
| ANALYTICS-02 | P0 | Все существующие вкладки/периоды, архивные результаты, границы TZ | Oracle соответствует реальным источникам/датам, не смешивает creation/start/won timestamps | A+B |
| ANALYTICS-03 | P0 | Manual receipts/refunds/net, пустой ledger, external unavailable/stale | Не называется прибылью/долгом; unavailable не превращается в ноль; источники не суммируются произвольно | A+B |
| ANALYTICS-04 | P0 | Сужение field/resource/branch grants, OWN/TEAM financial summary | Недоступные суммы/объекты отсутствуют в totals и экспорте | A+B |
| ANALYTICS-05 | P1 | Export отчёта, scheduled reports/widgets API, long range | Selector/период совпадают с UI; job/лимит/ошибка честны | A+W+B |

## TIMELINE: история и аудит

Основа: [activity](../../../apps/activities/views.py), [timeline UI](../../../frontend/src/features/timeline).
O/M/OP; B40.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| TIMELINE-01 | P1 | Действия клиента/записи/задачи/системы; old/new поля и actor | Понятное событие, сохранённые изменения, имя объекта отдельно от клиента | A+B |
| TIMELINE-02 | P0 | Открыть ссылку/детали после отзыва ресурсных/PII прав | Analytics grant не раскрывает закрытый объект, чувствительные суммы masked | A+B |
| TIMELINE-03 | P1 | Period/calendar/filter/search/page/reset в RU/KK/EN | Реальный результат, полные месяцы/правильная кодировка, выборочный reset | A+B |
| TIMELINE-04 | P2 | Mobile filters/list, scroll, keyboard, narrow320 | Один понятный scroll, нет обрезанных действий и потери focus | B |

## SUPPORT: обращения и инциденты

Основа: [support API](../../../apps/support/urls.py), [views](../../../apps/support/views.py).
O/M/PA/PS; B34/B36.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| SUPPORT-01 | P1 | Создать case, reply/attachments/read, close/reopen | Чёткие статусы/история, сообщения двух сторон и unread независимы | A+B |
| SUPPORT-02 | P0 | Чужой merchant case, internal notes, participant permissions | Нет утечки platform notes или чужого Business; current auth на каждом action | A+B |
| SUPPORT-03 | P1 | Platform assign/transition/internal note/incident association | Только допустимый сотрудник/переход; traceable history и актуальная очередь | A+B |
| SUPPORT-04 | P0 | Concurrent transitions/reopen/repeated reply | Lifecycle согласован, сообщения не теряются и не дублируются | A+C+W |

## PLATFORM: администрирование платформы

Основа: [platform views](../../../apps/core/platform_views.py), [routes](../../../frontend/src/app/platformRoutes.tsx).
PA/PS/O; B35/B36/B41.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| PLATFORM-01 | P0 | Merchant пытается /platform и соответствующий API; PA/PS login/MFA | Merchant denied, platform роли не обходят MFA; legacy route не повышает доступ | A+B |
| PLATFORM-02 | P1 | Overview/operations/worklists/merchants/detail/search/filter | Реальные данные, здоровый/ошибочный компонент различаются, секреты скрыты | A+B |
| PLATFORM-03 | P0 | CRM browser/read section при support grant/expiry/case/основании | Чтение в разрешённом контексте с audit; без grant нет произвольного CRM доступа | A+B |
| PLATFORM-04 | P0 | Account recovery/employee repair с owner consent, cancel/expiry/replay | Нет глобального unlock или восстановления без разрешения; история и scope сохранены | A+C+B |
| PLATFORM-05 | P0 | Ownership transfer/подтверждение другой стороной/конфликт/expiry | Нельзя захватить Business через generic edit, согласованный двухсторонний lifecycle | A+C+B |
| PLATFORM-06 | P0 | Sensitive action без свежего step-up/открытого case/reason | Серверный отказ; успешный разрешённый action имеет audit и минимальные эффекты | A+B |

## BILLING: SaaS foundation

Основа: [billing](../../../apps/billing), [UI](../../../frontend/src/features/settings/sections/BillingSection.tsx).
O/PA/PS/RO; B42. Не реальные списания, пока не выбран provider и target.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| BILLING-01 | P1 | Usage/limits/requisites/requested plan, null/zero limits | Реальные units/month, null≠0; requested plan не активирует оплаченный тариф | A+B |
| BILLING-02 | P1 | Commerce off/no offer; включённый sandbox offer→order→bank/card | Off честно unavailable; order snapshot/buyer/amount валидны | A+B |
| BILLING-03 | P0 | Platform bank confirmation PS vs PA, repeated callback/order action | Только разрешённая роль; идемпотентный платёж/аудит, без двойной активации | A+C+W |
| BILLING-04 | P0 | Expired/stale offer, wrong Business/currency/signature, current blocked account | Не снимает независимую блокировку; invalid платёж не признаётся успешным | A+B+W |
| BILLING-05 | P1 | Entitlements и отсутствие утверждённого commercial enforcement | Проверяется существующий контракт, не выдумывается рабочая продажа/expiry policy | A+B |

## LEGACY: Lead/Deal и старые ссылки

Основа: [legacy routes](../../../frontend/src/app/legacyRoutes.tsx), [leads](../../../apps/leads), [crm](../../../apps/crm).
M/RO; B43.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| LEGACY-01 | P0 | Старые /leads,/deals и /app/leads,/app/deals, linked/unlinked IDs | Сохранённые данные/права; никакого numeric-ID redirect на чужую запись/автоконвертации | A+B |
| LEGACY-02 | P0 | Lead status/convert/follow-up/lost reason через retained API | Domain lifecycle, обязательная причина, отдельные TASKS/DEALS права, replay guards | A+C |
| LEGACY-03 | P0 | Deal stage/pipeline/won/lost/archive и cross-business stage | Stage принадлежит Business/pipeline, terminal timestamps/history корректны | A+C |
| LEGACY-04 | P1 | Legacy aliases /dashboard,/integrations,/billing,/services,/ai,/inbox | Документированный redirect или retained view без потерянного контекста и bypass guards | A+B |
| LEGACY-05 | P1 | Generic old routes видны вопреки принятому pilot flow | Зафиксировать контрактное расхождение отдельным defect, не молча объявлять legacy основным UI | B |

## OUTREACH: существующие кампании API, вне пилотного UI

Основа: [outreach](../../../apps/outreach), `OutreachPage` не найден в действующем router.
O/RO; B44 только проверка отсутствия/доступности пути, без выдуманной страницы.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| OUTREACH-01 | P0 | Template/campaign CRUD и recipients на synthetic наборе | Existing NOTIFICATIONS action/scope/capability guards соблюдены | A |
| OUTREACH-02 | P0 | Consent/revoke/STOP/import consent, current permission на send | Нет отправки без допустимого актуального основания; историю consent не теряет | A+W |
| OUTREACH-03 | P0 | Preview/start/retry/cancel/repeated recipient | Идемпотентность и отмена согласно реализованному transport, только mock | A+C+W |
| OUTREACH-04 | P1 | Market exchange/новая частотная политика/реальная рассылка | Отдельно NOT IMPLEMENTED/DEFERRED/NOT AUTHORIZED по контракту, не PASS текущего пилота | A |

## PUBLIC: публичные страницы, формы и widget

Основа: [public routes](../../../frontend/src/app/publicRoutes.tsx), [forms API](../../../apps/leads/views.py),
[widget](../../../frontend/widget). AN; B01/B37.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| PUBLIC-01 | P1 | Landing/login links/documents/404, RU/KK/EN/mobile | Правильный маршрут/документ, нет пустого экрана и внутренних данных | B |
| PUBLIC-02 | P0 | Public form valid/invalid/repeated submit и существующий контакт | Приватные совпадения/CRM IDs не раскрыты; validation/rate limits соблюдены | A+B |
| PUBLIC-03 | P0 | Widget token/session/create/message, reload, cross-session ID | Изоляция посетителей и Business, история только своей беседы | A+B |
| PUBLIC-04 | P1 | Disabled form/channel, expired token, offline/timeout | Понятное состояние, никакого ложного принятия заявки/сообщения | A+B |
| PUBLIC-05 | P0 | LeadForm/fields CRUD, submissions/errors access, неверные field options и чужой form | Настройка только своего Business с нужными правами; private submission/error не публичны | A |

## OPS: эксплуатация, схема, очереди и производительность

Основа: [operations contract](../../current/operations.md), [runner](../../../scripts/codex_verify.py).
Только E1/E2 и отдельно выбранный E3; B45 технические наблюдения, не замена UI.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| OPS-01 | P0 | Migration drift/system; clean DB migrate; restore selected test backup | Схема согласована; restore/constraints/row-field parity проверены без working DB writes | A+W |
| OPS-02 | P0 | PG row locks/unique constraints по booking/payment/import/task/support/auth | Нет пропущенных PG-only проверок под видом полного PASS SQLite | A+C |
| OPS-03 | P1 | Redis/Celery actual queue, worker stop/restart/reclaim, timeout | Нет потери/двойного side effect, очереди и run state согласованы | A+W |
| OPS-04 | P0 | Logs/telemetry/errors/reset/invite URLs/file/download/provider tokens | Секреты/частные payload не уходят в лог/телеметрию; correlation сохраняется | A+W |
| OPS-05 | P1 | Health/readiness/service status/queue warnings/SSE reconnect | Сигнал соответствует реальной зависимости; internal feed не имитирует transport backlog | A+W+B |
| OPS-06 | P1 | Повтор прежней нагрузки small/large,1+workers, RAM/CPU/paging/SQL | Измеренные latency/errors/записи по утверждённому порогу, без переноса локального PASS на сервер | A+W |
| OPS-07 | P0 | Expired-token/CRM-command retention cleanup и конкурентное renewal | Только просроченные записи, актуальные revocation/idempotency не удалены | A+C |
| OPS-08 | P1 | Dependencies/build/i18n/types/bundle/security audit/full backend | Результат точного candidate, каждый skip/failure виден; CI/local/stand различаются | A |

## UX: общая браузерная матрица X-UX

Основа: [frontend contract](../../current/frontend.md), router/settings source inventory.
Все B01–B45/B48, расширенные B46/B47.

| ID | P | Действие / варианты | Ожидаемый результат | Метод |
| --- | --- | --- | --- | --- |
| UX-01 | P1 | Все reachable routes + deep link/reload/back/forward/unknown ID | Рабочая навигация и guards; route sweep во всех локалях, aliases отдельно | B |
| UX-02 | P1 | Loading/empty/403/404/500/timeout/offline/retry каждой critical формы | Ошибка отличима от пустоты, введённое не теряется без причины, recovery reachable | A+B |
| UX-03 | P1 | Save twice, Cancel/Escape/outside, dirty close, nested calendar/select | Нет случайного submit/потери данных, focus вернулся, draft/commit разделены | B |
| UX-04 | P1 | Desktop1440/mobile390/narrow320/tablet1024, zoom200% | Нет горизонтального переполнения и недоступных controls, правильный scroll | B |
| UX-05 | P1 | RU/KK/EN, длинные строки, даты/числа/валюта, терминология | Нет keys/mojibake, нейтральные подписи, правильный locale при неизменных данных | B |
| UX-06 | P1 | Keyboard-only и human screen-reader critical flow | Labels/errors/focus/live status понятны; недоступный human этап не считается PASS | B+L |
| UX-07 | P1 | Logout/switch business/session expired в открытом modal/stream | Чужие данные очищены, действие не уходит в прежний Business, путь восстановления понятен | A+B |
| UX-08 | P2 | Contrast/action colors/toasts/date picker/card size на основных consumers | Существующая дизайн-система последовательна; screenshot не является доказательством domain correctness | B |

## Как читать остаток

Все строки выше запланированы, не исполнены. Для существующего, но недоступного
пользователю компонента указать `UI unreachable` и сохранить API-проверку отдельно.
Не добавлять кнопки/страницы в ходе аудита ради закрытия теста. Если контракт требует
доступного пути, отсутствие пути является finding, а не разрешением на разработку.
Новая общая проверка не стирает исторические FAIL и не закрывает AC-CRM-PILOT-01–14,
D01, AC-SEC/I18N/RELEASE/RESTORE автоматически: нужны соответствующие результаты
и явно выбранная целевая среда из [основного плана](README.md).
