import { useState } from "react";
import type { Branch } from "../../api/branches";
import { managementApi, type ManagementCatalog } from "../../api/management";
import { Input } from "../../components/ui/Input";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";
import { EntityChoices, FormShell } from "./FormShell";

export function BranchEditor({ data, business, item, onClose }: { data: ManagementCatalog; business: Id; item?: Branch; onClose: () => void }) {
  const { t } = useI18n();
  const [active, setActive] = useState(item?.is_active ?? true);
  const [name, setName] = useState(item?.name || "");
  const [city, setCity] = useState(item?.city || "");
  const [address, setAddress] = useState(item?.address || "");
  const [phone, setPhone] = useState(item?.phone || "");
  const [services, setServices] = useState<Id[]>(data.offers.filter(row => row.branch === item?.id && row.is_active).map(row => row.service));
  const [specialists, setSpecialists] = useState<Id[]>(data.assignments.filter(row => row.branch === item?.id && row.is_active).map(row => row.resource));
  return <FormShell title={t(item ? "management.editBranch" : "management.addBranch")} onClose={onClose} save={() => managementApi.branch({ business, id: item?.id, is_active: active, name, city, address, phone, service_ids: services, specialist_ids: specialists })}>
    <Input label={t("management.name")} required maxLength={255} value={name} onChange={event => setName(event.target.value)} />
    <Input label={t("management.city")} maxLength={120} value={city} onChange={event => setCity(event.target.value)} />
    <Input label={t("management.address")} maxLength={10000} value={address} onChange={event => setAddress(event.target.value)} />
    <Input label={t("management.phone")} type="tel" maxLength={32} value={phone} onChange={event => setPhone(event.target.value)} />
    <EntityChoices label={t("nav.services")} options={data.services.filter(row => !row.is_archived)} selected={services} onChange={setServices} empty={t("management.noServices")} />
    <EntityChoices label={t("management.specialists")} options={data.resources.filter(row => row.resource_type === "staff" && !row.archived_at && !row.retired_at)} selected={specialists} onChange={setSpecialists} empty={t("management.noSpecialists")} />
    <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={active} onChange={event => setActive(event.target.checked)} />{t("management.active")}</label>
  </FormShell>;
}
