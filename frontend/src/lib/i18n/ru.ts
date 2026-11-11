import { timeline } from "./ru/timeline";
import { importWorkspace } from "./ru/importWorkspace";
import { voice } from "./ru/voice";
import { leads } from "./ru/leads";
import { platform } from "./ru/platform";
import { commerce } from "./ru/commerce";
import { identity } from "./ru/identity";
import { support } from "./ru/support";
import { crm } from "./ru/crm";
import { business } from "./ru/business";
import { management } from "./ru/management";
import { analytics } from "./ru/analytics";
import { core } from "./ru/core";
import { tasks } from "./ru/tasks";
import { settings } from "./ru/settings";
import { inbox } from "./ru/inbox";
import { dashboard } from "./ru/dashboard";
import { ai } from "./ru/ai";
import { aiAgents } from "./ru/aiAgents";
import { calendar } from "./ru/calendar";
import { automations } from "./ru/automations";
import { outreach } from "./ru/outreach";
import { integrations } from "./ru/integrations";
import { notifications } from "./ru/notifications";
import { clients } from "./ru/clients";
import { deals } from "./ru/deals";

export const ru: Record<string, string> = {
  ...importWorkspace,
  ...voice,
  ...leads,
  ...platform,
  ...commerce,
  ...identity,
  ...support,
  ...crm,
  ...business,
  ...management,
  ...analytics,
  ...core,
  ...tasks,
  ...settings,
  ...inbox,
  ...dashboard,
  ...ai,
  ...aiAgents,
  ...calendar,
  ...automations,
  ...outreach,
  ...integrations,
  ...notifications,
  ...clients,
  ...deals,
  ...timeline,
  "notification.announcement": "Объявление",
  "notification.announcements": "Объявления бизнеса",
  "notification.myFeed": "Мои уведомления",
  "notification.workItem": "Рабочее уведомление",
  "notification.openCenter": "Все уведомления",
  "notification.publishAnnouncement": "Создать объявление",
  "notification.publish": "Опубликовать",
  "notification.published": "Объявление опубликовано",
  "notification.readAllResult": "Отмечено прочитанными: {count}",
  "notification.announcementText": "Текст объявления",
  "notification.audienceAll": "Получатели: все действующие участники бизнеса на момент публикации",
  "notification.priorityLabel": "Важность",
  "notification.recipients": "Получатели",
  "notification.opened": "Открыто",
  "notification.readCount": "Прочитано",
  "notification.acknowledged": "Ознакомление подтверждено",
  "notification.acknowledge": "Подтвердить ознакомление",
  "notification.markUnread": "Отметить непрочитанным",
  "notification.monitoring": "Открытия и ознакомление",
  "notification.employee": "Сотрудник",
  "notification.notYet": "—",
  "notification.noAnnouncements": "Объявлений пока нет",
  "notification.noRecipients": "Получателей нет",
  "notification.revoked": "Отозвано",
  "notification.revoke": "Отозвать объявление",
  "notification.revokeQuestion": "Отозвать объявление из личных лент? История прочтения и ознакомления сохранится.",
  "notification.pages": "Страницы уведомлений",
  "notification.previous": "Назад",
  "notification.next": "Далее",
  "notification.work.tasks": "Обновление задачи",
  "notification.work.leads": "Обновление заявки",
  "notification.work.deals": "Обновление сделки",
  "notification.work.clients": "Обновление клиента",
  "notification.work.appointments": "Обновление записи",
  "notification.work.conversations": "Обновление диалога",
  "notification.service.automations.started": "Автоматизации: обработка задерживается.",
  "notification.service.automations.recovered": "Автоматизации: задержка обработки устранена.",
  "notification.service.notifications.started": "Уведомления: обработка задерживается.",
  "notification.service.notifications.recovered": "Уведомления: задержка обработки устранена.",
  "notification.service.exports.started": "Экспорт: обработка задерживается.",
  "notification.service.exports.recovered": "Экспорт: задержка обработки устранена.",
  "notification.service.files.started": "Проверка файлов: обработка задерживается.",
  "notification.service.files.recovered": "Проверка файлов: задержка обработки устранена.",
  "records.loadFailed": "Не удалось загрузить записи",
  "records.loadFailedHint": "Список записей недоступен. Повторите загрузку.",
  "records.invalidFilters": "Проверьте выбранные фильтры и повторите загрузку.",
  "notification.work.notifications": "Рабочее обновление",
  "notification.work.settings": "Обновление настроек бизнеса",
  "notification.work.integrations": "Обновление интеграции",
  "botDetail.previewCreated":
    "Диалог {conversation} создан. Сообщение появится в разделе сообщений.",
};
