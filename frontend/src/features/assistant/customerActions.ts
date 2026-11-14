import { autoPipelineFromSettings } from "./aiAgentsUtils";

export type CreationPolicy = "staff_confirmation" | "automatic";

export function customerActionsFromSettings(settings: Record<string, unknown>) {
  const previous = autoPipelineFromSettings(settings);
  const raw = settings.auto_crm_pipeline as Record<string, unknown> | undefined;
  const policy = (key: string): CreationPolicy =>
    (raw?.[key] ?? previous.creation_policy) === "automatic" ? "automatic" : "staff_confirmation";
  return {
    mode: "customer_actions" as const,
    enabled: previous.enabled && previous.mode !== "off",
    auto_send_reply: previous.auto_send_reply,
    create_appointment: previous.create_appointment,
    task_creation_policy: policy("task_creation_policy"),
    appointment_creation_policy: policy("appointment_creation_policy"),
    max_auto_reply_chars: previous.max_auto_reply_chars,
  };
}

export function customerActionsSettings(settings: Record<string, unknown>, patch: Partial<ReturnType<typeof customerActionsFromSettings>>) {
  const actions = { ...customerActionsFromSettings(settings), ...patch };
  return { ...settings, auto_crm_pipeline: { ...actions,
    creation_policy: actions.task_creation_policy === "automatic" || actions.appointment_creation_policy === "automatic"
      ? "automatic" : "staff_confirmation",
  } };
}
