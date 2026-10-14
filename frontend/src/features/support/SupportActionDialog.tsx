import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { normalizeAppError } from "../../api/appError";
import { supportApi } from "../../api/support";
import { useActionConfirm } from "../../components/actions/ActionConfirmProvider";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { Textarea } from "../../components/ui/Textarea";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import type { SupportCase, SupportScope, SupportStatus } from "../../types/support";
import type { SupportDraftListener } from "./SupportThread";
import { SupportError } from "./SupportUI";

export type SupportAction = "assign" | "reopen" | SupportStatus;

export function SupportActionDialog({ item, scope, action, onClose, onDraft }: {
  item: SupportCase; scope: SupportScope; action: SupportAction; onClose: () => void; onDraft: SupportDraftListener;
}) {
  const { t } = useI18n();
  const confirm = useActionConfirm();
  const queryClient = useQueryClient();
  const [version, setVersion] = useState(item.version);
  const [reason, setReason] = useState("");
  const [assignee, setAssignee] = useState(item.assignee ? String(item.assignee.id) : "");
  const [search, setSearch] = useState("");
  const needle = useDebouncedValue(search, 250);
  const [refreshError, setRefreshError] = useState<unknown>(null);
  const [refreshing, setRefreshing] = useState(false);
  const staff = useQuery({ queryKey: ["support-staff", needle], queryFn: () => supportApi.staff(needle), enabled: action === "assign" });
  const save = useMutation({
    mutationFn: () => action === "assign" ? supportApi.assign(item.id, Number(assignee) || null, version)
      : action === "reopen" ? supportApi.reopen(scope, item.id, reason.trim(), version)
        : supportApi.transition(item.id, action, reason.trim(), version),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["support"] }); onClose(); },
  });
  const dirty = Boolean(reason.trim()) || assignee !== (item.assignee ? String(item.assignee.id) : "");
  useEffect(() => { onDraft("action", dirty, save.isPending); return () => onDraft("action", false, false); }, [dirty, save.isPending, onDraft]);
  const conflict = save.isError && normalizeAppError(save.error).category === "conflict";
  const needsReason = action === "reopen" || action === "resolved";
  const title = action === "assign" ? t("supportCases.assign") : action === "reopen" ? t("supportCases.reopen") : t(`supportCases.status.${action}`);
  async function close() {
    if (save.isPending) return;
    if (dirty) {
      const result = await confirm({ title: t("taskWorkspace.discardTitle"), confirmLabel: t("taskWorkspace.discard"), cancelLabel: t("taskWorkspace.keepEditing"), tone: "warning" });
      if (!result.confirmed) return;
    }
    onClose();
  }
  async function refreshVersion() {
    setRefreshing(true); setRefreshError(null);
    try {
      const current = await supportApi.detail(scope, item.id);
      setVersion(current.version); save.reset();
      queryClient.setQueryData(["support", scope.platform ? "platform" : "clinic", scope.business, "case", item.id], current);
    } catch (error) { setRefreshError(error); } finally { setRefreshing(false); }
  }
  const options = (staff.data?.results || []).map(user => ({ value: String(user.id), label: user.name }));
  if (item.assignee && !options.some(option => option.value === String(item.assignee!.id))) options.unshift({ value: String(item.assignee.id), label: item.assignee.name });
  const actionAllowed = action === "assign" ? item.available_actions.assign : action === "reopen" ? item.available_actions.reopen : item.available_actions.transitions.includes(action);
  return <Modal open title={title} onClose={() => void close()} closeOnBackdrop={false} testId="support-action-dialog">
    <form className="space-y-4" onSubmit={event => { event.preventDefault(); save.mutate(); }}>
      {action === "assign" ? <>
        <Input label={t("supportCases.staffSearch")} value={search} onChange={event => setSearch(event.target.value)} disabled={save.isPending} />
        <Select label={t("supportCases.assignee")} value={assignee} onChange={event => setAssignee(event.target.value)} options={[{ value: "", label: t("supportCases.filter.unassigned") }, ...options]} disabled={save.isPending} />
        {staff.isError && <SupportError error={staff.error} retry={() => staff.refetch()} />}
      </> : <Textarea label={t(action === "resolved" ? "supportCases.outcome" : "supportCases.reason")} value={reason} onChange={event => setReason(event.target.value)} required={needsReason} maxLength={4000} disabled={save.isPending} autoFocus />}
      {save.isError && <SupportError error={save.error} />}
      {conflict && <Button type="button" variant="secondary" onClick={() => void refreshVersion()} isLoading={refreshing}>{t("supportCases.refreshVersion")}</Button>}
      {Boolean(refreshError) && <SupportError error={refreshError} retry={() => void refreshVersion()} />}
      {!actionAllowed && <p role="alert" className="text-sm text-platforma-warning">{t("supportCases.actionUnavailable")}</p>}
      <div className="flex flex-wrap justify-end gap-2">
        <Button type="button" variant="ghost" onClick={() => void close()} disabled={save.isPending}>{t("common.cancel")}</Button>
        <Button type="submit" isLoading={save.isPending} disabled={conflict || refreshing || !actionAllowed || (needsReason && !reason.trim())}>{t("common.save")}</Button>
      </div>
    </form>
  </Modal>;
}
