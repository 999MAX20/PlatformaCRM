import { useQuery } from "@tanstack/react-query";
import { customFieldValuesApi } from "../../api/customFields";
import type { CustomFieldEntityType, Id } from "../../types";
import { ErrorState, LoadingState } from "../ui/StateViews";
import { CustomFieldsEditor } from "./drawers/EntityCustomFieldsPanel";
import { Button } from "../ui/Button";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../../features/auth/AuthProvider";
import { hasPermission } from "../../lib/permissions";

export function useCustomFieldContext(business: Id, kind: CustomFieldEntityType, ids: Id[], enabled = true) {
  const { user } = useAuth();
  return useQuery({ queryKey: ["custom-field-context", business, kind, user?.id, ids.map(String).join(",")],
    queryFn: async () => {
      const batches = ids.length ? Array.from({ length: Math.ceil(ids.length / 100) }, (_, index) => ids.slice(index * 100, (index + 1) * 100)) : [[]];
      const pages = await Promise.all(batches.map(batch => customFieldValuesApi.context(business, kind, batch)));
      return { ...pages[0], values: pages.flatMap(page => page.values), editable_entities: Object.assign({}, ...pages.map(page => page.editable_entities)) };
    }, enabled: enabled && !!business && hasPermission(user, business, "settings", "view") });
}

export function CustomEntityFields({ business, kind, id, readOnly, onDirtyChange }: {
  business: Id; kind: CustomFieldEntityType; id: Id; readOnly?: boolean; onDirtyChange?: (dirty: boolean) => void;
}) {
  const query = useCustomFieldContext(business, kind, [id]); const { t } = useI18n();
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("importWorkspace.reload")}</Button>} />;
  const fields = (query.data?.definitions || []).filter(field => (field.options_json.display as { in_card?: boolean } | undefined)?.in_card !== false).map(definition => ({
    definition, value: query.data?.values.find(value => value.definition === definition.id && value.entity_id === String(id)) || null,
    can_edit: !!query.data?.editable_entities[String(id)] && !!query.data.editable_fields.includes(definition.id),
  }));
  return <CustomFieldsEditor fields={fields} businessId={business} entity={{ type: kind, id }} readOnly={readOnly} onDirtyChange={onDirtyChange} />;
}
