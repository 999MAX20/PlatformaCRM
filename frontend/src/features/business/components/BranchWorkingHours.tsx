import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect } from "react";
import { useSearchParams } from "react-router";
import { branchesApi, type Branch } from "../../../api/branches";
import { usePageHeader } from "../../../components/layout/PageHeaderContext";
import { useNotification } from "../../../components/notifications/NotificationProvider";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import { BranchScheduleEditor } from "./BranchScheduleEditor";
import { BusinessWorkspaceNav } from "./BusinessWorkspaceNav";

export function BranchWorkingHours({ branches }: { branches: Branch[] }) {
  const { t } = useI18n();
  const { setPageHeader } = usePageHeader();
  const [params, setParams] = useSearchParams();
  const selected = branches.find(branch => String(branch.id) === params.get("branch")) || branches.find(branch => !branch.archived_at) || branches[0];
  useEffect(() => { setPageHeader({ title: t("nav.workingHours") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  return <div className="space-y-4">
    <BusinessWorkspaceNav />
    {branches.length > 1 ? <Select label={t("branches.branch")} value={selected.id}
      onChange={event => setParams(previous => { const next = new URLSearchParams(previous); next.set("branch", event.target.value); return next; })}
      options={branches.map(branch => ({ value: branch.id, label: branch.name }))} /> : <h2 className="text-lg font-semibold">{selected.name}</h2>}
    <LocationSchedule key={selected.id} branch={selected} branches={branches} />
  </div>;
}

function LocationSchedule({ branch, branches }: { branch: Branch; branches: Branch[] }) {
  const { t } = useI18n();
  const client = useQueryClient();
  const notify = useNotification();
  const query = useQuery({ queryKey: ["branch-configuration", branch.id], queryFn: () => branchesApi.configuration(branch.id) });
  const mutation = useMutation({ mutationFn: (operation: () => Promise<unknown>) => operation(), onSuccess: async () => {
    await Promise.all(["branch-configuration", "branch-catalog", "available-slots"].map(key => client.invalidateQueries({ queryKey: [key] })));
    notify({ message: t("workingHours.savedNotice"), tone: "success" });
  } });
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} />;
  if (!query.data) return null;
  return <div className="space-y-4">
    {mutation.error && <ErrorState error={mutation.error} />}
    <BranchScheduleEditor tab="schedule" branch={branch} branches={branches} config={query.data}
      save={operation => mutation.mutateAsync(operation)} disabled={!branch.can_manage || !!branch.archived_at || mutation.isPending} />
  </div>;
}
