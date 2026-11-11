import { timeline } from "./en/timeline";
import { importWorkspace } from "./en/importWorkspace";
import { voice } from "./en/voice";
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
  ...importWorkspace,
  ...voice,
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
  ...timeline,
  "notification.announcement": "Announcement",
  "notification.announcements": "Business announcements",
  "notification.myFeed": "My notifications",
  "notification.workItem": "Work notification",
  "notification.openCenter": "All notifications",
  "notification.publishAnnouncement": "Create announcement",
  "notification.publish": "Publish",
  "notification.published": "Announcement published",
  "notification.readAllResult": "Marked as read: {count}",
  "notification.announcementText": "Announcement text",
  "notification.audienceAll": "Recipients: all active business members at publication",
  "notification.priorityLabel": "Importance",
  "notification.recipients": "Recipients",
  "notification.opened": "Opened",
  "notification.readCount": "Read",
  "notification.acknowledged": "Acknowledged",
  "notification.acknowledge": "Acknowledge",
  "notification.markUnread": "Mark unread",
  "notification.monitoring": "Opens and acknowledgements",
  "notification.employee": "Employee",
  "notification.notYet": "—",
  "notification.noAnnouncements": "No announcements yet",
  "notification.noRecipients": "No recipients",
  "notification.revoked": "Revoked",
  "notification.revoke": "Revoke announcement",
  "notification.revokeQuestion": "Remove this announcement from personal feeds? Read and acknowledgement history will be retained.",
  "notification.pages": "Notification pages",
  "notification.previous": "Previous",
  "notification.next": "Next",
  "notification.work.tasks": "Task update",
  "notification.work.leads": "Lead update",
  "notification.work.deals": "Deal update",
  "notification.work.clients": "Client update",
  "notification.work.appointments": "Appointment update",
  "notification.work.conversations": "Conversation update",
  "notification.service.automations.started": "Automations: processing is delayed.",
  "notification.service.automations.recovered": "Automations: the processing delay has been resolved.",
  "notification.service.notifications.started": "Notifications: processing is delayed.",
  "notification.service.notifications.recovered": "Notifications: the processing delay has been resolved.",
  "notification.service.exports.started": "Export: processing is delayed.",
  "notification.service.exports.recovered": "Export: the processing delay has been resolved.",
  "notification.service.files.started": "File checks: processing is delayed.",
  "notification.service.files.recovered": "File checks: the processing delay has been resolved.",
  "records.loadFailed": "Could not load records",
  "records.loadFailedHint": "The records list is unavailable. Try loading it again.",
  "records.invalidFilters": "Check the selected filters and try loading again.",
  "notification.work.notifications": "Work update",
  "notification.work.settings": "Business settings update",
  "notification.work.integrations": "Integration update",
  "botDetail.previewCreated":
    "Conversation {conversation} created. The message will appear in Messages.",
};
