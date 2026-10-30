import { type BadgeVariant } from "../../components/ui/Badge";

import type { AutomationActionDraft, AutomationRun } from "../../types";
export const triggerKeys = [
  { value: "lead_created", labelKey: "automations.trigger.leadCreated" },
  {
    value: "lead_status_changed",
    labelKey: "automations.trigger.leadStatusChanged",
  },
  {
    value: "deal_stage_changed",
    labelKey: "automations.trigger.dealStageChanged",
  },
  { value: "deal_created", labelKey: "automations.trigger.dealCreated" },
  { value: "stage_changed", labelKey: "automations.trigger.stageChanged" },
  {
    value: "message_received",
    labelKey: "automations.trigger.messageReceived",
  },
  {
    value: "bot_message_received",
    labelKey: "automations.trigger.botMessageReceived",
  },
  {
    value: "conversation_unread",
    labelKey: "automations.trigger.conversationUnread",
  },
  {
    value: "appointment_created",
    labelKey: "automations.trigger.appointmentCreated",
  },
  {
    value: "appointment_cancelled",
    labelKey: "automations.trigger.appointmentCancelled",
  },
  {
    value: "appointment_completed",
    labelKey: "automations.trigger.appointmentCompleted",
  },
  { value: "task_overdue", labelKey: "automations.trigger.taskOverdue" },
];

export const conditionOperators = [
  { value: "eq", label: "=" },
  { value: "contains", label: "contains" },
  { value: "gt", label: ">" },
  { value: "lt", label: "<" },
  { value: "in", label: "in" },
];

export const actionOptionKeys = [
  { value: "create_task", labelKey: "automations.action.createTask" },
  {
    value: "create_notification",
    labelKey: "automations.action.createNotification",
  },
  { value: "assign_user", labelKey: "automations.action.assignUser" },
  { value: "add_note", labelKey: "automations.action.addNote" },
  { value: "create_follow_up", labelKey: "automations.action.createFollowUp" },
  { value: "wait", labelKey: "automations.action.wait" },
];

export const localeByLanguage = {
  ru: "ru-RU",
  kk: "kk-KZ",
  en: "en-US",
};

export function defaultActions(t: (key: string) => string) {
  const title = t("automations.defaultTaskTitle");
  return [
    {
      action_type: "create_task",
      config: { title },
      delay_seconds: 0,
    },
  ] as AutomationActionDraft[];
}

export function formatJson(value: unknown) {
  return JSON.stringify(value ?? {}, null, 2);
}

export function canCancelRun(run: AutomationRun) {
  return [
    "pending",
    "running",
    "waiting",
    "retry_scheduled",
    "failed",
  ].includes(run.status);
}

export function canRetryRun(run: AutomationRun) {
  return run.status === "failed" || run.status === "cancelled";
}

export const runStatuses = ["pending", "running", "waiting", "retry_scheduled", "success", "failed", "skipped", "cancelled", "error", "blocked"];

export function runStatusVariant(status?: string): BadgeVariant {
  if (["success", "succeeded", "completed", "processed"].includes(status || ""))
    return "success";
  if (
    ["pending", "queued", "running", "waiting", "retry_scheduled"].includes(
      status || "",
    )
  )
    return "warning";
  if (["failed", "error", "cancelled", "blocked"].includes(status || ""))
    return "danger";
  return "neutral";
}

export function runStatusLabel(
  status: string | undefined,
  t: (key: string) => string,
) {
  if (!status) return "-";
  if (runStatuses.includes(status)) return t(`automations.runStatus.${status}`);
  if (status === "waiting" || status === "retry_scheduled")
    return t("status.pending");
  if (status === "success" || status === "cancelled")
    return t(`status.${status}`);
  const statusKey =
    status === "completed"
      ? "status.completed"
      : `integrations.status.${status}`;
  const label = t(statusKey);
  return label === statusKey ? status : label;
}
