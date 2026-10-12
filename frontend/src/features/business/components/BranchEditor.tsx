import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { useSearchParams } from "react-router";
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
  const { t } = useI18n();
  const client = useQueryClient();
  const confirm = useActionConfirm();
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
    {mutation.error && <ErrorState error={mutation.error} />}
    {tab === "details" ? <>
      <BranchDetailsForm branch={branch} pending={mutation.isPending} onSave={(payload) => save(() => branchesApi.update({ id: branch.id, payload }))} />
      {branch.can_manage && <div className="flex flex-wrap gap-2"><Button variant="secondary" disabled={mutation.isPending} onClick={() => mutation.mutate(() => branchesApi.state(branch.id, branch.is_active ? "paused" : "active"))}>{t(branch.is_active ? "branches.pause" : "branches.activate")}</Button>
        {!branch.archived_at && <Button variant="secondary" disabled={mutation.isPending} onClick={async () => { const result = await confirm({ title: t("branches.archive"), description: t("branches.archiveConfirm"), tone: "warning" }); if (result.confirmed) mutation.mutate(() => branchesApi.state(branch.id, "archived")); }}>{t("branches.archive")}</Button>}
      </div>}
    </> : query.isLoading || services.isLoading || resources.isLoading ? <LoadingState /> : query.error || services.error || resources.error ? <ErrorState error={query.error || services.error || resources.error} /> : query.data && <>
      {(tab === "services" || tab === "specialists") && <BranchCatalogEditor key={tab} tab={tab} branch={branch} config={query.data} services={services.data || []} resources={resources.data || []} save={save} disabled={disabled} />}
      {(tab === "schedule" || tab === "travel") && <BranchScheduleEditor key={tab} tab={tab} branch={branch} branches={branches} config={query.data} save={save} disabled={disabled} />}
    </>}
  </section>;
}
