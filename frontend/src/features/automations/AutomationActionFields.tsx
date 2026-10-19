import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import type { AutomationActionDraft, TeamMember } from "../../types";
import { actionUserConfig, localDateTimeValue } from "./editorDraft";

export function AutomationActionFields({ action, onChange, members, membersLoading, invalidFields = [] }: {
  action: AutomationActionDraft;
  onChange: (config: Record<string, unknown>) => void;
  members: TeamMember[];
  membersLoading: boolean;
  invalidFields?: string[];
}) {
  const { t } = useI18n();
  const config = action.config;
  const update = (field: string, value: unknown) => {
    const next = { ...config };
    if (value === "" || value === undefined) delete next[field];
    else next[field] = value;
    onChange(next);
  };
  const text = (field: string) => String(config[field] ?? "");
  const error = (field: string) => invalidFields.includes(field) ? t("automations.fieldInvalid") : undefined;
  const userField = action.action_type === "assign_user" ? "user_id" : action.action_type === "create_notification" ? "recipient_id" : "assignee_id";
  const userOptions = [
    { value: "", label: t(action.action_type === "assign_user" ? "automations.selectUser" : "automations.automaticUser") },
    ...members.filter(member => member.is_active)
      .map(member => ({ value: member.user.id, label: member.user.full_name || member.user.email })),
  ];
  const task = action.action_type === "create_task" || action.action_type === "create_follow_up";
  const notification = action.action_type === "create_notification";
  const priorityOptions = ["low", "normal", "high", "urgent"].map(value => ({ value, label: t(`taskWorkspace.priority.${value}`) }));
  if (action.action_type === "wait") return null;
  return <div className="mt-3 grid min-w-0 grid-cols-1 gap-3 md:grid-cols-2 [&>*]:min-w-0">
    {task ? <>
      <Input label={t("automations.taskTitle")} maxLength={255} value={text("title")} error={error("title")} onChange={event => update("title", event.target.value)} />
      <Select label={t("tasks.priority")} value={text("priority") || "normal"} options={priorityOptions} error={error("priority")} onChange={event => update("priority", event.target.value)} />
      <Textarea label={t("automations.descriptionLabel")} value={text("description")} error={error("description")} onChange={event => update("description", event.target.value)} />
      <Input label={t("automations.dueAt")} type="datetime-local" value={localDateTimeValue(text("due_at"))} error={error("due_at")} onChange={event => update("due_at", event.target.value ? new Date(event.target.value).toISOString() : "")} />
      {action.action_type === "create_follow_up" ? <Input label={t("automations.dueInDays")} type="number" min={1} step={1} value={text("due_in_days") || 1} error={error("due_in_days")} onChange={event => update("due_in_days", event.target.value ? Number(event.target.value) : "")} /> : null}
    </> : null}
    {notification || action.action_type === "add_note" ? <Textarea label={t("automations.actionText")} value={text("text")} error={error("text")} onChange={event => update("text", event.target.value)} /> : null}
    {task || notification || action.action_type === "assign_user" ? <Select
      label={t(notification ? "automations.recipient" : "tasks.assignee")} value={String(config[userField] ?? config.user_id ?? config.assignee_id ?? config.owner_id ?? "")}
      options={userOptions} disabled={membersLoading} error={error(userField)}
      onChange={event => onChange(actionUserConfig(config, userField, event.target.value ? Number(event.target.value) : ""))}
    /> : null}
    {notification ? <>
      <Select label={t("automations.channel")} value={text("channel") || "system"}
        options={["system", "email", "telegram", "whatsapp"].map(value => ({ value, label: t(`automations.channel.${value}`) }))}
        error={error("channel")} onChange={event => update("channel", event.target.value)} />
      <Select label={t("automations.category")} value={text("category") || "sales"}
        options={["sales", "finance", "system", "ai_alerts", "outreach", "tasks"].map(value => ({ value, label: t(`settings.notifications.category.${value === "ai_alerts" ? "aiAlerts" : value}`) }))}
        error={error("category")} onChange={event => update("category", event.target.value)} />
      <Select label={t("tasks.priority")} value={text("priority") || "normal"} options={priorityOptions} error={error("priority")} onChange={event => update("priority", event.target.value)} />
      <Input label={t("automations.actionUrl")} maxLength={255} value={text("action_url")} error={error("action_url")} onChange={event => update("action_url", event.target.value)} />
      <Input label={t("automations.actionLabel")} maxLength={64} value={text("action_label")} error={error("action_label")} onChange={event => update("action_label", event.target.value)} />
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={config.include_owner === true} onChange={event => update("include_owner", event.target.checked)} />{t("automations.includeOwner")}</label>
    </> : null}
  </div>;
}
