import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { leadsApi } from "../../api/leads";
import { dealsApi } from "../../api/deals";
import { teamApi } from "../../api/team";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { ErrorState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useAuth } from "../auth/AuthProvider";
import type { Deal, Lead } from "../../types";

export function LegacyAssignment({ source, kind }: { source: Lead | Deal; kind: "lead" | "deal" }) {
  const { t } = useI18n();
  const { user } = useAuth();
  const cache = useQueryClient();
  const [assignee, setAssignee] = useState("");
  const allowed = !source.is_archived && hasPermission(user, source.business, kind === "lead" ? "leads" : "deals", "update") && hasPermission(user, source.business, "team", "view");
  const members = useQuery({ queryKey: ["legacy-assignment-members", source.business, user?.id],
    queryFn: () => teamApi.allMembers(source.business), enabled: allowed });
  const save = useMutation<Lead | Deal>({ mutationFn: async () => kind === "lead"
    ? leadsApi.assign({ id: source.id, user_id: Number(assignee) })
    : dealsApi.update({ id: source.id, payload: { owner: Number(assignee) } }),
    onSuccess: async () => { setAssignee(""); await Promise.all([
      cache.invalidateQueries({ queryKey: ["legacy-record-links"] }),
      cache.invalidateQueries({ queryKey: ["legacy-history"] }),
      cache.invalidateQueries({ queryKey: ["specialist-retirement"] }),
      cache.invalidateQueries({ queryKey: ["crm-card"] }),
    ]); } });
  if (!allowed) return null;
  const current = "owner" in source ? source.owner : source.responsible_user;
  return <form className="flex flex-wrap items-end gap-2" onSubmit={event => { event.preventDefault(); if (assignee) save.mutate(); }}>
    <Select label={t("taskWorkspace.assignee")} value={assignee || String(current || "")} onChange={event => setAssignee(event.target.value)} disabled={members.isPending || members.isError || save.isPending}
      options={[{ value: "", label: t("records.all") }, ...(members.data || []).filter(item => item.is_active).map(item => ({ value: item.user.id, label: item.user.full_name || item.user.email }))]} />
    <Button type="submit" variant="secondary" disabled={!assignee || members.isError} isLoading={save.isPending}>{t("common.save")}</Button>
    {save.error ? <ErrorState error={save.error} /> : null}
    {members.error ? <ErrorState error={members.error} action={<Button type="button" onClick={() => void members.refetch()}>{t("common.retry")}</Button>} /> : null}
  </form>;
}
