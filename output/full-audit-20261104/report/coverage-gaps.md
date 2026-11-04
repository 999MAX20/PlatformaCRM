# Пробелы покрытия и ограничения

Файловый и статический аудит завершён. Этот файл сохраняет недоступные
динамические границы; наличие документа не превращает их в PASS.

## Завершённая локальная граница

Все127843 исходных пути сопоставлены с категорией и способом проверки;5734
собственных текстовых файла имеют завершённые dispositions. Требования1557,
UI3014 и все87 находок связаны с evidence; итоговый structural validator PASS.
Это не5734 новых теста и не3014 независимых клика. Новых выполнимых обычных
сценариев в итоговых реестрах не осталось;99 protected/external UI commands,
три protected migration-failure сценария и перечисленные ниже внешние проверки
сохраняют явную незакрытую динамическую границу.
Безопасное сохранение аудиторского пакета учитывается отдельно от проверки продукта.

## Ограничения выполнения

| ID | Что не доказано | Причина и доступная граница | Что потребуется для закрытия |
| --- | --- | --- | --- |
| ENV-SECURITY | Полный active-security проход и некоторые protected identity/authorization сценарии | Deep Scan не стартовал без managed filesystem permission profile. Последующий отказ автоматической проверки сообщён подзадачей без точной операции; заблокированное действие не повторялось. Выполнены безопасное полное чтение и допустимые обычные diagnostics, сохранены прежние exact-input tests | Доступный разрешённый security workflow и явный безопасный план оставшихся сценариев; текущий static-only статус не превращается в PASS |
| ENV-LINUX | Docker image, Linux runtime, UID/signals/graceful shutdown и startup нескольких replicas | Windows окружение; Docker engine отсутствует, WSL не содержит подходящих Django/psycopg/pip. Compose CLI merge проверяет конфигурацию без запуска контейнеров | Согласованный целевой/изолированный Linux runtime и image-specific acceptance |
| ENV-TARGET | Yandex topology, DNS/TLS/proxy/origins, storage ACL, реальные alerts/on-call, release/rollback | Deployment и инфраструктурные изменения не разрешены этим аудитом; целевая конфигурация не предоставлена как действующий стенд | Отдельно разрешённая target verification с точной версией и эксплуатационными ответственными |
| ENV-PROVIDERS | Live messages/webhooks, marketplace writes, email delivery, платежи/подписи/заказы | Реальные внешние эффекты и платные вызовы исключены. Local stubs, parser controls и source contracts проверяют только названные границы | Sandbox/live credentials и заранее разрешённые сценарии/получатели; безопасная reconciliation неизвестного результата |
| ENV-LLM | Реальная модель, качество RU/KK/mixed prompts, фактическая injection resistance в production | Синтетические/mock receipts и source grounding/approval tests не равны работе выбранной модели. Исторические три completion не являются CRM E2E | Разрешённый provider/model/version, fixtures и оценочные критерии; расходы и privacy отдельно согласованы |
| ENV-NATIVE | Сборка/установка/устройство, OS permissions, background lifecycle и push | Проверен исторический immutable source и отдельные actual-function/ORM reproductions; физическая platform среда отсутствует | Выбранный поддерживаемый native revision, device/emulator и действующий API contract |

Локальное восстановление PostgreSQL/Redis/worker/AV, dump/files/keys и scanner
outage/retry имеет собственные доказательства. Оно не подтверждает реальные RPO/RTO,
операторские права, production key custody и сохранность внешних provider effects.
Прежняя ошибка штатного recovery helper и первоначальный PostgreSQL teardown
остаются в результатах рядом с успешными изолированными повторными проверками.

## Разрывы продукта и решения

REQ01 (денежный контур плана) и REQ02 (ограниченный голосовой D01) — обнаруженные
разрывы реализации, а не причина прекратить чтение или проверку имеющегося продукта.
REQ04 касается будущего CRM↔Market обмена и не расширяет пилот автоматически.
Закрытие таких пунктов потребует отдельной реализации и её acceptance; аудит
не исправляет продукт и не утверждает новые фундаментальные решения.

В candidate dispositions отдельно остаются вопросы break-glass Django admin,
pricing freshness/repeated simulation, замены настроенных часов шаблоном и другие
неустановленные policy boundaries. Наблюдаемое поведение сохранено; отсутствие
решения не маскируется под подтверждённый дефект или молчаливое разрешение.
Точные основания находятся в backend/candidate-dispositions.json и матрице
требований. Новые вопросы владельцу не требуются для завершения независимой
разрешённой части аудита.
