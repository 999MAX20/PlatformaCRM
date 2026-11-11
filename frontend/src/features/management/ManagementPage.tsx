import { useQuery } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { Link, useSearchParams } from "react-router";
import { managementApi, type ManagementKind, type ManagementResource, type ManagementService } from "../../api/management";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";
import { BusinessSchedulePage } from "../business/BusinessSchedulePage";
import { ManagementLayout, managementSections, type ManagementSection } from "./ManagementLayout";
import { ServiceEditor } from "./ServiceEditor";
import { ResourceEditor } from "./ResourceEditor";
import { BranchEditor } from "./BranchEditor";
import { BranchDetail } from "./BranchDetail";
import { EntityActions } from "./EntityActions";
import { AbsenceDialog } from "./AbsenceDialog";

export function ManagementPage({ section = "services" }: { section?: ManagementSection }) {
  const { t } = useI18n();
  const { setPageHeader } = usePageHeader();
  useEffect(() => { setPageHeader({ title: t("nav.business") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  return <ManagementLayout section={section}>{section === "working-hours" ? <BusinessSchedulePage embedded /> : <ManagementCatalogPage key={section} section={section} />}</ManagementLayout>;
}

function ManagementCatalogPage({ section }: { section: Exclude<ManagementSection, "working-hours"> }) {
  const { t, language } = useI18n();
  const { business } = useActiveBusiness();
  const [params, setParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [state, setState] = useState("current");
  const [related, setRelated] = useState("");
  const [editor, setEditor] = useState<{ kind: ManagementKind; id?: Id } | null>(null);
  const [absence, setAbsence] = useState<ManagementResource | null>(null);
  const query = useQuery({ queryKey: ["management", business?.id], queryFn: () => managementApi.catalog(business!.id), enabled: !!business });
  const data = query.data;
  const requestedEntity = params.get(section === "services" ? "service" : "resource");
  useEffect(() => {
    if (!data || !requestedEntity || section === "branches") return;
    const item = (section === "services" ? data.services : data.resources).find(row => String(row.id) === requestedEntity);
    if (item?.can_manage) setEditor({ kind: section === "resources" ? "rooms" : section, id: item.id });
  }, [data, requestedEntity, section]);
  const closeEditor = () => { setEditor(null); setParams(previous => { const next = new URLSearchParams(previous); next.delete("service"); next.delete("resource"); return next; }, { replace: true }); };
  if (query.isPending) return <LoadingState />;
  if (query.error || !data || !business) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  const currentBranches = data.branches.filter(row => !row.archived_at);
  const branchId = data.branches.find(row => String(row.id) === params.get("branch"))?.id || (currentBranches.length === 1 ? currentBranches[0].id : undefined);
  const filterBranchId = data.branches.find(row => String(row.id) === params.get("branch"))?.id;
  const kind: ManagementKind = section === "resources" ? "rooms" : section;
  const open = (kind: ManagementKind, id?: Id) => setEditor({ kind, id });
  const staff = data.resources.filter(row => row.resource_type === "staff" && !row.retired_at);
  const matchesState = (row: { is_active: boolean; archived_at?: string | null; is_archived?: boolean }) => state === "archived" ? !!(row.archived_at || row.is_archived) : !(row.archived_at || row.is_archived) && (state === "current" || row.is_active === (state === "active"));
  const rows = section === "services" ? data.services.filter(row => matchesState(row) && row.name.toLocaleLowerCase().includes(search.toLocaleLowerCase())
    && (!filterBranchId || data.offers.some(offer => offer.branch === filterBranchId && offer.service === row.id && offer.is_active))
    && (!related || data.assignments.some(link => link.resource === Number(related) && link.service_ids.includes(row.id) && link.is_active && (!filterBranchId || link.branch === filterBranchId))))
    : data.resources.filter(row => !row.retired_at && (section === "staff" ? row.resource_type === "staff" : row.resource_type !== "staff") && matchesState(row)
      && `${row.name} ${row.profession}`.toLocaleLowerCase().includes(search.toLocaleLowerCase())
      && (!filterBranchId || (section === "staff" ? data.assignments.some(link => link.resource === row.id && link.branch === filterBranchId && link.is_active) : row.branch === filterBranchId))
      && (!related || (section === "staff" ? data.assignments.some(link => link.resource === row.id && link.service_ids.includes(Number(related)) && link.is_active && (!filterBranchId || link.branch === filterBranchId)) : data.room_options.some(link => link.resource_id === row.id && link.service_id === Number(related)))));
  const title = managementSections.find(item => item.id === section)!.key;
  const createKey = { services: "management.addService", staff: "management.addSpecialist", rooms: "management.addRoom", branches: "management.addBranch" }[kind];
  const canCreate = kind === "services" || kind === "branches" ? data.can_create_service : data.can_create_resource;
  const branchName = (id: Id) => data.branches.find(row => row.id === id)?.name || "";
  const names = (ids: Id[], pool: { id: Id; name: string }[]) => pool.filter(row => ids.includes(row.id)).map(row => row.name).join(", ") || t("management.notAssigned");
  const cell = (label: string, children: ReactNode, className = "") => <td data-label={t(label)} className={className}>{children}</td>;
  const actions = (row: ManagementService | ManagementResource) => <EntityActions business={business.id} kind={kind} id={row.id} name={row.name} active={row.is_active} archived={"is_archived" in row ? row.is_archived : !!row.archived_at}
    canManage={row.can_manage} canDelete={data.can_delete} edit={() => open(kind, row.id)} branch={branchId}
    absence={kind !== "services" && row.can_manage && !("is_archived" in row) && !row.archived_at ? () => setAbsence(row) : undefined} />;
  const status = (row: ManagementService | ManagementResource) => <span className="text-xs text-platforma-subtle">{t(("is_archived" in row ? row.is_archived : row.archived_at) ? "management.archived" : row.is_active ? "management.active" : "management.inactive")}</span>;
  const selectedBranch = data.branches.find(row => row.id === branchId) || currentBranches[0] || data.branches[0];
  return <div className="min-w-0 space-y-5">
    <header className="flex flex-wrap items-center justify-between gap-3"><h2 className="text-xl font-semibold">{t(title)} <span className="ml-2 text-sm font-normal text-platforma-subtle">{section === "branches" ? data.branches.length : rows.length}</span></h2>
      {canCreate && <Button onClick={() => open(kind)}><Plus size={17} aria-hidden="true" />{t(createKey)}</Button>}
    </header>
    {section !== "branches" ? <>
      <div className="grid min-w-0 gap-3 sm:grid-cols-2 xl:grid-cols-[minmax(180px,1fr)_repeat(3,minmax(110px,auto))_auto]">
        <Input label={t("management.search")} value={search} onChange={event => setSearch(event.target.value)} />
        {currentBranches.length > 1 && <Select label={t("branches.branch")} value={branchId || ""} options={[{ value: "", label: t("branches.all") }, ...currentBranches.map(row => ({ value: row.id, label: row.name }))]} onChange={event => setParams(previous => { const next = new URLSearchParams(previous); event.target.value ? next.set("branch", event.target.value) : next.delete("branch"); return next; })} />}
        <Select label={t(section === "services" ? "management.specialists" : "nav.services")} value={related} options={[{ value: "", label: t("management.all") }, ...(section === "services" ? staff : data.services.filter(row => !row.is_archived)).map(row => ({ value: row.id, label: row.name }))]} onChange={event => setRelated(event.target.value)} />
        <Select label={t("management.state")} value={state} options={["current", "active", "inactive", "archived"].map(value => ({ value, label: t(`management.${value}`) }))} onChange={event => setState(event.target.value)} />
        <Button variant="secondary" className="self-end" onClick={() => { setSearch(""); setRelated(""); setState("current"); setParams({}); }}>{t("management.reset")}</Button>
      </div>
      {rows.length ? <table className="management-table"><caption className="sr-only">{t(title)}</caption><thead><tr className="border-y border-platforma-border text-platforma-subtle">
        {(section === "services" ? ["management.name", "management.duration", "management.price", "management.specialists", ...(currentBranches.length > 1 ? ["branches.title"] : []), "management.state", "management.actions"] : ["management.name", ...(section === "staff" ? ["management.profession"] : ["branches.branch"]), "nav.services", "nav.workingHours", "management.state", "management.actions"]).map(key => <th scope="col" key={key}>{t(key)}</th>)}
      </tr></thead><tbody>{rows.map(row => <tr key={row.id} className="border-b border-platforma-border">
        {cell("management.name", <><button type="button" className="platforma-focus-ring min-h-10 break-words text-left font-semibold hover:underline" onClick={() => row.can_manage && open(kind, row.id)} disabled={!row.can_manage}>{row.name}</button>{"requires_room" in row && row.is_active && <ServiceReadiness service={row} branch={branchId} data={data} />}</>)}
        {"duration_minutes" in row ? <>
          {cell("management.duration", `${row.duration_minutes} ${t("management.minutes")}`, "management-number")}
          {cell("management.price", row.price_from === null ? t("management.notSpecified") : Number(row.price_from) === 0 ? t("management.free") : new Intl.NumberFormat(language === "kk" ? "kk-KZ" : language === "ru" ? "ru-KZ" : "en-GB", { maximumFractionDigits: 2 }).format(Number(row.price_from)), "management-number")}
          {cell("management.specialists", names(data.assignments.filter(link => link.is_active && link.service_ids.includes(row.id) && (!branchId || link.branch === branchId)).map(link => link.resource), staff))}
          {currentBranches.length > 1 && cell("branches.title", names(data.offers.filter(offer => offer.service === row.id && offer.is_active).map(offer => offer.branch), data.branches))}
        </> : <>
          {cell(section === "staff" ? "management.profession" : "branches.branch", section === "staff" ? row.profession || t("management.notSpecified") : row.branch ? branchName(row.branch) : t("management.notAssigned"))}
          {cell("nav.services", names(section === "staff" ? data.assignments.filter(link => link.resource === row.id && link.is_active && (!branchId || link.branch === branchId)).flatMap(link => link.service_ids) : data.room_options.filter(link => link.resource_id === row.id).map(link => link.service_id), data.services))}
          {cell("nav.workingHours", <Link className="platforma-focus-ring inline-flex min-h-11 items-center text-brand-700 underline" to={`/app/business/working-hours?view=${section === "staff" ? "staff" : "physical"}&resource=${row.id}${branchId || row.branch ? `&branch=${branchId || row.branch}` : ""}`}>{t(section === "staff" ? "management.editSchedule" : row.inherit_schedule ? "management.inheritHours" : "management.individualHours")}</Link>)}
        </>}
        {cell("management.state", status(row))}{cell("management.actions", actions(row))}
      </tr>)}</tbody></table> : <div className="space-y-3 border-t border-platforma-border py-12 text-center"><p className="text-sm text-platforma-subtle">{t("management.noResults")}</p>{canCreate && <Button variant="secondary" onClick={() => open(kind)}>{t(createKey)}</Button>}</div>}
    </> : <div className={data.branches.length > 1 ? "grid min-w-0 gap-6 xl:grid-cols-[170px_minmax(0,1fr)]" : "min-w-0"}>
      {data.branches.length > 1 && <nav className="flex gap-2 overflow-x-auto pb-2 xl:flex-col" aria-label={t("branches.title")}>{data.branches.map(row => <button type="button" key={row.id} aria-pressed={row.id === selectedBranch?.id} className={`platforma-focus-ring min-h-11 min-w-32 rounded-control p-3 text-left text-sm ${row.id === selectedBranch?.id ? "bg-brand-50 text-brand-700" : "hover:bg-surface-hover"}`} onClick={() => setParams({ branch: String(row.id) })}>{row.name}{row.archived_at && <span className="block text-xs">{t("management.archived")}</span>}</button>)}</nav>}
      {selectedBranch ? <BranchDetail branch={selectedBranch} data={data} business={business.id} edit={() => open("branches", selectedBranch.id)} openEntity={open} /> : <p>{t("management.noBranches")}</p>}
    </div>}
    {editor?.kind === "services" && <ServiceEditor data={data} business={business.id} item={data.services.find(row => row.id === editor.id)} selectedBranch={branchId} onClose={closeEditor} />}
    {editor && (editor.kind === "staff" || editor.kind === "rooms") && <ResourceEditor kind={editor.kind} data={data} business={business.id} item={data.resources.find(row => row.id === editor.id)} selectedBranch={branchId} onClose={closeEditor} />}
    {editor?.kind === "branches" && <BranchEditor data={data} business={business.id} item={data.branches.find(row => row.id === editor.id)} onClose={closeEditor} />}
    {absence && <AbsenceDialog item={absence} onClose={() => setAbsence(null)} />}
  </div>;
}

function ServiceReadiness({ service, branch, data }: { service: ManagementService; branch?: Id; data: import("../../api/management").ManagementCatalog }) {
  const { t } = useI18n();
  const offers = data.offers.filter(row => row.service === service.id && row.is_active && (!branch || row.branch === branch) && data.branches.some(item => item.id === row.branch && item.is_active && !item.archived_at));
  const reasons = offers.map(offer => {
    const links = data.assignments.filter(row => row.branch === offer.branch && row.is_active && row.service_ids.includes(service.id));
    const people = data.resources.filter(row => row.is_active && !row.retired_at && !row.archived_at && links.some(link => link.resource === row.id));
    if (!people.length) return "management.missingSpecialist";
    if (service.requires_room && !data.room_options.some(row => row.service_id === service.id && row.branch_id === offer.branch && data.resources.some(room => room.id === row.resource_id && room.is_active && !room.archived_at))) return "management.missingRoom";
    if (!data.scheduled_pairs.some(row => row.branch === offer.branch && row.resource === null) || !people.some(person => data.scheduled_pairs.some(row => row.branch === offer.branch && row.resource === person.id))) return "management.missingSchedule";
    return null;
  });
  const reason = !offers.length ? "management.missingBranch" : reasons.includes(null) ? null : reasons[0];
  return reason ? <p className="mt-1 max-w-xs text-xs text-platforma-subtle">{t(reason)}</p> : null;
}
