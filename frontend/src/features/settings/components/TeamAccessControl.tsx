import { useMutation, useQueryClient } from "@tanstack/react-query";

import { teamApi } from "../../../api/team";
import { getApiErrorMessage } from "../../../api/client";
import { useActionConfirm } from "../../../components/actions/ActionConfirmProvider";
import { Button } from "../../../components/ui/Button";
import { ErrorState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { TeamMember } from "../../../types";

export function TeamAccessControl({ member, canManage }: { member: TeamMember; canManage: boolean }) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const cache = useQueryClient();
  const mutation = useMutation({
    mutationFn: teamApi.updateMember,
    onSuccess: async () => {
      await Promise.all([
        cache.invalidateQueries({ queryKey: ["team-members"] }),
        cache.invalidateQueries({ queryKey: ["auth-me"] }),
      ]);
    },
  });
  if (!canManage || member.role === "owner") return null;
  const label = t(member.is_active ? "teamAccess.disable" : "teamAccess.enable");
  async function changeAccess() {
    const result = await confirm({
      title: label,
      description: t(member.is_active ? "teamAccess.disableText" : "teamAccess.enableText", {
        name: member.user.full_name || member.user.email,
      }),
      confirmLabel: label,
      tone: member.is_active ? "warning" : "brand",
    });
    if (result.confirmed) mutation.mutate({ id: member.id, payload: { is_active: !member.is_active } });
  }
  return <div className="mt-4 space-y-3">
    <Button type="button" data-testid="team-access-toggle" variant={member.is_active ? "warning" : "secondary"}
      isLoading={mutation.isPending} onClick={() => void changeAccess()}>{label}</Button>
    {mutation.error && <ErrorState message={getApiErrorMessage(mutation.error)} />}
    {mutation.isSuccess && <p role="status" className="text-sm text-platforma-success">{t("common.saved")}</p>}
  </div>;
}
