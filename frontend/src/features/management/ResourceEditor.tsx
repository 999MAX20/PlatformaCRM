import { useState } from "react";
import { managementApi, type ManagementCatalog, type ManagementResource, type SpecialistFormInput } from "../../api/management";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";
import { EntityChoices, FormShell } from "./FormShell";

export function ResourceEditor({ kind, data, business, item, selectedBranch, onClose }: { kind: "staff" | "rooms"; data: ManagementCatalog; business: Id; item?: ManagementResource; selectedBranch?: Id; onClose: () => void }) {
  const { t } = useI18n();
  const staff = kind === "staff";
  const [active, setActive] = useState(item?.is_active ?? true);
  const [name, setName] = useState(item?.name || "");
  const [profession, setProfession] = useState(item?.profession || "");
  const [description, setDescription] = useState(item?.public_description || "");
  const branches = data.branches.filter(branch => !branch.archived_at && branch.can_manage);
  const initialBranch = item?.branch || selectedBranch || (branches.length === 1 ? branches[0].id : undefined);
  const [branch, setBranch] = useState(String(initialBranch || ""));
  const [inherit, setInherit] = useState(item?.inherit_schedule ?? true);
  const [selectionDirty, setSelectionDirty] = useState(false);
  const [serviceIds, setServiceIds] = useState<Id[]>(item ? data.room_options.filter(link => link.resource_id === item.id).map(link => link.service_id) : []);
  const [locations, setLocations] = useState<SpecialistFormInput["locations"]>(() => item ? data.assignments.filter(row => row.resource === item.id && row.is_active).map(row => ({ branch: row.branch, service_ids: row.service_ids })) : initialBranch ? [{ branch: initialBranch, service_ids: [] }] : []);
  const offeredServices = (branchId: Id) => data.services.filter(service => !service.is_archived && data.offers.some(offer => offer.branch === branchId && offer.service === service.id && offer.is_active));
  return <FormShell dirty={selectionDirty} title={t(staff ? item ? "management.editSpecialist" : "management.addSpecialist" : item ? "management.editRoom" : "management.addRoom")} onClose={onClose} save={() => staff
    ? managementApi.specialist({ business, id: item?.id, is_active: active, name, profession, public_description: description, locations })
    : managementApi.room({ business, id: item?.id, is_active: active, name, public_description: description, branch: Number(branch), service_ids: serviceIds, inherit_schedule: inherit })}>
    <Input label={t(staff ? "management.fullName" : "management.name")} required maxLength={255} value={name} onChange={event => setName(event.target.value)} />
    {staff && <Input label={t("management.profession")} maxLength={120} value={profession} onChange={event => setProfession(event.target.value)} />}
    <Textarea label={t(staff ? "management.publicDescription" : "management.description")} rows={3} maxLength={10000} value={description} onChange={event => setDescription(event.target.value)} />
    {staff ? <>
      <EntityChoices label={t("branches.title")} options={branches} selected={locations.map(row => row.branch)} empty={t("management.noBranches")} onChange={ids => setLocations(ids.map(id => locations.find(row => row.branch === id) || { branch: id, service_ids: [] }))} />
      {locations.map(location => <section key={location.branch} className="min-w-0 space-y-4 rounded-control border border-platforma-border p-4">
        <h3 className="text-sm font-semibold">{branches.find(item => item.id === location.branch)?.name}</h3>
        <EntityChoices label={t("nav.services")} options={offeredServices(location.branch)} selected={location.service_ids} empty={t("management.noServices")} onChange={ids => setLocations(current => current.map(row => row.branch === location.branch ? { ...row, service_ids: ids } : row))} />
      </section>)}
    </> : <>
      <Select label={t("branches.branch")} required value={branch} options={[{ value: "", label: t("management.chooseBranch") }, ...branches.map(item => ({ value: item.id, label: item.name }))]} onChange={event => { setSelectionDirty(true); setBranch(event.target.value); setServiceIds([]); }} />
      <EntityChoices label={t("nav.services")} options={offeredServices(Number(branch))} selected={serviceIds} onChange={setServiceIds} empty={t("management.noServices")} />
      <Select label={t("management.scheduleMode")} value={inherit ? "branch" : "individual"} options={[{ value: "branch", label: t("management.inheritHours") }, { value: "individual", label: t("management.individualHours") }]} onChange={event => { setSelectionDirty(true); setInherit(event.target.value === "branch"); }} />
    </>}
    <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />{t("management.active")}</label>
  </FormShell>;
}
