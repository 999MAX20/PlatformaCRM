import { apiClient, unwrapList } from "./client";
import { createCrudApi } from "./crud";
import type { CustomFieldEntityType, CustomFieldDefinition, CustomFieldValue, Id } from "../types";

export const customFieldsApi = {
  ...createCrudApi<CustomFieldDefinition>("/api/custom-fields/"),
  listByEntity: async (entityType: CustomFieldEntityType, business?: Id) => {
    const { data } = await apiClient.get<{ results: CustomFieldDefinition[] } | CustomFieldDefinition[]>("/api/custom-fields/", {
      params: { entity_type: entityType, business },
    });
    return unwrapList(data);
  },
};

export const customFieldValuesApi = {
  context: async (business: Id, entity_type: CustomFieldEntityType, ids: Id[]) => {
    const params = new URLSearchParams({ business: String(business), entity_type });
    ids.forEach(id => params.append("ids", String(id)));
    return (await apiClient.get<{ definitions: CustomFieldDefinition[]; values: CustomFieldValue[]; editable_entities: Record<string, boolean>; editable_fields: Id[] }>("/api/custom-field-values/context/", { params })).data;
  },
  ...createCrudApi<CustomFieldValue>("/api/custom-field-values/"),
  bulkUpsert: async (payload: {
    business: Id;
    entity_type: CustomFieldEntityType;
    entity_id: string;
    values: Array<{ definition: Id; value_json: Record<string, unknown> }>;
  }) => {
    const { data } = await apiClient.post<CustomFieldValue[]>("/api/custom-field-values/bulk-upsert/", payload);
    return unwrapList(data);
  },
};
