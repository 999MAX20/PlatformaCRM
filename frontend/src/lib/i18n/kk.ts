import { medical } from "./kk/medical";
import { timeline } from "./kk/timeline";
import { googleSheets } from "./kk/googleSheets";
import { importWorkspace } from "./kk/importWorkspace";
import { voice } from "./kk/voice";
import { ru } from "./ru";
import { leads } from "./kk/leads";
import { platform } from "./kk/platform";
import { commerce } from "./kk/commerce";
import { identity } from "./kk/identity";
import { support } from "./kk/support";
import { crm } from "./kk/crm";
import { business } from "./kk/business";
import { management } from "./kk/management";
import { analytics } from "./kk/analytics";
import { core } from "./kk/core";
import { tasks } from "./kk/tasks";
import { settings } from "./kk/settings";
import { inbox } from "./kk/inbox";
import { dashboard } from "./kk/dashboard";
import { ai } from "./kk/ai";
import { aiAgents } from "./kk/aiAgents";
import { calendar } from "./kk/calendar";
import { automations } from "./kk/automations";
import { outreach } from "./kk/outreach";
import { integrations } from "./kk/integrations";
import { notifications } from "./kk/notifications";
import { clients } from "./kk/clients";
import { deals } from "./kk/deals";

export const kk: Record<string, string> = {
  ...ru,
  ...medical,
  ...googleSheets,
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
  "notification.announcement": "Хабарландыру",
  "notification.announcements": "Бизнес хабарландырулары",
  "notification.myFeed": "Менің хабарламаларым",
  "notification.workItem": "Жұмыс хабарламасы",
  "notification.openCenter": "Барлық хабарламалар",
  "notification.publishAnnouncement": "Хабарландыру жасау",
  "notification.publish": "Жариялау",
  "notification.published": "Хабарландыру жарияланды",
  "notification.readAllResult": "Оқылды деп белгіленді: {count}",
  "notification.announcementText": "Хабарландыру мәтіні",
  "notification.audienceAll": "Алушылар: жариялау сәтіндегі бизнестің барлық белсенді қатысушылары",
  "notification.priorityLabel": "Маңыздылық",
  "notification.recipients": "Алушылар",
  "notification.opened": "Ашылды",
  "notification.readCount": "Оқылды",
  "notification.acknowledged": "Танысу расталды",
  "notification.acknowledge": "Танысуды растау",
  "notification.markUnread": "Оқылмаған деп белгілеу",
  "notification.monitoring": "Ашу және танысу",
  "notification.employee": "Қызметкер",
  "notification.notYet": "—",
  "notification.noAnnouncements": "Әзірге хабарландыру жоқ",
  "notification.noRecipients": "Алушылар жоқ",
  "notification.revoked": "Кері қайтарылды",
  "notification.revoke": "Хабарландыруды кері қайтару",
  "notification.revokeQuestion": "Хабарландыруды жеке таспалардан алып тастау керек пе? Оқу және танысу тарихы сақталады.",
  "notification.pages": "Хабарлама беттері",
  "notification.previous": "Артқа",
  "notification.next": "Келесі",
  "notification.work.tasks": "Тапсырма жаңартылды",
  "notification.work.leads": "Өтінім жаңартылды",
  "notification.work.deals": "Мәміле жаңартылды",
  "notification.work.clients": "Клиент жаңартылды",
  "notification.work.appointments": "Жазылу жаңартылды",
  "notification.work.conversations": "Диалог жаңартылды",
  "notification.service.automations.started": "Автоматтандыру: өңдеу кешігуде.",
  "notification.service.automations.recovered": "Автоматтандыру: өңдеу кідірісі жойылды.",
  "notification.service.notifications.started": "Хабарландырулар: өңдеу кешігуде.",
  "notification.service.notifications.recovered": "Хабарландырулар: өңдеу кідірісі жойылды.",
  "notification.service.exports.started": "Экспорт: өңдеу кешігуде.",
  "notification.service.exports.recovered": "Экспорт: өңдеу кідірісі жойылды.",
  "notification.service.files.started": "Файлдарды тексеру: өңдеу кешігуде.",
  "notification.service.files.recovered": "Файлдарды тексеру: өңдеу кідірісі жойылды.",
  "records.loadFailed": "Жазбалар жүктелмеді",
  "records.loadFailedHint": "Жазбалар тізімі қолжетімсіз. Қайта жүктеп көріңіз.",
  "records.invalidFilters": "Таңдалған сүзгілерді тексеріп, қайта жүктеңіз.",
  "notification.work.notifications": "Жұмыс жаңартуы",
  "notification.work.settings": "Бизнес баптаулары жаңартылды",
  "notification.work.integrations": "Интеграция жаңартылды",
  "botDetail.previewCreated":
    "Диалог {conversation} жасалды. Хабар хабарламалар бөлімінде пайда болады.",
};
