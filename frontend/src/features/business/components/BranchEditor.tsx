import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useSearchParams } from "react-router";
import { normalizeAppError } from "../../../api/appError";
import { branchesApi, type Branch } from "../../../api/branches";
import { servicesApi } from "../../../api/services";
import { resourcesApi } from "../../../api/resources";
import { Button } from "../../../components/ui/Button";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { BranchDetailsForm } from "../BranchesPage";
import { BranchCatalogEditor } from "./BranchCatalogEditor";
import { BranchScheduleEditor } from "./BranchScheduleEditor";

export function BranchEditor({ branch, branches }: { branch: Branch; branches: Branch[] }) {
  return branch.uses_business_defaults ? <InitialLocation branch={branch} branches={branches} /> : <ConfiguredBranchEditor branch={branch} branches={branches} />;
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
      <Button variant="secondary" disabled={pending} onClick={() => onState(branch.is_active ? "paused" : "active")}>{t(branch.is_active ? "branches.pause" : "branches.activate")}</Button>
      {!branch.archived_at && <Button variant="secondary" disabled={pending || !canArchive} aria-describedby={!canArchive ? "last-active-branch" : undefined} onClick={async () => {
        const result = await confirm({ title: t("branches.archive"), description: t("branches.archiveConfirm"), tone: "warning" });
        if (result.confirmed) onState("archived");
      }}>{t("branches.archive")}</Button>}
    </div>
    {!branch.archived_at && !canArchive && <p id="last-active-branch" className="text-sm text-platforma-subtle">{t("branches.lastActive")}</p>}
  </div>;
}

function InitialLocation({ branch, branches }: { branch: Branch; branches: Branch[] }) {
  const { t } = useI18n();
  const client = useQueryClient();
  const mutation = useMutation({ mutationFn: (state: "active" | "paused" | "archived") => branchesApi.state(branch.id, state),
    onSuccess: async () => { await Promise.all([client.invalidateQueries({ queryKey: ["branches"] }), client.invalidateQueries({ queryKey: ["branch-catalog"] }), client.invalidateQueries({ queryKey: ["available-slots"] })]); } });
  return <section className="space-y-4" data-testid="automatic-location">
    <div className="space-y-2 rounded-card border border-platforma-border bg-surface-card p-4">
      <h2 className="text-base font-semibold">{branch.name}</h2>
      {branch.address && <p className="text-sm">{branch.address}</p>}
      {branch.phone && <p className="text-sm">{branch.phone}</p>}
      <p className="text-sm text-platforma-subtle">{t("branches.businessDefaults")}</p>
      {branch.can_manage && <Link className="platforma-focus-ring inline-flex min-h-10 items-center text-sm underline" to="/app/settings#business-profile">{t("branches.editBusinessDetails")}</Link>}
    </div>
    {mutation.error && <ErrorState error={mutation.error} message={normalizeAppError(mutation.error).code === "last_active_branch" ? t("branches.lastActive") : undefined} />}
    <BranchLifecycleActions branch={branch} branches={branches} pending={mutation.isPending} onState={state => mutation.mutate(state)} />
  </section>;
}

function ConfiguredBranchEditor({ branch, branches }: { branch: Branch; branches: Branch[] }) {
  const { t } = useI18n();
  const client = useQueryClient();
  const [params] = useSearchParams();
  const [tab, setTab] = useState(["details", "services", "specialists", "schedule", "travel"].includes(params.get("section") || "") ? params.get("section")! : "details");
  const query = useQuery({ queryKey: ["branch-configuration", branch.id], queryFn: () => branchesApi.configuration(branch.id) });
  const services = useQuery({ queryKey: ["services", "branch-options", branch.business], queryFn: () => servicesApi.listAll({ business: branch.business }) });
  const resources = useQuery({ queryKey: ["resources", "branch-options", branch.business], queryFn: () => resourcesApi.listAll({ business: branch.business, resource_type: "staff" }) });
  const mutation = useMutation({ mutationFn: (operation: () => Promise<unknown>) => operation(), onSuccess: async () => {
    await Promise.all([client.invalidateQueries({ queryKey: ["branches"] }), client.invalidateQueries({ queryKey: ["branch-configuration", branch.id] }), client.invalidateQueries({ queryKey: ["branch-catalog"] }), client.invalidateQueries({ queryKey: ["available-slots"] })]);
  } });
  const save = (operation: () => Promise<unknown>) => mutation.mutateAsync(operation);
  const disabled = !branch.can_manage || !!branch.archived_at || mutation.isPending;
  return <section className="space-y-4">
    <div className="flex flex-wrap gap-2" role="group" aria-label={t("branches.settings")}>
      {["details", "services", "specialists", "schedule", "travel"].map((value) => <Button key={value} variant={tab === value ? "primary" : "secondary"} onClick={() => setTab(value)} aria-pressed={tab === value}>{t(`branches.${value}`)}</Button>)}
    </div>
    {mutation.error && <ErrorState error={mutation.error} message={normalizeAppError(mutation.error).code === "last_active_branch" ? t("branches.lastActive") : undefined} />}
    {tab === "details" ? <>
      <BranchDetailsForm branch={branch} pending={mutation.isPending} onSave={(payload) => save(() => branchesApi.update({ id: branch.id, payload }))} />
      <BranchLifecycleActions branch={branch} branches={branches} pending={mutation.isPending} onState={state => mutation.mutate(() => branchesApi.state(branch.id, state))} />
    </> : query.isLoading || services.isLoading || resources.isLoading ? <LoadingState /> : query.error || services.error || resources.error ? <ErrorState error={query.error || services.error || resources.error} /> : query.data && <>
      {(tab === "services" || tab === "specialists") && <BranchCatalogEditor key={tab} tab={tab} branch={branch} config={query.data} services={services.data || []} resources={resources.data || []} save={save} disabled={disabled} />}
      {(tab === "schedule" || tab === "travel") && <BranchScheduleEditor key={tab} tab={tab} branch={branch} branches={branches} config={query.data} save={save} disabled={disabled} />}
    </>}
  </section>;
}
