import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ownershipApi, type OwnershipTransfer } from "../../api/ownership";
import { normalizeAppError } from "../../api/appError";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { TaskDraftGuard } from "../tasks/components/TaskDraftGuard";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { OwnershipTransferSummary } from "./OwnershipTransferSummary";

export function OwnershipConfirmations() {
  const { user } = useAuth();
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const queryClient = useQueryClient();
  const key = ["account-ownership", user?.id];
  const list = useQuery({ queryKey: key, queryFn: ownershipApi.mine, enabled: Boolean(user), retry: false, gcTime: 0 });
  const mutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: "confirm" | "decline" }) => ownershipApi.decide(id, decision),
    retry: false,
    onSuccess: item => {
      queryClient.setQueryData<OwnershipTransfer[]>(key, rows => rows?.map(row => row.id === item.id ? item : row));
    },
  });
  async function decide(item: OwnershipTransfer, decision: "confirm" | "decline") {
    const label = t(decision === "confirm" ? "ownership.confirm" : "ownership.decline");
    if (!(await confirm({ title: label, description: `${item.previous_owner.name} → ${item.new_owner.name}. ${t("ownership.previousAccess")}: ${item.previous_owner_business_role?.name || t("ownership.disableAccess")}. ${t("ownership.sessionEffect")}`, confirmLabel: label, tone: "warning" })).confirmed) return;
    mutation.mutate({ id: item.id, decision });
  }
  if (list.isSuccess && !list.data.length) return null;
  const conflict = mutation.error && normalizeAppError(mutation.error).category === "conflict";
  return <section id="ownership" data-testid="account-ownership" className="scroll-mt-36 space-y-3 lg:scroll-mt-24" aria-label={t("ownership.title")}>
    {mutation.isPending && <TaskDraftGuard dirty={false} pending />}
    <div className="flex flex-wrap items-center justify-between gap-2"><h2 className="font-semibold">{t("ownership.title")}</h2><Button variant="secondary" disabled={mutation.isPending} isLoading={list.isFetching} onClick={() => { mutation.reset(); void list.refetch(); }}>{t("common.refresh")}</Button></div>
    {list.isPending && <LoadingState />}
    {list.error && <ErrorState error={list.error} action={<Button onClick={() => list.refetch()}>{t("common.retry")}</Button>} />}
    {mutation.error && <ErrorState error={mutation.error} />}
    {conflict && <p role="alert" className="text-sm text-platforma-warning">{t("ownership.conflict")}</p>}
    {!list.isError && list.data?.map(item => <OwnershipTransferSummary item={item} key={item.id}>
      <div className="flex flex-wrap gap-2">
        {item.actions.confirm && <Button disabled={mutation.isPending || Boolean(conflict)} onClick={() => void decide(item, "confirm")}>{t("ownership.confirm")}</Button>}
        {item.actions.decline && <Button variant="secondary" disabled={mutation.isPending} onClick={() => void decide(item, "decline")}>{t("ownership.decline")}</Button>}
      </div>
    </OwnershipTransferSummary>)}
  </section>;
}
