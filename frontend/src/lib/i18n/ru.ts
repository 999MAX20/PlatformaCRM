import { leads } from "./ru/leads";
import { platform } from "./ru/platform";
import { commerce } from "./ru/commerce";
import { identity } from "./ru/identity";
import { support } from "./ru/support";
import { crm } from "./ru/crm";
import { business } from "./ru/business";
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
  ...leads,
  ...platform,
  ...commerce,
  ...identity,
  ...support,
  ...crm,
  ...business,
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
  "botDetail.previewCreated":
    "Диалог {conversation} создан. Заявка: {lead}. Сообщение появится в разделе сообщений.",

};
