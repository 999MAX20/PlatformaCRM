import { ImportErrorNotice } from "./ImportErrorNotice";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { importWorkspaceApi, type ImportSource, type ImportSourceRow, type ImportDecision, type ImportEntity } from "../../api/importWorkspace";
import { getApiErrorMessage } from "../../api/client";
import { CrmDataTable } from "../../components/crm/CrmDataTable";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { useAuth } from "../auth/AuthProvider";

export function SourceRows({ workspaceId, version, source, onChange, disabled, initialRow }: {
  workspaceId: number; version: number; source: ImportSource; onChange: (source: ImportSource) => void; disabled: boolean; initialRow?: number;
}) {
  const { user } = useAuth();
  const { t } = useI18n(); const label = (key: string) => t(`importWorkspace.${key}`);
  const [page, setPage] = useState(initialRow ? Math.ceil(initialRow / 50) : 1);
  const [selected, setSelected] = useState<ImportSourceRow | null>(null);
  const rows = useQuery({ queryKey: ["import-source-rows", workspaceId, user?.id, source.id, version, page], queryFn: () => importWorkspaceApi.rows(workspaceId, source.id, page), staleTime: 0 });
  const opened = useRef<number | undefined>(undefined);
  useEffect(() => {
    if (!rows.error && initialRow && opened.current !== initialRow) {
      const row = rows.data?.results.find(item => item.row === initialRow);
      if (row) { opened.current = initialRow; setSelected(row); }
    }
  }, [initialRow, rows.data, rows.error]);
  return <div className="space-y-3">
    {rows.isLoading && <LoadingState />}
    {rows.error && <ImportErrorNotice error={rows.error} message={getApiErrorMessage(rows.error)} action={<Button size="sm" variant="secondary" onClick={() => { void rows.refetch(); }}>{label("reload")}</Button>} />}
    <CrmDataTable contentClassName="overflow-x-auto">
      <table className="w-full text-left text-sm"><thead className="bg-surface-muted"><tr><th className="px-3 py-2">{label("row")}</th>{source.headers.map(header => <th key={header} className="max-w-64 px-3 py-2">{header}</th>)}<th className="px-3 py-2">{label("edit")}</th></tr></thead>
        <tbody>{(!rows.error ? rows.data?.results : [])?.map(row => <tr key={row.row} className="border-t border-platforma-border">
          <td className="px-3 py-2">{row.row}{source.excluded.includes(row.row) && <span className="block text-xs text-platforma-muted">{label("skipped")}</span>}</td>
          {source.headers.map(header => <td key={header} className="max-w-64 truncate px-3 py-2" title={source.corrections[String(row.row)]?.[header] ?? row.values[header]}>{source.corrections[String(row.row)]?.[header] ?? row.values[header]}</td>)}
          <td className="px-3 py-2"><Button size="sm" variant="ghost" disabled={disabled} onClick={() => setSelected(row)} aria-label={`${label("edit")}: ${label("row")} ${row.row}`}>{label("edit")}</Button></td>
        </tr>)}</tbody></table>
    </CrmDataTable>
    <div className="flex justify-end gap-2"><Button size="sm" variant="secondary" disabled={page === 1 || rows.isFetching} onClick={() => setPage(page - 1)}>{label("previous")}</Button><span className="self-center text-sm">{page} / {Math.max(1, Math.ceil((rows.data?.count || 0) / 50))}</span><Button size="sm" variant="secondary" disabled={page * 50 >= (rows.data?.count || 0) || rows.isFetching} onClick={() => setPage(page + 1)}>{label("next")}</Button></div>
    {selected && !rows.error && <RowEditor key={selected.row} workspaceId={workspaceId} source={source} row={selected} onClose={() => setSelected(null)} onSave={next => { onChange(next); setSelected(null); }} />}
  </div>;
}

function RowEditor({ workspaceId, source, row, onClose, onSave }: { workspaceId: number; source: ImportSource; row: ImportSourceRow; onClose: () => void; onSave: (source: ImportSource) => void }) {
  const { user } = useAuth();
  const { t } = useI18n(); const label = (key: string) => t(`importWorkspace.${key}`);
  const [values, setValues] = useState({ ...row.values, ...source.corrections[String(row.row)] });
  const [excluded, setExcluded] = useState(source.excluded.includes(row.row));
  const [decision, setDecision] = useState<ImportDecision>(source.resolutions[String(row.row)] || { action: "create" });
  const [search, setSearch] = useState("");
  const [targetLabel, setTargetLabel] = useState("");
  const candidates = useQuery({ queryKey: ["import-targets", workspaceId, user?.id, source.entity_type, search], queryFn: () => importWorkspaceApi.candidates(workspaceId, source.entity_type, search), enabled: source.entity_type !== "appointments" && (decision.action === "fill" || decision.action === "update") });
  return <Modal open title={`${label("row")} ${row.row}`} onClose={onClose} size="lg">
    <div className="space-y-4">
      {source.headers.map(header => {
        const target = Object.keys(source.mapping).find(key => source.mapping[key] === header);
        const kind = ({ client_ref: "clients", service_ref: "services", specialist_ref: "specialists" } as Record<string, ImportEntity>)[target || ""];
        return <div key={header} className="space-y-1">
          {kind ? <ReferencePicker workspaceId={workspaceId} kind={kind} label={header} value={values[header]} onSelect={token => setValues({ ...values, [header]: token })} /> : <Input label={header} value={values[header]} onChange={event => setValues({ ...values, [header]: event.target.value })} />}
          <p className="break-words text-xs text-platforma-muted">{label("original")}: {row.original[header] || "—"}</p>

        </div>;
      })}
      <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={excluded} onChange={event => setExcluded(event.target.checked)} />{label("exclude")}</label>
      {!excluded && <>
        <Select label={label("decision")} value={decision.action} options={(source.entity_type === "appointments" ? ["create", "skip"] : ["create", "fill", "update", "skip"]).map(value => ({ value, label: label(value) }))} onChange={event => { setDecision({ action: event.target.value as ImportDecision["action"] }); setTargetLabel(""); }} />
        {(decision.action === "fill" || decision.action === "update") && <div className="space-y-2">
          <Input label={label("target")} value={search} onChange={event => setSearch(event.target.value)} placeholder={label("search")} />
          {targetLabel && <p className="text-sm font-semibold">{targetLabel}</p>}
          {candidates.error && <ImportErrorNotice error={candidates.error} />}
          <div className="max-h-40 overflow-auto rounded-control border border-platforma-border">
            {(!candidates.error ? candidates.data?.results : [])?.map(candidate => <Button key={candidate.id} variant={decision.target_id === candidate.id ? "primary" : "ghost"} className="w-full justify-start" onClick={() => { setDecision({ ...decision, target_id: candidate.id }); setTargetLabel(candidate.label); }}>{candidate.label}</Button>)}
          </div>
        </div>}
        {decision.action === "update" && <div className="flex flex-wrap gap-3">{Object.keys(source.mapping).filter(key => key !== "external_id").map(key => <label key={key} className="flex items-center gap-2 text-sm"><input type="checkbox" checked={decision.update_fields?.includes(key) || false} onChange={event => setDecision({ ...decision, update_fields: event.target.checked ? [...(decision.update_fields || []), key] : decision.update_fields?.filter(field => field !== key) })} />{key.startsWith("custom.") ? source.fields.find(field => `custom.${field.key}` === key)?.label : label(`field.${key}`)}</label>)}</div>}
      </>}
      <div className="flex justify-end gap-2"><Button variant="secondary" onClick={onClose}>{label("close")}</Button><Button onClick={() => onSave({ ...source, corrections: { ...source.corrections, [String(row.row)]: values }, excluded: excluded ? [...new Set([...source.excluded, row.row])] : source.excluded.filter(number => number !== row.row), resolutions: { ...source.resolutions, [String(row.row)]: decision } })}>{label("save")}</Button></div>
    </div>
  </Modal>;
}

function ReferencePicker({ workspaceId, kind, label, value, onSelect }: { workspaceId: number; kind: ImportEntity; label: string; value: string; onSelect: (value: string) => void }) {
  const { user } = useAuth();
  const { t } = useI18n(); const [search, setSearch] = useState(""); const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"existing" | "source">("source"); const [page, setPage] = useState(1);
  const linked = /^(crm|row):/.test(value);
  const selected = useQuery({ queryKey: ["import-reference", workspaceId, user?.id, kind, value], queryFn: () => importWorkspaceApi.references(workspaceId, kind, { reference: value }), enabled: linked });
  const candidates = useQuery({ queryKey: ["import-targets", workspaceId, user?.id, kind, search], queryFn: () => importWorkspaceApi.candidates(workspaceId, kind, search), enabled: open && mode === "existing" });
  const staged = useQuery({ queryKey: ["import-reference-choices", workspaceId, user?.id, kind, search, page], queryFn: () => importWorkspaceApi.references(workspaceId, kind, { search, page }), enabled: open && mode === "source" });
  return <div className="space-y-2">
    <Input label={label} value={linked ? (!selected.error ? selected.data?.results[0]?.label : undefined) || t(selected.isLoading ? "importWorkspace.processing" : "importWorkspace.referenceUnavailable") : value} readOnly={linked} onChange={event => onSelect(event.target.value)} />
    {selected.error && <ImportErrorNotice error={selected.error} />}
    <div className="flex gap-2"><Button size="sm" variant="ghost" aria-expanded={open} onClick={() => setOpen(!open)}>{t("importWorkspace.choose")} · {t(`importWorkspace.${kind}`)}</Button>{linked && <Button size="sm" variant="ghost" onClick={() => onSelect("")}>{t("importWorkspace.clearReference")}</Button>}</div>
    {open && <><div className="flex gap-2">{(["source", "existing"] as const).map(option => <Button key={option} size="sm" variant={mode === option ? "secondary" : "ghost"} onClick={() => { setMode(option); setPage(1); }}>{t(`importWorkspace.reference.${option}`)}</Button>)}</div>
      <Input aria-label={t("importWorkspace.search")} value={search} onChange={event => { setSearch(event.target.value); setPage(1); }} />
      {(mode === "source" ? staged.error : candidates.error) && <ImportErrorNotice error={mode === "source" ? staged.error : candidates.error} />}
      {(mode === "source" ? staged.isFetching : candidates.isFetching) && <LoadingState />}
      <div className="max-h-36 overflow-auto">{(mode === "source" ? (!staged.error ? staged.data?.results : []) : (!candidates.error ? candidates.data?.results : [])?.map(item => ({ reference: `crm:${item.id}`, label: item.label })))?.map(item => <Button key={item.reference} variant="ghost" className="w-full justify-start" onClick={() => { onSelect(item.reference); setOpen(false); }}>{item.label}</Button>)}</div>
      {mode === "source" && <div className="flex justify-end gap-2"><Button size="sm" variant="ghost" disabled={page === 1 || staged.isFetching} onClick={() => setPage(page - 1)}>{t("importWorkspace.previous")}</Button><Button size="sm" variant="ghost" disabled={page * 50 >= (staged.data?.count || 0) || staged.isFetching} onClick={() => setPage(page + 1)}>{t("importWorkspace.next")}</Button></div>}
    </>}
  </div>;
}
