import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, useNavigate, useSearchParams } from "react-router";
import { normalizeAppError } from "../../../api/appError";
import { branchesApi, type Branch, type BranchConfiguration } from "../../../api/branches";
import { servicesApi } from "../../../api/services";
import { resourcesApi } from "../../../api/resources";
import { Button } from "../../../components/ui/Button";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { BranchDetailsForm } from "../BranchesPage";
import { BranchCatalogEditor } from "./BranchCatalogEditor";
import { BranchScheduleEditor } from "./BranchScheduleEditor";
import { BranchStatusBadge } from "./BranchStatusBadge";
import { BranchOverview } from "./BranchOverview";
import { BranchPhysicalResources } from "./BranchPhysicalResources";

export function BranchEditor({ branch, branches }: { branch: Branch; branches: Branch[] }) {
  const { t } = useI18n();
  const client = useQueryClient();
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const automatic = !!branch.uses_business_defaults;
  const sections = ["overview", "services", "specialists", "resources", "schedule", ...(branches.length > 1 ? ["travel"] : []), "details"];
  const tab = sections.includes(params.get("section") || "") ? params.get("section")! : "overview";
  const selectTab = (value: string) => setParams(previous => { const next = new URLSearchParams(previous); next.set("section", value); return next; });
  const query = useQuery({ queryKey: [branch.can_manage ? "branch-configuration" : "branch-catalog", branch.id],
    queryFn: async (): Promise<BranchConfiguration> => {
      if (branch.can_manage) return branchesApi.configuration(branch.id);
      const catalog = await branchesApi.catalog(branch.id);
      return { ...catalog, days: catalog.days || [], travel: [], physical_resources: catalog.physical_resources || [], resource_requirements: catalog.resource_requirements || [] };
    } });
  const editingCatalog = !automatic && (tab === "services" || tab === "specialists");
  const services = useQuery({ queryKey: ["services", "branch-options", branch.business], queryFn: () => servicesApi.listAll({ business: branch.business }), enabled: editingCatalog });
  const resources = useQuery({ queryKey: ["resources", "branch-options", branch.business], queryFn: () => resourcesApi.listAll({ business: branch.business, resource_type: "staff" }), enabled: editingCatalog });
  const mutation = useMutation({ mutationFn: (operation: () => Promise<unknown>) => operation(), onSuccess: async () => {
    await Promise.all(["branches", "branch-configuration", "branch-catalog", "available-slots"].map(key => client.invalidateQueries({ queryKey: [key] })));
  } });
  const save = (operation: () => Promise<unknown>) => mutation.mutateAsync(operation);
  const disabled = !branch.can_manage || !!branch.archived_at || mutation.isPending;
  const open = (section: string) => {
    if (branch.archived_at) { selectTab(section); return; }
    const path = section === "services" ? "services" : section === "schedule" ? "working-hours" : section === "specialists" ? "staff" : "resources";
    navigate(`/app/business/${path}?branch=${branch.id}`);
  };
  return <section className="space-y-5" data-testid={automatic ? "automatic-location" : "configured-location"}>
    <header className="flex flex-wrap items-start justify-between gap-3">
      <div className="min-w-0 space-y-2">
        <div className="flex flex-wrap items-center gap-3"><h3 className="break-words text-lg font-semibold">{branch.name}</h3><BranchStatusBadge branch={branch} /></div>
        {(branch.address || branch.phone) && <p className="break-words text-sm text-platforma-subtle">{[branch.address, branch.phone].filter(Boolean).join(" · ")}</p>}
      </div>
      <div className="flex flex-wrap gap-2">
        {branch.can_manage && !branch.archived_at && (automatic ? <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm font-semibold text-brand-700 underline" to={`/app/business/company?branch=${branch.id}`}>{t("branches.editContacts")}</Link>
          : <Button variant="secondary" onClick={() => selectTab("details")}>{t("branches.editContacts")}</Button>)}
        {!automatic && branches.length > 1 && <Button variant="secondary" onClick={() => selectTab("travel")}>{t("branches.travel")}</Button>}
      </div>
    </header>
    {!automatic && tab !== "overview" && <div className="flex flex-wrap items-center gap-3"><Button variant="secondary" onClick={() => selectTab("overview")}>{t("common.back")}</Button><h4 className="font-semibold">{t(tab === "resources" ? "branches.physicalResources" : `branches.${tab}`)}</h4></div>}
    {mutation.error && <ErrorState error={mutation.error} message={normalizeAppError(mutation.error).code === "last_active_branch" ? t("branches.lastActive") : undefined} />}
    <div id={`location-settings-panel-${tab}`}>
      {!automatic && tab === "details" ? <BranchDetailsForm branch={branch} pending={mutation.isPending} onSave={payload => save(() => branchesApi.update({ id: branch.id, payload }))} />
        : query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} /> : query.data && <>
          {(automatic || tab === "overview") && <BranchOverview config={query.data} onOpen={open} />}
          {!automatic && tab === "resources" && <BranchPhysicalResources branch={branch} branches={branches} config={query.data} disabled={disabled} />}
          {editingCatalog && (services.isLoading || resources.isLoading ? <LoadingState /> : services.error || resources.error ? <ErrorState error={services.error || resources.error} />
            : <BranchCatalogEditor key={tab} tab={tab} branch={branch} config={query.data} services={services.data || []} resources={resources.data || []} save={save} disabled={disabled} />)}
          {!automatic && (tab === "schedule" || tab === "travel") && <BranchScheduleEditor key={tab} tab={tab} branch={branch} branches={branches} config={query.data} save={save} disabled={disabled} />}
        </>}
    </div>
    {(automatic || tab === "overview" || tab === "details") && <BranchLifecycleActions branch={branch} branches={branches} pending={mutation.isPending} onState={state => mutation.mutate(() => branchesApi.state(branch.id, state))} />}
  </section>;
}

function BranchLifecycleActions({ branch, branches, pending, onState }: {
  branch: Branch; branches: Branch[]; pending: boolean; onState: (state: "active" | "paused" | "archived") => void;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const canArchive = branches.some(item => item.id !== branch.id && item.is_active && !item.archived_at);
  if (!branch.can_manage) return null;
  return <div className="space-y-2">
    <div className="flex flex-wrap gap-2">
      <Button variant="secondary" disabled={pending} onClick={() => onState(branch.archived_at || branch.is_active ? "paused" : "active")}>{t(branch.archived_at ? "business.restorePaused" : branch.is_active ? "branches.pause" : "branches.activate")}</Button>
      {!branch.archived_at && <Button variant="secondary" disabled={pending || !canArchive} aria-describedby={!canArchive ? "last-active-branch" : undefined} onClick={async () => {
        const result = await confirm({ title: t("branches.archive"), description: t("branches.archiveConfirm"), tone: "warning" });
        if (result.confirmed) onState("archived");
      }}>{t("branches.archive")}</Button>}
    </div>
    {!branch.archived_at && !canArchive && <p id="last-active-branch" className="text-sm text-platforma-subtle">{t("branches.lastActive")}</p>}
  </div>;
}
