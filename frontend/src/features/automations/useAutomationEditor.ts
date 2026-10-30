import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
  automationActionErrors,
  automationRulesApi,
} from "../../api/automations";
import { teamApi } from "../../api/team";

import { ruleEditorDraft } from "./editorDraft";

import { getApiErrorMessage } from "../../api/client";

import { useActiveBusiness } from "../../hooks/useBusiness";

import { useI18n } from "../../lib/i18n";
import type {
  AutomationActionDraft,
  AutomationConditionDraft,
  AutomationPreview,
  AutomationRule,
  ManualAutomationRulePayload,
} from "../../types";
import { defaultActions } from "./automationPresentation";
export function useAutomationEditor(
  business: ReturnType<typeof useActiveBusiness>["business"],
  canUpdate: boolean,
) {
  const { t } = useI18n();
  const queryClient = useQueryClient();
  const [createOpen, setCreateOpen] = useState(false);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const editorSession = useRef(0);
  const [editingRuleId, setEditingRuleId] = useState<number | null>(null);
  const [editorLoading, setEditorLoading] = useState(false);
  const [editorLoadError, setEditorLoadError] = useState<unknown>(null);
  useEffect(() => {
    editorSession.current += 1;
    setAdvancedOpen(false);
    setCreateOpen(false);
  }, [business?.id]);
  const [form, setForm] = useState({
    name: "",
    trigger_type: "lead_created",
    description: "",
  });
  const [advancedForm, setAdvancedForm] = useState({
    name: "",
    trigger_type: "lead_created",
    description: "",
    is_active: false,
    priority: 100,
  });
  const [conditions, setConditions] = useState<
    Array<AutomationConditionDraft & { rawValue: string }>
  >([]);
  const [actions, setActions] = useState<AutomationActionDraft[]>(() =>
    defaultActions(t),
  );
  const [preview, setPreview] = useState<AutomationPreview | null>(null);
  const [previewSignature, setPreviewSignature] = useState("");
  const [actionErrors, setActionErrors] = useState<Record<number, string[]>>(
    {},
  );
  const members = useQuery({
    queryKey: ["automation-members", business?.id],
    queryFn: () => teamApi.allMembers(business?.id),
    enabled: advancedOpen && Boolean(business),
  });
  const draftSignature = JSON.stringify({
    advancedForm,
    conditions,
    actions,
    business: business?.id,
    editingRuleId,
    session: editorSession.current,
  });
  const validPreview = previewSignature === draftSignature ? preview : null;
  const [advancedError, setAdvancedError] = useState<string | null>(null);
  const mutation = useMutation({
    mutationFn: (payload: Partial<AutomationRule>) =>
      automationRulesApi.create(payload),
    onSuccess: (rule) => {
      queryClient.invalidateQueries({ queryKey: ["automation-rules"] });
      setCreateOpen(false);
      setForm({ name: "", trigger_type: "lead_created", description: "" });
      if (canUpdate) void openEditor(rule.id);
    },
  });
  const previewMutation = useMutation({
    mutationFn: async ({
      payload,
      signature,
      id,
      session,
    }: {
      payload: ManualAutomationRulePayload;
      signature: string;
      id: number | null;
      session: number;
    }) => ({
      data: await (id
        ? automationRulesApi.previewConfiguration(id, payload)
        : automationRulesApi.previewManual(payload)),
      signature,
      session,
    }),
    onSuccess: ({ data, signature, session }) => {
      if (session !== editorSession.current) return;
      setPreview(data);
      setPreviewSignature(signature);
      setActionErrors({});
      setAdvancedError(null);
    },
    onError: (error, variables) => {
      if (variables.session !== editorSession.current) return;
      setPreview(null);
      setActionErrors(automationActionErrors(error));
      setAdvancedError(getApiErrorMessage(error, t));
    },
  });
  const createManualMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number | null;
      payload: ManualAutomationRulePayload;
      session: number;
    }) =>
      id
        ? automationRulesApi.saveConfiguration(id, payload)
        : automationRulesApi.createManual(payload),
    onSuccess: (_rule, variables) => {
      queryClient.invalidateQueries({ queryKey: ["automation-rules"] });
      if (variables.session !== editorSession.current) return;
      editorSession.current += 1;
      setAdvancedOpen(false);
      setPreview(null);
      setAdvancedError(null);
    },
    onError: (error, variables) => {
      if (variables.session !== editorSession.current) return;
      setActionErrors(automationActionErrors(error));
      setAdvancedError(getApiErrorMessage(error, t));
    },
  });
  async function openEditor(id: number | null = null) {
    const session = ++editorSession.current;
    setEditingRuleId(id);
    setAdvancedOpen(true);
    setPreview(null);
    setAdvancedError(null);
    setActionErrors({});
    setEditorLoadError(null);
    setEditorLoading(Boolean(id));
    if (id === null) {
      setAdvancedForm({
        name: "",
        trigger_type: "lead_created",
        description: "",
        is_active: false,
        priority: 100,
      });
      setConditions([]);
      setActions(defaultActions(t));
      return;
    }
    try {
      const rule = await automationRulesApi.get(id);
      if (session !== editorSession.current) return;
      if (rule.business !== business?.id)
        throw new Error("Rule context changed.");
      const draft = ruleEditorDraft(rule);
      setAdvancedForm(draft.form);
      setConditions(draft.conditions);
      setActions(draft.actions.length ? draft.actions : defaultActions(t));
    } catch (error) {
      if (session === editorSession.current) setEditorLoadError(error);
    } finally {
      if (session === editorSession.current) setEditorLoading(false);
    }
  }
  function closeEditor() {
    if (createManualMutation.isPending) return;
    editorSession.current += 1;
    setAdvancedOpen(false);
  }
  function buildManualPayload(): ManualAutomationRulePayload {
    if (!business) throw new Error("Business is required.");
    return {
      business: business.id,
      name: advancedForm.name,
      trigger_type: advancedForm.trigger_type,
      description: advancedForm.description,
      is_active: advancedForm.is_active,
      priority: advancedForm.priority,
      conditions: conditions.map((condition) => ({
        field: condition.field,
        operator: condition.operator,
        value: condition.value,
      })),
      actions: actions.map((action) => ({
        action_type: action.action_type,
        config: action.config,
        delay_seconds: Number(action.delay_seconds || 0),
      })),
    };
  }
  return {
    createOpen,
    setCreateOpen,
    advancedOpen,
    setAdvancedOpen,
    editorSession,
    editingRuleId,
    setEditingRuleId,
    editorLoading,
    setEditorLoading,
    editorLoadError,
    setEditorLoadError,
    form,
    setForm,
    advancedForm,
    setAdvancedForm,
    conditions,
    setConditions,
    actions,
    setActions,
    preview,
    setPreview,
    previewSignature,
    setPreviewSignature,
    actionErrors,
    setActionErrors,
    members,
    draftSignature,
    validPreview,
    advancedError,
    setAdvancedError,
    mutation,
    previewMutation,
    createManualMutation,
    openEditor,
    closeEditor,
    buildManualPayload,
  };
}
