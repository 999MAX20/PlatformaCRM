import { apiClient } from "./client";
import axios from "axios";
import { createCrudApi } from "./crud";
import type { AutomationPreview, AutomationRule, AutomationRun, AutomationTemplate, Id, ManualAutomationRulePayload } from "../types";

export function automationActionErrors(error: unknown): Record<number, string[]> {
  if (!axios.isAxiosError(error)) return {};
  const actions: unknown = error.response?.data?.errors?.actions;
  if (!actions || typeof actions !== "object") return {};
  return Object.fromEntries(Object.entries(actions).map(([index, value]) => {
    const item = value && typeof value === "object" ? value as Record<string, unknown> : {};
    const config = item.config && typeof item.config === "object" ? item.config as Record<string, unknown> : {};
    return [Number(index), [...Object.keys(item), ...Object.keys(config)]];
  }).filter(([index]) => Number.isInteger(index)));
}

export const automationRulesApi = {
  ...createCrudApi<AutomationRule>("/api/automation-rules/"),
  templates: async () => {
    const { data } = await apiClient.get<AutomationTemplate[]>("/api/automation-rules/templates/");
    return data;
  },
  applyTemplate: async ({ business, template_key, is_active = false }: { business: Id; template_key: string; is_active?: boolean }) => {
    const { data } = await apiClient.post<AutomationRule>("/api/automation-rules/apply-template/", {
      business,
      template_key,
      is_active,
    });
    return data;
  },
  previewManual: async (payload: ManualAutomationRulePayload) => {
    const { data } = await apiClient.post<AutomationPreview>("/api/automation-rules/preview/", payload);
    return data;
  },
  createManual: async (payload: ManualAutomationRulePayload) => {
    const { data } = await apiClient.post<AutomationRule>("/api/automation-rules/create-manual/", payload);
    return data;
  },
};

export const automationRunsApi = {
  ...createCrudApi<AutomationRun>("/api/automation-runs/"),
  retry: async (id: Id) => {
    const { data } = await apiClient.post<AutomationRun>(`/api/automation-runs/${id}/retry/`);
    return data;
  },
  cancel: async (id: Id) => {
    const { data } = await apiClient.post<AutomationRun>(`/api/automation-runs/${id}/cancel/`);
    return data;
  },
};
