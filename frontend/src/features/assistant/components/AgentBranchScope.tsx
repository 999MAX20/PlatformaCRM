import { useQuery } from "@tanstack/react-query";
import type { Dispatch, SetStateAction } from "react";
import { branchesApi } from "../../../api/branches";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { useI18n } from "../../../lib/i18n";
import type { BotDraftState } from "../aiAgentsTypes";

export function AgentBranchScope({ draft, setDraft, disabled }: { draft: BotDraftState; setDraft: Dispatch<SetStateAction<BotDraftState>>; disabled: boolean }) {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const query = useQuery({ queryKey: ["branches", business?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  if (query.isLoading) return <LoadingState />;
  if (query.error) return <ErrorState error={query.error} />;
  if (!query.data?.length) return null;
  const all = draft.settings_json.branch_ids == null;
  const ids = Array.isArray(draft.settings_json.branch_ids) ? draft.settings_json.branch_ids as number[] : [];
  const update = (branch_ids: number[] | null) => setDraft((current) => ({ ...current, settings_json: { ...current.settings_json, branch_ids } }));
  return <fieldset disabled={disabled} className="space-y-2 py-5"><legend className="text-base font-semibold">{t("branches.agentScope")}</legend>
    <label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={all} onChange={(event) => update(event.target.checked ? null : query.data.filter((branch) => branch.can_book).map((branch) => branch.id))} />{t("branches.allFuture")}</label>
    {!all && query.data.map((branch) => <label key={branch.id} className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={ids.includes(branch.id)} onChange={(event) => update(event.target.checked ? [...ids, branch.id] : ids.filter((id) => id !== branch.id))} />{branch.name} · {branch.address}</label>)}
  </fieldset>;
}
