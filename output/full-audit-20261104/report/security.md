# Безопасность: доказательства и ограничения

Срез: d27044b1 с учтённым WIP. Полное чтение текущих backend/frontend исходников
расширяет предыдущий ручной аудит; это не завершённый автоматический security scan
и не подтверждение отсутствия уязвимостей. Матрица разрешений и сверка покрытия
завершены с явными static/reused/protected границами.

## Модель угроз и границы доверия

Активы: данные Business и клиентов, роли/сессии, private files, provider credentials,
денежные записи, approval/idempotency identities, история действий и доступность.
Рассмотрены внешний неавторизованный пользователь, участник Business с ограниченной
ролью, другой tenant, недоверенный provider payload/файл, устаревший worker и локальный
потребитель артефактов/logs. Устаревший worker — сценарий целостности без предположения
о злонамеренном операторе. Host compromise не считается преодолённой границей.

| Переход доверия | Проверяемый инвариант и существующие защиты | Доказательство / открытая граница |
| --- | --- | --- |
| Browser/public widget → HTTP API | Session/epoch/MFA, membership, tenant/object/field rules; UI не предоставляет серверное право | Backend role/decision и endpoint registries; TEAM source-projection defect; новые protected probes ограничены ENV-SEC |
| HTTP/domain → DB/history | Lifecycle service, transaction, lock/version, current actor и audit | Named transition/rollback tests; audit partial writes, required-stage payload и stale lifecycle findings |
| Provider/webhook → ingress | Подпись/время/replay, credential isolation, валидация входных данных | Connector source и synthetic fixtures; live signatures/delivery/rotation не сертифицированы |
| User/provider files → storage/AV/download | MIME/size/path/AV quarantine, привязка файла к текущему доступному parent | Existing tests и isolated scanner recovery; private parent-scope candidates сохраняют static status |
| Broker/job → domain/provider effects | Claim ownership, idempotency, retry и проверка актуального состояния | Stale completion/prune/routing reproductions; live external unknown outcome требует отдельной среды |
| Недоверенные данные → AI/tool execution | Grounding, allowlisted tools, explicit approval, повторная проверка прав | Source и mock named tests; реальная модель/injection resistance остаются ENV-LLM |
| Operator/config → console/archive/telemetry | Секреты не попадают в выдаваемые артефакты и диагностические sinks | Archive/readiness/exception findings; фактическая передача секретов не доказана |
| CI/dependency inputs → executable build | Lock/integrity/RECORD provenance, install hooks и env boundary | Installed provenance и passive history review; advisory snapshot имеет свою дату, target image не исполнялся |
| Django admin/platform → identity/business mutation | Отдельные sessions и административные guards не равны REST MFA/epoch | Static caller review; break-glass policy и target ingress остаются явными условиями |
| Historical native storage → следующая session | Auth/queue/account binding, URL validation, durable replay | Immutable73482a3 synthetic reproductions; не текущий web и не установленное приложение |

Детальная связь guards, callers и эффектов находится в
[backend module registry](../backend/module-registry.json),
[effective role contract](../backend/role-decision-contract.json) и
[candidate applicability review](../backend/candidate-applicability-review.json).
Наличие защиты в коде не объявляется доказательством всех сочетаний входов/ролей.

## Подтверждённые проблемы

| Сценарий | Доказательство | Граница вывода |
| --- | --- | --- |
| Team performance возвращает число лидов и текст причины потери при запрете чтения Leads или выключенном модуле | Изолированный API reproducer, положительный контроль и foreign-Business403; [независимая проверка](../team-analytics-independent-review.md) | Внутри Business нарушается доступ к исходному ресурсу; межтенантный обход не доказан |
| Helper чистого архива включает вложенные backup DB/env/browser-auth artifacts | Синтетическое дерево и фактический archive helper; [receipt](../archive-probe.json) | Реальные секреты не копировались, внешнее распространение не установлено |
| Paid-beta readiness выводит CELERY_BROKER_URL целиком | Полное чтение paid_beta_gate.py и CLI, [backend findings](../backend/FINDINGS.md) | Условная утечка в вывод команды, если URL содержит credentials; фактическая утечка не заявлена |
| Console logger сохраняет чувствительный текст исключения | Provider logger.exception → настроенный JsonLogFormatter без redaction, тест с синтетическим маркером; [независимая проверка](../exception-logging-independent-review.md) | Содержимое зависит от исключения; внешняя обработка Sentry не проверена |
| Исторический native-клиент отправляет очередь предыдущего пользователя с авторизацией следующего | Исполнение кода immutable73482a3 с синтетическими токенами и перехваченным fetch; [независимая проверка](../native-independent-review.md) | Исторический клиент, не текущий web и не выполненная серверная мутация |
| Legacy Inbox draft без автора присваивается текущему пользователю | Текущие source hashes совпали с прежним actual-hook reproducer; [независимая проверка](../historical-frontend-security-independent-review.md) | Low: тот же tab/profile, старый формат и законный доступ к той же беседе; текущие namespaced drafts изолированы |
| Optional Sentry сохраняет чувствительную часть URL | Неизменившаяся init-конфигурация и SDK10.56.0, прежний synthetic in-memory event | Conditional Medium: нужен enabled DSN, capture пока bearer полезен и доступ получателя telemetry; фактическая deployed утечка не доказана |

Механизмы archive, readiness и exception logging требуют общей политики обработки
секретов, но сохраняют разные условия воспроизведения. Их нельзя свести к одному
тесту на отсутствие токена в API-ответе: файл, консоль и внешний error sink — разные
каналы. Сырые auth traces, env, DB и приватные backup-файлы не входят в отчётный пакет.

## Проверенные защитные границы

Исходники и существующие автоматизированные проверки охватывают auth epoch и
device sessions, MFA/recovery, tenant/object/field permissions, private attachments,
AV quarantine, ZIP/input limits, webhook signature/replay, destination validation,
AI approval binding и повторную проверку прав перед действием. Точные методы тестов,
исходные SHA и результаты находятся в [backend-test-results.csv](../backend-test-results.csv).
Общий прогон содержит 2698 PASS, 4 FAIL и 50 SQLite SKIP; это не общий зелёный gate.
Отдельные PostgreSQL результаты и причины ошибок сохранены в [tests.md](tests.md).

Проверка UI также показала доступную кнопку Archive для manager без соответствующего
права: фактический backend ответил403, UI показал ошибку. Это дефект доступности
действия в интерфейсе, а не доказанный обход серверной авторизации.

Обычный Django admin использует отдельные sessions/ModelAdmin и не наследует REST
epoch/MFA автоматически. Допустимость raw ownership/member edits как break-glass
процедуры остаётся вопросом политики и отдельной проверки; подтверждённым публичным
exploit этот путь не объявлен. Аналогично default-root image и публичные порты base
Compose требуют контекста развёртывания: stand merge убирает обходные порты, но
CLI-разбор не доказывает доступность или защищённость реально работающего сервера.

Исторические FU-HIST02 (public intake privacy) и FU-HIST04 (login CSRF) закрыты
в текущем локальном срезе по изменённому коду и именованным прежним проверкам
(12 privacy и7 CSRF). Это не deployed certification. Ещё три исторические
гипотезы сохранены условными статическими кандидатами: failed-factor budget при
смене пароля уже авторизованным пользователем; доверие X-Forwarded-For при реально
доступном ingress; social auto-link после pre-registration при отключённом
обязательном privileged MFA. Их предпосылки и возможные внешние защиты не заменены
предположением об эксплуатации. Точные текущие source hashes, snippets, controls
и статусы: [historical-security-current-reconciliation.json](../backend/historical-security-current-reconciliation.json).

## Зависимости, история и ignored-материалы

Предыдущий advisory snapshot сохранил npm0 и pip14 advisories в3 dev-пакетах.
Это результат на дату проверки, а не новый запрос к базам уязвимостей и не
доказательство runtime exploitability. Список и исходные ссылки сохранены в
[предыдущем security report](../../../docs/testing/comprehensive-audit-20261103/security.md).
Текущие входные lock-файлы входят в успешную итоговую сверку исходного среза;
новый запрос advisories не заявляется.

Дополнительный проход проверил версии и байты установленных зависимостей:
81 Python distribution, 10686 совпавших RECORD hashes; 283 установленных npm
пакета совпали с lock и cached tarball integrity. Unhashed Python entries,
неустановленные platform packages и происхождение отдельных unsigned launchers
учтены отдельно. Это проверка происхождения, не построчный аудит библиотек.

Пассивный поиск охватил ignored/browser artifacts и достижимую локальную Git-историю.
Он выявил чувствительные локальные артефакты; значения не выводились и не проверялись
у провайдеров. Все85 кандидатных исторических text blobs разобраны как placeholder,
template expression или явная redaction fixture. Это не исключает неизвестные
форматы секретов, unreachable objects и удалённую историю. Полные границы, hashes,
классификации и исключения: [passive-review.md](../passive-review.md).

## Недоступные проверки

Codex Security Deep Scan не стартовал: инструмент потребовал managed filesystem
permission profile. Позднее автоматическая проверка безопасности отклонила действие
подзадачи, не предоставив точной операции. Заблокированное действие не повторялось
и не переформулировывалось; active-security coverage не объявляется завершённым.
Независимое безопасное чтение исходников и обычные функциональные проверки продолжены.

Не доказаны production origins/proxy/TLS, object-store ACL, key custody/rotation,
Linux image/runtime, live provider signatures/delivery, реальная модель и prompt
injection resistance, физический native device и целевая облачная инфраструктура.
Эти ограничения не отменяют найденные локальные дефекты и не закрывают release
acceptance. Продукт, зависимости, рабочая конфигурация и рабочие БД не менялись.
