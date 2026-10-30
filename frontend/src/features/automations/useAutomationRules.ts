import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { automationRulesApi } from "../../api/automations";

import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";

import type { AutomationRule } from "../../types";

export function useAutomationRules(
  business: ReturnType<typeof useActiveBusiness>["business"],
) {
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const automationRules = useQuery({
    queryKey: ["automation-rules", "workspace", business?.id, user?.id],
    queryFn: () => automationRulesApi.listPage(business!.id),
    enabled: Boolean(business?.id && user?.id),
  });
  const templates = useQuery({
    queryKey: ["automation-templates"],
    queryFn: automationRulesApi.templates,
  });
  const applyTemplateMutation = useMutation({
    mutationFn: ({
      templateKey,
      isActive,
    }: {
      templateKey: string;
      isActive: boolean;
    }) => {
      if (!business) throw new Error("Business is required.");
      return automationRulesApi.applyTemplate({
        business: business.id,
        template_key: templateKey,
        is_active: isActive,
      });
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["automation-rules"] }),
  });
  const toggleMutation = useMutation({
    mutationFn: ({
      rule,
      isActive,
    }: {
      rule: AutomationRule;
      isActive: boolean;
    }) =>
      automationRulesApi.update({
        id: rule.id,
        payload: { is_active: isActive },
      }),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: ["automation-rules"] }),
  });
  return { automationRules, templates, applyTemplateMutation, toggleMutation };
}
