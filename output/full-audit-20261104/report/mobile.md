# Responsive web и исторический native

Текущий web и историческая native-реализация проверяются раздельно. Восстановленные
исходники73482a3bea7f168113c58d8cb928214c97f032d5 не означают текущую опубликованную
сборку Android/iOS. Device acceptance, push delivery и store publication не выполнялись.

## Текущий web

Матрица1140 render cases покрыла95 маршрутов × RU/KK/EN × ширины320/390/768/1440.
В ней не наблюдалось document overflow или page errors; locale проверялся по
фактическому отображению. Это render/DOM/один Tab, а не выполнение каждого действия
или доказательство доступности всей клавиатурной навигации. Supplement276 cases
добавляет валидные параметры сущностей и роли. Settings supplement проверяет54
раздела и отдельное восстановление Billing после503 через Refresh.

Действия, ошибки, retry и focus проверяются дополнительно; точные границы и
результаты в [runtime-scenario-register.json](../ui/runtime-scenario-register.json).
Наличие responsive layout не устраняет подтверждённые функциональные дефекты:
частичный upload/segment save, потерю retry identity в Inbox, устаревший ответ
duplicate check, недоступное по правам действие и неполную локализацию. Эти случаи
сохраняются как отдельные находки, без утверждения, что они возникают только на телефоне.

## Native: сохранённые находки и расширение проверки

| Сценарий исторической версии | Результат и граница |
| --- | --- |
| Очередь actorA после logout исполняется с авторизацией actorB | Сохранён MOB-H01; синтетические tokens/fetch, без серверной мутации |
| Объявленная HTTPS deep link теряет task target | Подтверждён MOB-H02; custom scheme control работает |
| Capacity eviction и конкурентные enqueue/replay | MOB-H03 дополнен двумя воспроизведёнными lost-update сценариями |
| Временный refresh503 | Клиент очищает session и возвращает Login; отдельный recovery defect |
| Два одновременных refresh | Два вызова подтверждены; последствия server rotation отдельно не доказаны |
| Порядок newest-first | Алгоритм подтверждён; вредный результат зависимых команд этим тестом не установлен |
| Истёкшая idempotency receipt | Реальный isolated ORM: старый unique tuple остаётся, повтор вызывает IntegrityError |
| Повтор успешной task command с прежней версией | View проверяет stale_state раньше receipt replay:200 затем409 |

Полные исходные hashes, diagnostics и различия между in-memory transpilation,
fake AsyncStorage/fetch и Django ORM adapters:
[native-function-validation.json](../ui/native-function-validation.json),
[native-idempotency-validation.json](../ui/native-idempotency-validation.json),
[независимая проверка](../native-independent-review.md).
Тесты, ожидающие наблюдаемый дефект, не являются продуктовым acceptance PASS.

Перед повторным использованием native нужны actor/Business-bound durable queue,
контроль capacity, конкурентные enqueue/replay, однозначная обработка unknown
outcome, корректный receipt replay и восстановление после временной недоступности
refresh. Отдельно нужны PostgreSQL concurrency и реальная platform/device проверка.
Этот аудит не утверждает, что исторические API доступны в текущем web deployment.
