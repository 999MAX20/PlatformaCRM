# Сверка поручения с доказательствами

Статус: **файловый и статический аудит завершён; динамическая проверка ограничена
перечисленными средами и сценариями**. Структурные проверки не подменяют
семантическое чтение, runtime evidence и открытые acceptance criteria.

| Раздел поручения | Доказательства | Текущая граница |
| --- | --- | --- |
| 1. Цель и результат | [baseline](baseline.md), [findings](findings.md), [план](remediation-plan.md) | 87 находок; все19 разделов сопоставлены; внешняя приёмка остаётся открытой |
| 2. Объект и полномочия | [план аудита](../PLAN.md), [исходное поручение](../OWNER-SCOPE.md) | CRM canonical tree; Market только cross-contract; без product fixes/workingDB/push/deploy |
| 3. Проверяемое состояние | [baseline](baseline.md), [global identity](../global-review-validation.json), [cross-contract hashes](../cross-contract-reuse.json) | 5734 own-text identities проверены:5729 unchanged,5 точных собственные docs deltas; product drift отсутствует |
| 4. Каждый файл | [inventory](../file-inventory-refined.csv), [file review](../file-review.csv) | 127843/127843 уникальных пути;5734 own-text; незавершённых reading dispositions0 |
| 5. Карта реализации | [architecture](architecture.md), [backend module registry](../backend/module-registry.json), [root architecture](../architecture-root.md) | 941 backend modules,413 process modules,976 API operations,17jobs,95routes,3014 UI instances |
| 6. Требования и процессы | [business processes](business-processes.md), [requirements source ledger](../requirements/document-ledger.json) | 1557 source statement traces;126 named CRM IDs;14 pilot AC; статусы/разрывы сохранены |
| 7. Backend/данные | [backend coverage](../backend/coverage-validation.json), [transitions](../backend/semantic-transition-validation.json), [tests](tests.md) | Full-read2079 assigned paths; SQLite/PG и static/security limits различаются |
| 8. Frontend | [UI current inventory](../ui/inventory-current.json), [route/action/state source](../ui/route-action-state-static.json) | 3014 exact instances reconciled;1140 renders+276 parameter/role cases;99 protected/external commands не исполнялись заново |
| 9. Сквозные сценарии | [transitions](../backend/semantic-transition-registry.json), [booking](../backend/booking-automation-results.json), [recovery](operations.md) | Named guards/effects и UI/API/job связи сверены; mock/isolated/reused/external границы различаются |
| 10. Security | [security](security.md), [passive review](../passive-review.md), [независимый archive review](../backend/archive-independent-review.md) | Safe static/retained tests завершены в названных границах; ENV-SEC/live/model gaps не PASS |
| 11. Производительность | [performance](performance.md), [helper measurements](../backend/performance-boundaries.md) | Small/heavy/distributed, HTTP burst/soak/recovery; timeout/ошибка sampler сохранены |
| 12. Mobile | [mobile](mobile.md), [native review](../native-independent-review.md) | Исторический immutable source и synthetic execution; ENV-NATIVE остаётся |
| 13. Эксплуатация | [operations](operations.md), [queue topology](../queue-topology.csv) | Local isolated recovery/Compose merge; target/Linux/live checks остаются |
| 14. Документация | [document ledger](../requirements/document-ledger.json) | 1162 document entries reconciled;4 неточности исправлены в2 текущих документах; foreign WIP не включается в собственные коммиты |
| 15. Прежние29 | [prior findings](prior-findings.md), [normalized29](../backend/prior-findings-normalized.json) | Все ID сохранены; текущий join учитывает exact inputs, partial docs и historical native |
| 16. Организация | [root checkpoint](../ROOT-CHECKPOINT.md), [plan](../PLAN.md) | Тот же scope, независимые reviews и локальные evidence; без сообщений другим чатам |
| 17. Артефакты | Файлы текущего report и связанные registries | README, все запрошенные реестры и отчёты доступны; состав локального сохранения указан отдельно в documentation.md |
| 18. Полнота | [final global validator](../global-review-validation-final.json), [remediation mapping](../remediation-mapping-validation.json) | COVERAGE_REGISTRY_PASS, ошибок0; это не полный динамический PASS |
| 19. Ответ владельцу | Итог владельцу должен сохранять выводы, ошибки и6 внешних границ; отчёт не является разрешением исправлений | Финальный ответ не подменяется этим checkpoint |

Технические внешние ограничения перечислены в [coverage-gaps.md](coverage-gaps.md).
Оставшаяся локальная работа в таблице не переименовывается во внешний блокер.
Реестры не содержат молча пропущенных исходных файлов или неразобранных кандидатов.
Недоступное выполнение не объявлено успешным: external/security/device границы
и99 command instances сохранены. Общий release PASS не выводится из validators.
