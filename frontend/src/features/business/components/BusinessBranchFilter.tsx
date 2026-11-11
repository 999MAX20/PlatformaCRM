import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router";
import { branchesApi } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState } from "../../../components/ui/StateViews";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { useI18n } from "../../../lib/i18n";

export function BusinessBranchFilter() {
  const { business } = useActiveBusiness();
  const { t } = useI18n();
  const [params, setParams] = useSearchParams();
  const query = useQuery({ queryKey: ["branches", business?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  if (query.error) return <ErrorState error={query.error} action={<Button onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  return <div className="mb-3 w-full sm:max-w-xs">
    <Select label={t("branches.branch")} value={params.get("branch") || ""} disabled={query.isPending}
      options={[{ value: "", label: t("business.allBranches") }, ...(query.data || []).filter(branch => !branch.archived_at && (branch.can_work || branch.can_manage)).map(branch => ({ value: branch.id, label: branch.name }))]}
      onChange={event => setParams(previous => {
        const next = new URLSearchParams(previous);
        if (event.target.value) next.set("branch", event.target.value); else next.delete("branch");
        ["resource", "service", "page"].forEach(key => next.delete(key));
        return next;
      })} />
  </div>;
}
