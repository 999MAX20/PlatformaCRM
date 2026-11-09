import { useCustomFieldContext } from "../../../components/crm/CustomEntityFields";
import { useI18n } from "../../../lib/i18n";
import type { Appointment } from "../../../types";

export function useCalendarCustomLabels(appointments: Appointment[], enabled: boolean) {
  const { t } = useI18n();
  const query = useCustomFieldContext(appointments[0]?.business || 0, "appointment", appointments.map(item => item.id), enabled);
  const definitions = (!query.isError ? query.data?.definitions || [] : []).filter(field =>
    (field.options_json.display as { in_calendar?: boolean } | undefined)?.in_calendar).slice(0, 2);
  const values = new Map((query.data?.values || []).map(value => [`${value.entity_id}:${value.definition}`, value.value_json.value]));
  return { query, labels: (appointment: Appointment) => definitions.flatMap(field => {
    const value = values.get(`${appointment.id}:${field.id}`);
    if (value === undefined || value === null || value === "") return [];
    return [{ label: field.label, value: typeof value === "boolean" ? t(value ? "crmCard.yes" : "crmCard.no") : Array.isArray(value) ? value.join(", ") : String(value) }];
  }) };
}
