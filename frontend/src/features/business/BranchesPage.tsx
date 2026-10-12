import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router";
import { branchesApi, type Branch } from "../../api/branches";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { BusinessWorkspaceNav } from "./components/BusinessWorkspaceNav";
import { BranchEditor } from "./components/BranchEditor";

export function BranchesPage() {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { setPageHeader } = usePageHeader();
  const [params, setParams] = useSearchParams();
  const [creating, setCreating] = useState(false);
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["branches", business?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  const branches = query.data || [];
  const selected = branches.find((item) => String(item.id) === params.get("branch")) || branches[0];
  const canManage = hasPermission(user, business?.id, "settings", "update");
  useEffect(() => { setPageHeader({ title: t("branches.title") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const save = useMutation({ mutationFn: (payload: Partial<Branch>) => branchesApi.create({ ...payload, business: business!.id }),
    onSuccess: async (branch) => { await client.invalidateQueries({ queryKey: ["branches"] }); setParams({ branch: String(branch.id) }); setCreating(false); } });
  return <div className="space-y-4"><BusinessWorkspaceNav />
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} /> : <>
      <div className="flex flex-wrap items-end gap-3">
        {!!branches.length && <Select label={t("branches.branch")} value={selected?.id || ""} onChange={(event) => { setParams({ branch: event.target.value }); setCreating(false); }} options={branches.map((item) => ({ value: item.id, label: `${item.name}${item.archived_at ? ` · ${t("branches.archived")}` : !item.is_active ? ` · ${t("branches.paused")}` : ""}` }))} />}
        {canManage && <Button onClick={() => setCreating(true)}>{t("branches.add")}</Button>}
      </div>
      {creating && <BranchDetailsForm onSave={(payload) => save.mutateAsync(payload)} pending={save.isPending} onCancel={() => setCreating(false)} />}
      {save.error && <ErrorState error={save.error} />}
      {!branches.length && !creating && <p className="text-sm text-platforma-subtle">{t("branches.empty")}</p>}
      {selected && !creating && <BranchEditor key={selected.id} branch={selected} branches={branches} />}
    </>}
  </div>;
}

export function BranchDetailsForm({ branch, onSave, pending, onCancel }: { branch?: Branch; onSave: (payload: Partial<Branch>) => Promise<unknown>; pending: boolean; onCancel?: () => void }) {
  const { t } = useI18n();
  const [name, setName] = useState(branch?.name || "");
  const [address, setAddress] = useState(branch?.address || "");
  const [phone, setPhone] = useState(branch?.phone || "");
  return <form className="grid gap-4 rounded-card border border-platforma-border bg-surface-card p-4" onSubmit={(event) => { event.preventDefault(); void onSave({ name, address, phone }).catch(() => undefined); }}>
    <Input label={t("branches.name")} required maxLength={255} value={name} onChange={(event) => setName(event.target.value)} />
    <Input label={t("branches.address")} value={address} onChange={(event) => setAddress(event.target.value)} />
    <Input label={t("branches.phone")} type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} />
    <div className="flex gap-2"><Button type="submit" isLoading={pending} disabled={!!branch && (!branch.can_manage || !!branch.archived_at)}>{t("common.save")}</Button>{onCancel && <Button type="button" variant="secondary" onClick={onCancel}>{t("common.cancel")}</Button>}</div>
  </form>;
}
