import type { AutomationActionDraft, AutomationConditionDraft, AutomationRule } from "../../types";

export function conditionText(value: unknown): string {
  const expected = value && typeof value === "object" && "value" in value ? value.value : value;
  return typeof expected === "string" ? expected : JSON.stringify(expected) ?? "";
}

export function editedConditionValue(text: string): { value: unknown } {
  try { return { value: JSON.parse(text) }; }
  catch { return { value: text }; }
}

export function ruleEditorDraft(rule: AutomationRule) {
  return {
    form: { name: rule.name, trigger_type: rule.trigger_type, description: rule.description,
      is_active: rule.is_active, priority: rule.priority },
    conditions: (rule.conditions || []).map(item => ({
      field: String(item.field), operator: item.operator as AutomationConditionDraft["operator"],
      value: structuredClone(item.value), rawValue: conditionText(item.value),
    })),
    actions: (rule.actions || []).map(item => ({
      action_type: item.action_type as AutomationActionDraft["action_type"],
      config: structuredClone(item.config) as Record<string, unknown>, delay_seconds: Number(item.delay_seconds),
    })),
  };
}

export function localDateTimeValue(value: string): string {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16);
}

export function actionUserConfig(config: Record<string, unknown>, field: string, value: number | "") {
  const next = { ...config };
  for (const alias of ["user_id", "assignee_id", "owner_id", "recipient_id"]) delete next[alias];
  if (value !== "") next[field] = value;
  return next;
}
