import { ru } from "./ru";
import { leads } from "./en/leads";
import { platform } from "./en/platform";
import { commerce } from "./en/commerce";
import { identity } from "./en/identity";
import { support } from "./en/support";
import { crm } from "./en/crm";
import { business } from "./en/business";
import { analytics } from "./en/analytics";
import { core } from "./en/core";
import { tasks } from "./en/tasks";
import { settings } from "./en/settings";
import { inbox } from "./en/inbox";
import { dashboard } from "./en/dashboard";
import { ai } from "./en/ai";
import { aiAgents } from "./en/aiAgents";
import { calendar } from "./en/calendar";
import { automations } from "./en/automations";
import { outreach } from "./en/outreach";
import { integrations } from "./en/integrations";
import { notifications } from "./en/notifications";
import { clients } from "./en/clients";
import { deals } from "./en/deals";

export const en: Record<string, string> = {
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
    "Conversation {conversation} created. Lead: {lead}. The message will appear in Messages.",

};
