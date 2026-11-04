# Производительность

Главный подтверждённый риск сохраняется в Clients: на синтетическом наборе в
1 000 строк на домен страница достигает десятков секунд. Новый PostgreSQL burst
и soak расширяют PERF02; успешный HTTP200 после длительного ожидания не считается
приемлемым временем ответа.

| Проверка | Наблюдение |
| --- | --- |
| Burst, 10 параллельных клиентов, 50 запросов | 40 HTTP200; 10 Clients deadline failures при10s |
| Первый soak, 2 клиента, 606s | 109/110 HTTP200; один Clients deadline60s; ресурсный sampler ошибся |
| Исправленный audit sampler, новый soak625s | 120/120 HTTP200; aggregate successful p95 51,504s |
| Recovery после нового soak | 5/5 HTTP200; Clients40,665s |

В исправленном прогоне RSS приложения изменился с127,3 до137,8MB, sampled peak
138,1MB; PostgreSQL tree — с186,8 до341,4MB, peak498,6MB. Смена процессов подключений
влияет на суммарный RSS. Эти данные не доказывают утечку памяти; десятиминутный
прогон не заменяет длительное production-наблюдение. Windows Django dev server,
изолированные PostgreSQL17/Redis и конкретная fixture ограничивают переносимость.

Ошибка первого sampler сохранена; исправлялся только диагностический helper,
затем выполнен его concurrent self-test и новый изолированный прогон. Исходные
HTTP deadlines не исчезают из результата. Полные параметры, samples, CPU, cleanup
и связь с прежними SQLite/distributed/query-count измерениями:
[extended load evidence](../performance-results.md).

Приоритет исправления: оптимизировать Clients page/count/summary/facets при
сохранении Business/actor scope и точности результатов; затем N+1 карточки и
рабочих очередей PERF01/PERF03. Приёмка должна повторять сопоставимые наборы,
профиль запросов и планы SQL с положительными/отрицательными проверками доступа.
Общий межпользовательский cache или удаление permission checks не являются
допустимым способом ускорения. Новые пределы SLO этот аудит не придумывает.

Дополнительные изолированные SQLite измерения проверили семь узких сценариев
на растущих синтетических наборах. Они дополняют HTTP/PG профиль и не заменяют его:

| Helper / объём | SQL count | Вывод |
| --- | --- | --- |
| usage_summary для1/10/25 Business | 11/110/275 | Линейный рост в компоненте platform list; не измерение всего privileged endpoint |
| branch slots при1/4/12 часах, без занятых слотов | 9/15/31 | Conflict lookup на каждый кандидат; сложная занятость/переезды не измерены |
| VisitPlan с1/20/100 шагами | selector2, полная owner projection4 во всех трёх случаях | N+1 в этой комбинации не подтверждён |
| Client card с1/20/100 overdue tasks | 29/27/27 | Ограниченная task-only fixture не опровергает PERF03 на других связанных доменах |
| Work queue limit10 с1/20/100 tasks | 40/103/103 | Ограничение страницы останавливает дальнейший рост;103 queries остаются стоимостью этой страницы |
| Первые10 notifications при1/20/100 строках | 6/5/5 | SQL count ограничен, но source materializes candidate IDs до slicing |

Root прочитал полный diagnostic и результаты, usage_summary и фактические callers,
а также personal_states. Reused owner object/caches ограничивают сравнение времени;
dictionary result_count у card/queue означает число ключей, а не число сущностей.
Небольшой набор100 notifications не доказывает утечку памяти или outage. Нельзя
убрать permission filtering для ускорения materialization.

Первый проход остановил один тест на неправильном URL fixture; исходный FAIL
сохранён, исправлен только diagnostic route, затем повторён затронутый тест.
21 usable observations и исходный исключённый результат:
[helper-performance-results.json](../backend/helper-performance-results.json),
[команды и ограничения](../backend/performance-boundaries.md).
