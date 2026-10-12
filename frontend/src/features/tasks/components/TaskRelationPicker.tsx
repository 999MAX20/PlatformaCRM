import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { taskRelationOptions, type TaskRelationType } from "../../../api/taskRelations";
import { Button } from "../../../components/ui/Button";
import { Input } from "../../../components/ui/Input";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";
import type { Id } from "../../../types";

export function TaskRelationPicker({ type, business, value, label, taskId, onChange }: {
  type: TaskRelationType; business: Id; value: string; label?: string; taskId?: Id;
  onChange: (value: string) => void;
}) {
  const { t } = useI18n();
  const [search, setSearch] = useState("");
  const query = useQuery({ queryKey: ["task-relation-options", business, type, search, taskId], queryFn: () => taskRelationOptions(type, business, search, taskId) });
  const options = query.data || [];
  return <div className="space-y-2">
    <Input aria-label={t("taskWorkspace.linkSearch")} placeholder={t("taskWorkspace.linkSearch")} value={search} onChange={e => setSearch(e.target.value)} />
    {query.isPending ? <LoadingState /> : query.error ? <ErrorState error={query.error} action={<Button variant="secondary" onClick={() => void query.refetch()}>{t("taskWorkspace.refresh")}</Button>} /> : <Select
      label={t(`taskWorkspace.link.${type}`)} value={value} onChange={e => onChange(e.target.value)}
      options={[{ value: "", label: t("taskWorkspace.none") }, ...(value && !options.some(v => v.value === value) ? [{ value, label: label || `#${value}` }] : []), ...options]} />}
  </div>;
}
