import { useState } from "react";
import { branchesApi, type Branch, type BranchConfiguration } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { useI18n } from "../../../lib/i18n";
import type { Resource, Service } from "../../../types";

export function BranchCatalogEditor({ tab, branch, config, services, resources, save, disabled }: {
  tab: string; branch: Branch; config: BranchConfiguration; services: Service[]; resources: Resource[];
  save: (operation: () => Promise<unknown>) => Promise<unknown>; disabled: boolean;
}) {
  const { t } = useI18n();
  const [service, setService] = useState("");
  const [resource, setResource] = useState("");
  const [duration, setDuration] = useState("30");
  const [price, setPrice] = useState("");
  const [active, setActive] = useState(true);
  const [serviceIds, setServiceIds] = useState<number[]>([]);
  const offers = config.offers.filter((item) => item.is_active);
  const chooseService = (id: string) => {
    setService(id);
    const offer = config.offers.find((item) => item.service === Number(id));
    const original = services.find((item) => item.id === Number(id));
    setDuration(String(offer?.duration_minutes ?? original?.duration_minutes ?? 30));
    setPrice(String(offer ? offer.price_from ?? "" : original?.price_from ?? ""));
    setActive(offer?.is_active ?? true);
  };
  const chooseResource = (id: string) => {
    setResource(id);
    const assignment = config.assignments.find((item) => item.resource === Number(id));
    setServiceIds(assignment?.service_ids || []); setActive(assignment?.is_active ?? true);
  };
  return <div className="grid gap-4 lg:grid-cols-2">
    <div className="space-y-2">{(tab === "services" ? config.offers.map((item) => ({ id: item.service, label: `${item.service_name} · ${item.duration_minutes} ${t("appointment.minutes")} · ${item.price_from ?? "—"}`, active: item.is_active })) : config.assignments.map((item) => ({ id: item.resource, label: item.resource_name, active: item.is_active }))).map((item) => <Button key={item.id} variant="secondary" className="w-full justify-start" onClick={() => tab === "services" ? chooseService(String(item.id)) : chooseResource(String(item.id))}>{item.label}{!item.active ? ` · ${t("branches.paused")}` : ""}</Button>)}</div>
    <form className="space-y-4 rounded-card border border-platforma-border bg-surface-card p-4" onSubmit={(event) => {
      event.preventDefault();
      void save(() => tab === "services" ? branchesApi.offer(branch.id, { service: Number(service), duration_minutes: Number(duration), price_from: price || null, is_active: active }) : branchesApi.assignment(branch.id, { resource: Number(resource), service_ids: serviceIds, is_active: active })).catch(() => undefined);
    }}><fieldset disabled={disabled} className="space-y-4">
      {tab === "services" ? <>
        <Select label={t("appointment.service")} value={service} onChange={(event) => chooseService(event.target.value)} options={[{ value: "", label: t("appointment.selectService") }, ...services.filter((item) => item.is_active && !item.is_archived).map((item) => ({ value: item.id, label: item.name }))]} />
        <Input label={t("branches.duration")} type="number" min={1} max={1440} required value={duration} onChange={(event) => setDuration(event.target.value)} />
        <Input label={t("branches.price")} type="number" min={0} step="0.01" value={price} onChange={(event) => setPrice(event.target.value)} />
      </> : <>
        <Select label={t("appointment.resource")} value={resource} onChange={(event) => chooseResource(event.target.value)} options={[{ value: "", label: t("appointment.selectSpecialist") }, ...resources.filter((item) => !item.retired_at).map((item) => ({ value: item.id, label: item.name }))]} />
        <fieldset className="space-y-2"><legend className="mb-2 text-sm font-semibold">{t("branches.services")}</legend>{offers.map((offer) => <label key={offer.id} className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={serviceIds.includes(offer.service)} onChange={(event) => setServiceIds(event.target.checked ? [...serviceIds, offer.service] : serviceIds.filter((id) => id !== offer.service))} />{offer.service_name}</label>)}</fieldset>
      </>}
      <label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={active} onChange={(event) => setActive(event.target.checked)} />{t("branches.active")}</label>
      <Button type="submit" disabled={disabled || !(tab === "services" ? service : resource)}>{t("common.save")}</Button>
    </fieldset></form>
  </div>;
}
