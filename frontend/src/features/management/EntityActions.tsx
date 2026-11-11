import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { Link } from "react-router";
import { managementApi, type LifecycleOperation, type ManagementKind } from "../../api/management";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import type { Id } from "../../types";
import { managementQueryKeys } from "./FormShell";

export function EntityActions({ business, kind, id, name, active, archived, canManage, canDelete, edit, absence, branch }: { business: Id; kind: ManagementKind; id: Id; name: string; active: boolean; archived: boolean; canManage: boolean; canDelete: boolean; edit: () => void; absence?: () => void; branch?: Id }) {
  const { t } = useI18n();
  const cache = useQueryClient();
  const confirm = useActionConfirm();
  const details = useRef<HTMLDetailsElement>(null);
  const mutation = useMutation({ mutationFn: (operation: LifecycleOperation) => managementApi.lifecycle({ business, kind, id, operation }), onSuccess: async () => { await Promise.all(managementQueryKeys.map(key => cache.invalidateQueries({ queryKey: [key] }))); } });
  const perform = async (operation: LifecycleOperation) => {
    if (details.current) details.current.open = false;
    if (!(await confirm({ title: `${t(`management.${operation}`)}: ${name}`, description: t(operation === "delete" ? "management.deleteHint" : "management.historyHint"), confirmLabel: t(`management.${operation}`), tone: operation === "activate" || operation === "restore" ? "neutral" : "warning" })).confirmed) return;
    mutation.mutate(operation);
  };
  const calendar = new URLSearchParams({ [kind === "services" ? "service" : kind === "branches" ? "branch" : "resource"]: String(id) });
  if (branch && kind !== "branches") calendar.set("branch", String(branch));
  return <div className="space-y-2">
    <div className="flex flex-wrap items-center gap-2">
      {canManage && !archived && <Button variant="secondary" onClick={edit}>{t("common.edit")}</Button>}
      <details ref={details} className="relative" onKeyDown={event => { if (event.key === "Escape" && details.current) { details.current.open = false; details.current.querySelector("summary")?.focus(); } }}>
        <summary className="platforma-focus-ring flex min-h-11 cursor-pointer list-none items-center rounded-control border border-platforma-border px-3 text-sm" aria-label={`${t("management.actions")}: ${name}`}>···</summary>
        <div className="absolute right-0 z-20 grid w-56 gap-1 rounded-control border border-platforma-border bg-white p-2 shadow-lg">
          <Link className="platforma-focus-ring p-2 text-sm text-brand-700" to={`/app/calendar?${calendar}`}>{t("management.appointments")}</Link>
          {absence && <Button variant="secondary" onClick={() => { if (details.current) details.current.open = false; absence(); }}>{t("management.unavailability")}</Button>}
          {canManage && <>
            {!archived && <Button variant="secondary" disabled={mutation.isPending} onClick={() => void perform(active ? "deactivate" : "activate")}>{t(active ? "management.deactivate" : "management.activate")}</Button>}
            <Button variant="secondary" disabled={mutation.isPending} onClick={() => void perform(archived ? "restore" : "archive")}>{t(archived ? "management.restore" : "management.archive")}</Button>
            {canDelete && <Button variant="warning" disabled={mutation.isPending} onClick={() => void perform("delete")}>{t("management.delete")}</Button>}
          </>}
        </div>
      </details>
    </div>
    {mutation.error && <ErrorState error={mutation.error} />}
  </div>;
}
