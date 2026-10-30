import { ru } from "./ru";
import { leads } from "./kk/leads";
import { platform } from "./kk/platform";
import { commerce } from "./kk/commerce";
import { identity } from "./kk/identity";
import { support } from "./kk/support";
import { crm } from "./kk/crm";
import { business } from "./kk/business";
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
    "Диалог {conversation} жасалды. Өтінім: {lead}. Хабар хабарламалар бөлімінде пайда болады.",

};
