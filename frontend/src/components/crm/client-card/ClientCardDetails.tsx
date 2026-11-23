import { useI18n } from "../../../lib/i18n";
import { formatDateTime } from "../../../lib/format";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import type { CrmCardPayload } from "../../../types";
import { CustomFieldsEditor } from "../drawers/EntityCustomFieldsPanel";
import { getChannelLabel } from "../drawers/shared";
import type { CrmDrawerEntity } from "../drawers/types";

export function ClientCardDetails({ data, entity, canEdit, onDirtyChange, onPendingChange, hideCustomFields = false }: {
  data: CrmCardPayload; entity: CrmDrawerEntity; canEdit: boolean;
  onDirtyChange: (dirty: boolean) => void; onPendingChange: (pending: boolean) => void;
  hideCustomFields?: boolean;
}) {
  const { t, language } = useI18n();
  const { business } = useActiveBusiness();
  const client = data.client!;
  const context = client.source_context_json || {};
  const rows = [
    [t("clients.source"), getChannelLabel(client.source, t)],
    [t("clients.sourceDetail"), client.source_detail],
    [t("clients.sourceCampaign"), context.campaign],
    [t("clients.sourceDomain"), context.page_domain],
  ].filter((row): row is [string, string] => typeof row[1] === "string" && Boolean(row[1].trim()));
  return <div className="space-y-6">
    {client.next_step_title ? <section><h3 className="mb-3 font-semibold">{t("crmCard.snapshotNext")}</h3><p className="text-sm">{client.next_step_title}</p>{client.next_step_date ? <p className="mt-1 text-xs text-platforma-subtle">{formatDateTime(client.next_step_date, business?.timezone, true, language)}</p> : null}</section> : null}
    <section><h3 className="mb-3 font-semibold">{t("clients.sourceAttribution")}</h3><dl className="space-y-3">{rows.map(([label, value]) => <div key={label} className="flex flex-wrap justify-between gap-2 text-sm"><dt className="text-platforma-subtle">{label}</dt><dd className="break-words">{value}</dd></div>)}</dl></section>
    {data.consents?.length ? <section><h3 className="mb-3 font-semibold">{t("clients.consentStatus")}</h3><ul className="divide-y divide-platforma-border">{data.consents.map(consent => <li key={consent.channel} className="py-3 text-sm"><div className="flex flex-wrap justify-between gap-2"><span>{getChannelLabel(consent.channel, t)}</span><span>{t(consent.status === "opted_in" ? "clients.consentOptedIn" : consent.status === "opted_out" ? "clients.consentOptedOut" : "clients.consentUnknown")}</span></div>{consent.source ? <p className="mt-1 text-xs text-platforma-subtle">{consent.source}</p> : null}</li>)}</ul></section> : null}
    {!hideCustomFields && <CustomFieldsEditor fields={data.custom_fields.filter(field => (field.definition.options_json.display as { in_card?: boolean } | undefined)?.in_card !== false)} entity={entity} businessId={client.business} readOnly={!canEdit} onDirtyChange={onDirtyChange} onPendingChange={onPendingChange} />}
  </div>;
}
