import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { employeeAccessApi, type AccessRepair } from "../../api/employeeAccess";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";
import { TaskDraftGuard } from "../tasks/components/TaskDraftGuard";
import { EmployeeAccessSummary } from "./EmployeeAccessSummary";

export function EmployeeAccessConfirmations() {
  const { user } = useAuth();
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const cache = useQueryClient();
  const key = ["employee-access-confirmations", user?.id];
  const query = useQuery({ queryKey: key, queryFn: employeeAccessApi.mine, retry: false, gcTime: 0, enabled: Boolean(user) });
  const mutation = useMutation({ mutationFn: ({ id, decision }: { id: string; decision: "confirm" | "decline" }) => employeeAccessApi.decide(id, decision), retry: false,
    onSuccess: () => cache.invalidateQueries({ queryKey: key }) });
  async function decide(item: AccessRepair, decision: "confirm" | "decline") {
    const label = t(`ownership.${decision}`);
    if (!(await confirm({ title: label, description: `${item.target_email} · ${t(`employeeAccess.action.${item.action}`)} · ${item.target_role?.name || t(`settings.role.${item.target_role_key}`)}. ${t("employeeAccess.effects")}`, confirmLabel: label, tone: "warning" })).confirmed) return;
    mutation.mutate({ id: item.id, decision });
  }
  if (query.isSuccess && !query.data.length) return null;
  return <section className="space-y-3" data-testid="employee-access-confirmations" aria-label={t("employeeAccess.title")}>
    <h2 className="font-semibold">{t("employeeAccess.title")}</h2>
    {mutation.isPending && <TaskDraftGuard dirty={false} pending />}
    {query.isPending && <LoadingState />}
    {query.error && <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} />}
    {mutation.error && <ErrorState error={mutation.error} action={<Button disabled={mutation.isPending} onClick={() => { mutation.reset(); void query.refetch(); }}>{t("common.refresh")}</Button>} />}
    {!query.isError && query.data?.map(item => <EmployeeAccessSummary key={item.id} item={item}>
      <div className="flex flex-wrap gap-2">
        <Button disabled={mutation.isPending} onClick={() => void decide(item, "confirm")}>{t("ownership.confirm")}</Button>
        <Button variant="secondary" disabled={mutation.isPending} onClick={() => void decide(item, "decline")}>{t("ownership.decline")}</Button>
      </div>
    </EmployeeAccessSummary>)}
  </section>;
}
