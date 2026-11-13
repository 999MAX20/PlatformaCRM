import { useQuery } from "@tanstack/react-query";
import type { Dispatch, SetStateAction } from "react";
import { branchesApi } from "../../../api/branches";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { useI18n } from "../../../lib/i18n";
import type { BotDraftState } from "../aiAgentsTypes";

export function AgentBranchScope({ draft, setDraft, disabled }: { draft: BotDraftState; setDraft: Dispatch<SetStateAction<BotDraftState>>; disabled: boolean }) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const query = useQuery({ queryKey: ["branches", business?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} action={<Button type="button" variant="secondary" onClick={() => void query.refetch()}>{t("common.retry")}</Button>} />;
  if (!query.data?.length) return <p className="text-sm text-platforma-subtle">{t("branches.empty")}</p>;
  const all = draft.settings_json.branch_ids == null;
  const ids = Array.isArray(draft.settings_json.branch_ids) ? draft.settings_json.branch_ids as number[] : [];
  const update = (branch_ids: number[] | null) => setDraft((current) => ({ ...current, settings_json: { ...current.settings_json, branch_ids } }));
  return <fieldset disabled={disabled} className="min-w-0 w-full space-y-2">
    <Select label={t("branches.agentScope")} density="compact" className="min-h-11 sm:min-h-9 sm:py-1" disabled={disabled}
      value={all ? "all" : "selected"} onChange={event => {
        const nextAll = event.target.value === "all";
        if (nextAll !== all) update(nextAll ? null : query.data.filter(branch => branch.can_book).map(branch => branch.id));
      }}
      options={[{ value: "all", label: t("branches.allFuture") }, { value: "selected", label: t("aiAgents.selectedBranches") }]} />
    {!all && <div className="grid gap-1">{query.data.map(branch => <label key={branch.id} className="flex min-h-11 items-center gap-2 rounded-control px-2 text-sm hover:bg-surface-hover sm:min-h-9">
      <input type="checkbox" checked={ids.includes(branch.id)} onChange={event => update(event.target.checked ? [...ids, branch.id] : ids.filter(id => id !== branch.id))} />
      <span className="min-w-0 break-words">{branch.name}{branch.address ? <span className="text-platforma-subtle"> · {branch.address}</span> : null}</span>
    </label>)}</div>}
  </fieldset>;
}
