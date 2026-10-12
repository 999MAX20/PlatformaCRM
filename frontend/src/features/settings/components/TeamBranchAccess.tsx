import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { branchesApi } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { TeamMember } from "../../../types";

export function TeamBranchAccess({ member }: { member: TeamMember }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const [all, setAll] = useState(member.branch_access?.all_branches || false);
  const [ids, setIds] = useState(member.branch_access?.branch_ids || []);
  const branches = useQuery({ queryKey: ["branches", member.business], queryFn: () => branchesApi.listAll({ business: member.business }) });
  const mutation = useMutation({ mutationFn: () => branchesApi.grant({ member: member.id, all_branches: all, branch_ids: ids }), onSuccess: async () => {
    await Promise.all([cache.invalidateQueries({ queryKey: ["team-members"] }), cache.invalidateQueries({ queryKey: ["branches"] }), cache.invalidateQueries({ queryKey: ["auth-me"] })]);
  } });
  if (branches.isLoading) return <LoadingState />;
  if (branches.error) return <ErrorState error={branches.error} />;
  if (!branches.data?.length) return null;
  return <form className="space-y-3 border-t border-platforma-border pt-4" onSubmit={(event) => { event.preventDefault(); mutation.mutate(); }}>
    <fieldset disabled={mutation.isPending} className="space-y-2"><legend className="mb-2 text-sm font-semibold">{t("branches.access")}</legend>
      <label className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={all} onChange={(event) => setAll(event.target.checked)} />{t("branches.allFuture")}</label>
      {!all && branches.data.map((branch) => <label key={branch.id} className="flex min-h-10 items-center gap-2 text-sm"><input type="checkbox" checked={ids.includes(branch.id)} onChange={(event) => setIds(event.target.checked ? [...ids, branch.id] : ids.filter((id) => id !== branch.id))} />{branch.name}</label>)}
      <Button type="submit" isLoading={mutation.isPending}>{t("common.save")}</Button>
    </fieldset>
    {mutation.error && <ErrorState error={mutation.error} />}
    {mutation.isSuccess && <p role="status" className="text-sm text-platforma-success">{t("common.saved")}</p>}
  </form>;
}
