import { useState } from "react";
import { managementApi, type ManagementCatalog, type ManagementService, type ServiceFormInput } from "../../api/management";
import { Input } from "../../components/ui/Input";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";
import { EntityChoices, FormShell } from "./FormShell";

export function ServiceEditor({ data, business, item, selectedBranch, onClose }: { data: ManagementCatalog; business: Id; item?: ManagementService; selectedBranch?: Id; onClose: () => void }) {
  const { t } = useI18n();
  const [active, setActive] = useState(item?.is_active ?? true);
  const [name, setName] = useState(item?.name || "");
  const [description, setDescription] = useState(item?.description || "");
  const [duration, setDuration] = useState(String(item?.duration_minutes || 30));
  const [price, setPrice] = useState(item?.price_from ?? "");
  const [requiresRoom, setRequiresRoom] = useState(item?.requires_room || false);
  const branches = data.branches.filter(branch => !branch.archived_at && branch.can_manage);
  const [locations, setLocations] = useState<ServiceFormInput["locations"]>(() => item ? data.offers.filter(offer => offer.service === item.id && offer.is_active).map(offer => ({
    branch: offer.branch, specialist_ids: data.assignments.filter(link => link.branch === offer.branch && link.is_active && link.service_ids.includes(item.id)).map(link => link.resource),
    room_ids: data.room_options.filter(link => link.service_id === item.id && link.branch_id === offer.branch).map(link => link.resource_id),
  })) : (selectedBranch || branches.length === 1 ? [{ branch: selectedBranch || branches[0].id, specialist_ids: [], room_ids: [] }] : []));
  const update = (branch: Id, patch: Partial<ServiceFormInput["locations"][number]>) => setLocations(current => current.map(row => row.branch === branch ? { ...row, ...patch } : row));
  return <FormShell title={t(item ? "management.editService" : "management.addService")} onClose={onClose} save={() => managementApi.service({ business, id: item?.id, is_active: active, name, description, duration_minutes: Number(duration), price_from: price === "" ? null : price, requires_room: requiresRoom, locations })}>
    <Input label={t("management.name")} required maxLength={255} value={name} onChange={event => setName(event.target.value)} />
    <div className="grid min-w-0 gap-4 sm:grid-cols-2">
      <Input label={t("management.duration")} type="number" min={1} max={1440} required value={duration} onChange={event => setDuration(event.target.value)} />
      <Input label={t("management.price")} type="number" min={0} step="0.01" value={price} onChange={event => setPrice(event.target.value)} />
    </div>
    <p className="text-xs text-platforma-subtle">{t("management.priceHint")}</p>
    <Textarea label={t("management.description")} rows={3} maxLength={10000} value={description} onChange={event => setDescription(event.target.value)} />
    <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={requiresRoom} onChange={event => setRequiresRoom(event.target.checked)} />{t("management.requiresRoom")}</label>
    {!requiresRoom && item && data.room_options.some(link => link.service_id === item.id && !link.is_alternative) && <p className="text-sm text-platforma-subtle">{t("management.legacyRooms")}: {data.resources.filter(room => data.room_options.some(link => link.service_id === item.id && link.resource_id === room.id && !link.is_alternative)).map(room => room.name).join(", ")}</p>}
    <EntityChoices label={t("branches.title")} options={branches} selected={locations.map(row => row.branch)} empty={t("management.noBranches")} onChange={ids => setLocations(ids.map(id => locations.find(row => row.branch === id) || { branch: id, specialist_ids: [], room_ids: [] }))} />
    {locations.map(location => <section key={location.branch} className="min-w-0 space-y-4 rounded-control border border-platforma-border p-4">
      <h3 className="text-sm font-semibold">{branches.find(branch => branch.id === location.branch)?.name}</h3>
      <EntityChoices label={t("management.specialists")} options={data.resources.filter(resource => resource.resource_type === "staff" && !resource.retired_at && !resource.archived_at)} selected={location.specialist_ids} onChange={ids => update(location.branch, { specialist_ids: ids })} empty={t("management.noSpecialists")} />
      {requiresRoom && <EntityChoices label={t("management.suitableRooms")} options={data.resources.filter(resource => resource.resource_type !== "staff" && resource.branch === location.branch && resource.is_active && !resource.archived_at)} selected={location.room_ids} onChange={ids => update(location.branch, { room_ids: ids })} empty={t("management.noRooms")} />}
    </section>)}
    <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />{t("management.active")}</label>
  </FormShell>;
}
