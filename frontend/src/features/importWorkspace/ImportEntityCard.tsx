import type { ImportReportRow, ImportWorkspace } from "../../api/importWorkspace";
import { ClientForm } from "../../components/forms/ClientForm";
import { ServiceForm } from "../../components/forms/ServiceForm";
import { ResourceForm } from "../../components/forms/ResourceForm";
import { CustomFieldsEditor } from "../../components/crm/drawers/EntityCustomFieldsPanel";
import type { Client, Service, Resource, CustomFieldEntityType, CrmCardCustomField } from "../../types";
import { useI18n } from "../../lib/i18n";
import { displayImportValue } from "./importViewModel";

const noWrite = async () => undefined;
export function ImportEntityCard({ row, workspace }: { row: ImportReportRow; workspace: ImportWorkspace }) {
  const { t } = useI18n();
  const source = workspace.sources.find(item => item.id === row.source_id);
  const entityType = ({ clients: "client", services: "service", specialists: "specialist", appointments: "appointment" } as Record<string, CustomFieldEntityType>)[row.entity_type];
  const fields: CrmCardCustomField[] = (source?.fields || []).filter(field => field.in_card).map((field, index) => ({
    definition: { id: -(index + 1), business: workspace.business, entity_type: entityType, key: field.key, label: field.label, field_type: field.field_type, options_json: { options: field.options }, permissions_json: {}, is_active: true, is_required: false, sort_order: index, created_at: "", updated_at: "" },
    value: { id: -(index + 1), definition: -(index + 1), business: workspace.business, entity_type: entityType, entity_id: "preview", value_json: row.custom[field.key] || {}, created_at: "", updated_at: "" }, can_edit: false,
  }));
  return <div className="space-y-4">
    {row.entity_type === "clients" && <ClientForm businessId={workspace.business} initial={row.values as Partial<Client>} disabled showSubmit={false} onSubmit={noWrite} />}
    {row.entity_type === "services" && <ServiceForm businessId={workspace.business} initial={row.values as Partial<Service>} disabled showContextHint={false} showSubmit={false} onSubmit={noWrite} />}
    {row.entity_type === "specialists" && <ResourceForm businessId={workspace.business} initial={{ ...row.values, resource_type: "staff", is_active: true } as Partial<Resource>} disabled showContextHint={false} showSubmit={false} onSubmit={noWrite} />}
    {row.entity_type === "appointments" && <dl className="grid gap-3 sm:grid-cols-2">{["client_name", "service_name", "specialist_name", "start_at", "status", "notes"].map(key => <div key={key}><dt className="text-xs text-platforma-muted">{t(`importWorkspace.field.${({ client_name: "client_ref", service_name: "service_ref", specialist_name: "specialist_ref" } as Record<string, string>)[key] || key}`)}</dt><dd className="text-sm">{key === "status" ? t(`appointment.status.${row.values[key]}`) : displayImportValue(row.values[key])}</dd></div>)}</dl>}
    <CustomFieldsEditor fields={fields} businessId={workspace.business} entity={{ type: entityType, id: 0 }} readOnly />
  </div>;
}
