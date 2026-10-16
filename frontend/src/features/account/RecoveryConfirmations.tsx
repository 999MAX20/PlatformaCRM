import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { recoveryApi, type RecoveryRequest } from "../../api/recovery";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { TaskDraftGuard } from "../tasks/components/TaskDraftGuard";
import { RecoverySummary } from "./RecoverySummary";

export function RecoveryConfirmations() {
  const { user } = useAuth();
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const cache = useQueryClient();
  const key = ["account-recovery", user?.id];
  const query = useQuery({ queryKey: key, queryFn: recoveryApi.mine, retry: false, gcTime: 0, enabled: Boolean(user) });
  const mutation = useMutation({ mutationFn: ({ id, decision }: { id: string; decision: "confirm" | "decline" }) => recoveryApi.decide(id, decision), retry: false,
    onSuccess: () => cache.invalidateQueries({ queryKey: key }) });
  async function decide(item: RecoveryRequest, decision: "confirm" | "decline") {
    const label = t(`ownership.${decision}`);
    if (!(await confirm({ title: label, description: `${item.user_name} → ${item.new_email}. ${t("recovery.ownerAttestation")} ${t("recovery.effects")}`, confirmLabel: label, tone: "warning" })).confirmed) return;
    mutation.mutate({ id: item.id, decision });
  }
  if (query.isSuccess && !query.data.length) return null;
  return <section className="space-y-3" data-testid="recovery-confirmations" aria-label={t("recovery.title")}>
    <h2 className="font-semibold">{t("recovery.title")}</h2>
    {mutation.isPending && <TaskDraftGuard dirty={false} pending />}
    {query.isPending && <LoadingState />}
    {query.error && <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} />}
    {mutation.error && <ErrorState error={mutation.error} />}
    {!query.isError && query.data?.map(item => <RecoverySummary key={item.id} item={item}>
      {item.status === "pending" && <div className="flex flex-wrap gap-2">
        <Button disabled={mutation.isPending} onClick={() => void decide(item, "confirm")}>{t("ownership.confirm")}</Button>
        <Button variant="secondary" disabled={mutation.isPending} onClick={() => void decide(item, "decline")}>{t("ownership.decline")}</Button>
      </div>}
    </RecoverySummary>)}
  </section>;
}
