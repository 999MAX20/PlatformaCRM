import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { businessesApi } from "../../../api/businesses";
import { getApiFieldErrors } from "../../../api/client";
import { businessConnectorsApi } from "../../../api/connectors";
import { Button } from "../../../components/ui/Button";
import { Card } from "../../../components/ui/Card";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";
import type { Business } from "../../../types";
import { SettingsFeedback } from "../../settings/components/SettingsLayout";
import { SettingsQueryState } from "../../settings/components/SettingsQueryState";

export function FinancialSourceSettings({ business }: { business: Business }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const [mode, setMode] = useState(business.financial_source_mode);
  const [connectorId, setConnectorId] = useState(business.financial_connector ? String(business.financial_connector) : "");
  const connectors = useQuery({
    queryKey: ["financial-source-options", business.id],
    queryFn: () => businessConnectorsApi.listAll({ business: business.id }),
  });
  const save = useMutation({
    mutationFn: () => businessesApi.update({ id: business.id, payload: { financial_source_mode: mode, financial_connector: mode === "external" && connectorId ? Number(connectorId) : null } }),
    onSuccess: () => { void cache.invalidateQueries({ queryKey: ["businesses"] }); },
  });
  const currentConnector = mode === "external" ? connectorId : "";
  const dirty = mode !== business.financial_source_mode || currentConnector !== (business.financial_connector ? String(business.financial_connector) : "");
  const options = [{ value: "", label: t("aiHistory.notSelected") }, ...(connectors.data || []).filter(item => item.capability === "finance").map(item => ({ value: String(item.id), label: item.name }))];
  if (connectorId && !options.some(option => option.value === connectorId)) options.push({ value: connectorId, label: t("settings.workflow.savedConnector", { id: connectorId }) });
  const errors = getApiFieldErrors(save.error);
  return <Card id="financial-source" padding="md">
    <form onSubmit={event => { event.preventDefault(); save.mutate(); }} className="space-y-4">
      <h2 className="text-base font-bold">{t("aiHistory.sourceSetting")}</h2>
      <fieldset disabled={save.isPending} className="grid gap-4 sm:grid-cols-2">
        <Select label={t("aiHistory.sourceSetting")} value={mode} error={errors.financial_source_mode?.join(" ")}
          options={[{ value: "manual", label: t("aiHistory.manual") }, { value: "external", label: t("aiHistory.external") }]}
          onChange={event => { setMode(event.target.value as Business["financial_source_mode"]); save.reset(); }} />
        {mode === "external" && <Select label={t("aiHistory.integration")} value={connectorId} options={options} error={errors.financial_connector?.join(" ")} disabled={connectors.isLoading || connectors.isError}
          onChange={event => { setConnectorId(event.target.value); save.reset(); }} />}
      </fieldset>
      {mode === "external" && <SettingsQueryState queries={[connectors]} />}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <SettingsFeedback error={!errors.financial_source_mode && !errors.financial_connector ? save.error : undefined} saved={save.isSuccess && !dirty} />
        <div className="flex gap-2">
          <Button type="button" variant="secondary" disabled={!dirty || save.isPending} onClick={() => { setMode(business.financial_source_mode); setConnectorId(business.financial_connector ? String(business.financial_connector) : ""); save.reset(); }}>{t("common.cancel")}</Button>
          <Button type="submit" disabled={!dirty || mode === "external" && (connectors.isLoading || connectors.isError)} isLoading={save.isPending}>{t("common.save")}</Button>
        </div>
      </div>
    </form>
  </Card>;
}
