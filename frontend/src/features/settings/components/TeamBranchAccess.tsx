import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { branchesApi } from "../../../api/branches";
import { Button } from "../../../components/ui/Button";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import { useI18n } from "../../../lib/i18n";
import type { TeamMember } from "../../../types";

export function TeamBranchAccess({ member }: { member: TeamMember }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const [all, setAll] = useState(member.branch_access?.all_branches || false);
  const [ids, setIds] = useState(member.branch_access?.branch_ids || []);
  const branches = useQuery({ queryKey: ["branches", member.business], queryFn: () => branchesApi.listAll({ business: member.business }) });
  const capabilities = useQuery({ queryKey: ["branch-grant-capabilities", member.business, member.id], queryFn: () => branchesApi.grantCapabilities(member.id) });
  const mutation = useMutation({ mutationFn: () => branchesApi.grant({ member: member.id, all_branches: all, branch_ids: ids }), onSuccess: async () => {
    await Promise.all([cache.invalidateQueries({ queryKey: ["team-members"] }), cache.invalidateQueries({ queryKey: ["branches"] }), cache.invalidateQueries({ queryKey: ["branch-grant-capabilities"] }), cache.invalidateQueries({ queryKey: ["auth-me"] })]);
  }, onError: () => { void capabilities.refetch(); } });
  if (branches.isLoading || capabilities.isPending) return <LoadingState />;
  if (branches.error || capabilities.error) return <ErrorState error={branches.error || capabilities.error} action={<Button type="button" variant="secondary" size="lg" onClick={() => { void branches.refetch(); void capabilities.refetch(); }}>{t("common.retry")}</Button>} />;
  if (!branches.data?.length) return null;
  const access = capabilities.data;
  const canSave = access?.can_edit && (!all || access.can_grant_all) && (all || ids.every(id => access.branch_ids.includes(id)));
  return <form data-testid="team-branch-access" className="space-y-3 border-t border-platforma-border pt-4" onSubmit={(event) => { event.preventDefault(); if (canSave && !mutation.isPending) mutation.mutate(); }}>
    {!access?.can_edit && <StatusNotice tone="warning" title={t(access?.reason === "owner_access" ? "branches.ownerAccessFixed" : "branches.grantOutsideScope")} />}
    {access?.can_edit && !access.can_grant_all && <p className="text-sm text-platforma-subtle">{t("branches.futureGrantRestricted")}</p>}
    <fieldset disabled={mutation.isPending || !access?.can_edit} className="space-y-2"><legend className="mb-2 text-sm font-semibold">{t("branches.access")}</legend>
      <label className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={all} disabled={!access?.can_grant_all && !all} onChange={(event) => setAll(event.target.checked)} />{t("branches.allFuture")}</label>
      {!all && branches.data.filter(branch => access?.branch_ids.includes(branch.id)).map((branch) => <label key={branch.id} className="flex min-h-11 items-center gap-2 text-sm"><input type="checkbox" checked={ids.includes(branch.id)} onChange={(event) => setIds(event.target.checked ? [...ids, branch.id] : ids.filter((id) => id !== branch.id))} />{branch.name}</label>)}
      <Button type="submit" size="lg" disabled={!canSave} isLoading={mutation.isPending}>{t("common.save")}</Button>
    </fieldset>
    {mutation.error && <ErrorState error={mutation.error} />}
    {mutation.isSuccess && <p role="status" className="text-sm text-platforma-success">{t("common.saved")}</p>}
  </form>;
}
