import { DraftGuard } from "../../components/actions/DraftGuard";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import { Plus } from "lucide-react";
import { branchesApi, type Branch } from "../../api/branches";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { usePageLoading } from "../../components/ui/PageLoadingBoundary";
import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import { BusinessWorkspaceNav } from "./components/BusinessWorkspaceNav";
import { BranchEditor } from "./components/BranchEditor";
import { BranchStatusBadge } from "./components/BranchStatusBadge";
import { cn } from "../../lib/cn";

export function BranchesPage() {
  const { t } = useI18n();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const { setPageHeader } = usePageHeader();
  const [params, setParams] = useSearchParams();
  const creating = params.get("create") === "1";
  const setCreating = (value: boolean) => setParams(previous => { const next = new URLSearchParams(previous); if (value) next.set("create", "1"); else next.delete("create"); return next; });
  const client = useQueryClient();
  const query = useQuery({ queryKey: ["branches", business?.id], queryFn: () => branchesApi.listAll({ business: business!.id }), enabled: !!business });
  const branches = query.data || [];
  usePageLoading(query.isLoading);
  const archived = params.get("archived") === "1";
  const visibleBranches = branches.filter(branch => Boolean(branch.archived_at) === archived);
  const selectionKey = archived ? "archived_branch" : "branch";
  const selected = visibleBranches.find((item) => String(item.id) === params.get(selectionKey)) || visibleBranches[0];
  const selectBranch = (id: string) => setParams(previous => {
    const next = new URLSearchParams(previous); next.set(selectionKey, id); next.delete("create"); next.delete("section"); return next;
  });
  useEffect(() => {
    const workingBranch = query.data?.find(item => String(item.id) === params.get("branch"));
    if (!workingBranch?.archived_at) return;
    const nextBranch = query.data?.find(item => !item.archived_at && (item.can_work || item.can_manage));
    setParams(previous => {
      const next = new URLSearchParams(previous);
      if (nextBranch) next.set("branch", String(nextBranch.id)); else next.delete("branch");
      return next;
    }, { replace: true });
  }, [query.data, params, setParams]);
  const canManage = hasPermission(user, business?.id, "settings", "update");
  useEffect(() => { setPageHeader({ title: t("nav.business") }); return () => setPageHeader(null); }, [setPageHeader, t]);
  const save = useMutation({ mutationFn: (payload: Partial<Branch>) => branchesApi.create({ ...payload, business: business!.id }),
    onSuccess: async () => { await Promise.all(["branches", "branch-catalog", "branch-configuration", "available-slots"].map(key => client.invalidateQueries({ queryKey: [key] }))); } });
  return <div className="space-y-5"><BusinessWorkspaceNav />
    {query.isLoading ? <LoadingState /> : query.error ? <ErrorState error={query.error} action={<Button onClick={() => query.refetch()}>{t("common.retry")}</Button>} /> : <>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 className="flex items-center gap-3 text-base font-semibold">{t("branches.title")}<span className="text-sm font-normal tabular-nums text-platforma-subtle">{visibleBranches.length}</span></h2>
        <Button variant="secondary" aria-pressed={archived} onClick={() => setParams(previous => { const next = new URLSearchParams(previous); if (archived) next.delete("archived"); else next.set("archived", "1"); next.delete("create"); next.delete("section"); return next; })}>{t("business.archive")}</Button>
        {canManage && <Button onClick={() => setCreating(true)}><Plus size={17} aria-hidden="true" />{t("branches.add")}</Button>}
      </div>
      {save.error && <ErrorState error={save.error} />}
      <div className={cn("grid items-start gap-4", visibleBranches.length > 1 ? "lg:grid-cols-[17rem_minmax(0,1fr)]" : "mx-auto w-full max-w-3xl")}>
        {visibleBranches.length > 1 && <>
          <div className="lg:hidden"><Select label={t("branches.branch")} value={selected?.id || ""}
            onChange={event => selectBranch(event.target.value)}
            options={visibleBranches.map(branch => ({ value: branch.id, label: branch.name }))} /></div>
          <nav aria-label={t("branches.title")} className="hidden space-y-2 rounded-card border border-platforma-border bg-surface-card p-3 lg:block">
            {visibleBranches.map(branch => <button key={branch.id} type="button" aria-current={!creating && selected?.id === branch.id ? "page" : undefined}
              onClick={() => selectBranch(String(branch.id))}
              className={cn("platforma-focus-ring flex w-full flex-col items-start gap-2 rounded-control border p-3 text-left", !creating && selected?.id === branch.id ? "border-brand-200 bg-brand-50" : "border-transparent hover:bg-surface-hover")}>
              <span className="max-w-full break-words text-sm font-semibold">{branch.name}</span>
              <BranchStatusBadge branch={branch} />
              {branch.address && <span className="max-w-full break-words text-xs text-platforma-subtle">{branch.address}</span>}
            </button>)}
          </nav>
        </>}
        <div className="min-w-0 rounded-card border border-platforma-border bg-surface-card p-4 sm:p-6">
          {creating ? <div className="space-y-4"><h3 className="text-lg font-semibold">{t("branches.add")}</h3>{save.error && <ErrorState error={save.error} />}<BranchDetailsForm onSave={payload => save.mutateAsync(payload)} onSaved={branch => setParams({ branch: String((branch as Branch).id) })} pending={save.isPending} onCancel={() => setCreating(false)} /></div>
            : selected ? <BranchEditor key={selected.id} branch={selected} branches={branches} />
              : <p className="text-sm text-platforma-subtle">{t("branches.empty")}</p>}
        </div>
      </div>
    </>}
  </div>;
}

export function BranchDetailsForm({ branch, onSave, pending, onCancel, onSaved }: { branch?: Branch; onSave: (payload: Partial<Branch>) => Promise<unknown>; pending: boolean; onCancel?: () => void; onSaved?: (result: unknown) => void }) {
  const { t } = useI18n();
  const [saved, setSaved] = useState(JSON.stringify([branch?.name || "", branch?.address || "", branch?.phone || ""]));
  const [name, setName] = useState(branch?.name || "");
  const [address, setAddress] = useState(branch?.address || "");
  const [phone, setPhone] = useState(branch?.phone || "");
  const dirty = JSON.stringify([name, address, phone]) !== saved;
  const savedRef = useRef(false);
  return <form className="grid gap-4 rounded-card border border-platforma-border bg-surface-card p-4" onChange={() => { savedRef.current = false; }} onSubmit={(event) => { event.preventDefault(); if (!name.trim()) return; void onSave({ name: name.trim(), address: address.trim(), phone: phone.trim() }).then(result => { savedRef.current = true; setSaved(JSON.stringify([name, address, phone])); onSaved?.(result); }).catch(() => undefined); }}>
    <DraftGuard dirty={dirty} pending={pending} saved={savedRef} />
    <Input label={t("branches.name")} required maxLength={255} value={name} onChange={(event) => setName(event.target.value)} />
    <Input label={t("branches.address")} value={address} onChange={(event) => setAddress(event.target.value)} />
    <Input label={t("branches.phone")} type="tel" value={phone} onChange={(event) => setPhone(event.target.value)} />
    <div className="flex gap-2"><Button type="submit" isLoading={pending} disabled={!name.trim() || (!!branch && (!branch.can_manage || !!branch.archived_at))}>{t("common.save")}</Button>{onCancel && <Button type="button" variant="secondary" onClick={onCancel}>{t("common.cancel")}</Button>}</div>
  </form>;
}
