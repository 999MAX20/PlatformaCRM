import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { customFieldsApi } from "../../api/customFields";

import { useActiveBusiness } from "../../hooks/useBusiness";

import type { CustomFieldDefinition, Id } from "../../types";

type Context = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  canManageSettings: boolean;
  activeSettingsSection: string;
  allowedSettingsSectionIds: Set<string>;
  queryClient: ReturnType<typeof useQueryClient>;
};

export function useSettingsCustomFields({ business, canManageSettings, activeSettingsSection, allowedSettingsSectionIds, queryClient }: Context) {
const customFields = useQuery({
    queryKey: ["custom-fields", business?.id],
    queryFn: () => customFieldsApi.listAll({ business: business?.id }),
    enabled: activeSettingsSection === "custom-fields" && Boolean(
      business &&
      canManageSettings &&
      allowedSettingsSectionIds.has("custom-fields"),
    ),
  });

const updateCustomFieldMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: Id;
      payload: Partial<CustomFieldDefinition>;
    }) => customFieldsApi.update({ id, payload }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-fields"] });
    },
  });

const removeCustomFieldMutation = useMutation({
    mutationFn: (id: Id) => customFieldsApi.remove(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["custom-fields"] });
    },
  });
return { customFields, updateCustomFieldMutation, removeCustomFieldMutation };
}
