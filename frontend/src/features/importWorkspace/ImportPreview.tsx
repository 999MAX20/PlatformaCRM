import { ImportEntityCard } from "./ImportEntityCard";
import { describeImportErrors, displayImportValue } from "./importViewModel";
import { useState } from "react";
import { Link } from "react-router";
import type { ImportWorkspace, ImportReportRow, ImportEntity } from "../../api/importWorkspace";
import { importEntities } from "../../api/importWorkspace";
import { CrmDataTable } from "../../components/crm/CrmDataTable";
import { Card } from "../../components/ui/Card";
import { Button } from "../../components/ui/Button";
import { Select } from "../../components/ui/Select";
import { Modal } from "../../components/ui/Modal";
import { useI18n } from "../../lib/i18n";
import { ImportCalendar } from "./ImportCalendar";


export function ImportPreview({ workspace, timezone, onEdit }: { workspace: ImportWorkspace; timezone: string; onEdit: (source: number, row: number) => void }) {
  const { t } = useI18n(); const label = (key: string) => t(`importWorkspace.${key}`);
  const [kind, setKind] = useState<ImportEntity>(workspace.sources[0]?.entity_type || "clients");
  const [mode, setMode] = useState("table"); const [selected, setSelected] = useState<ImportReportRow | null>(null); const [page, setPage] = useState(1);
  const imported = workspace.state === "imported";
  const outcomeLabel = (key: string) => label(imported && ["created", "updated"].includes(key) ? `result.${key}` : key);
  const report = imported ? workspace.result : workspace.report;
  const rows = (report.rows || []).filter(row => row.entity_type === kind);
  const sourceList = workspace.sources.filter(source => source.entity_type === kind);
  const columns = [...new Set(sourceList.flatMap(source => source.columns))];
  const fields = sourceList.flatMap(source => source.fields);
  const fieldLabel = (key: string) => key.startsWith("custom.") ? fields.find(field => `custom.${field.key}` === key)?.label || key : label(`field.${key}`);
  const value = (row: ImportReportRow, key: string) => {
    if (key.startsWith("custom.")) return row.custom[key.slice(7)]?.value;
    if (key === "client_ref") return row.values.client_name || row.values[key];
    if (key === "service_ref") return row.values.service_name || row.values[key];
    if (key === "specialist_ref") return row.values.specialist_name || row.values[key];
    if (key === "status") return t(`appointment.status.${row.values[key] || "created"}`);
    return row.values[key];
  };
  const link = (row: ImportReportRow) => row.id ? ({ clients: `/app/clients/${row.id}`, appointments: `/app/appointments/${row.id}`, services: `/app/business/services?service=${row.id}`, specialists: `/app/business/resources?resource=${row.id}` }[row.entity_type]) : null;
  if (report.access_changed) return <p role="alert">{label("accessChanged")}</p>;
  return <div className="space-y-4">
    <div className="flex flex-wrap gap-3">
      {report.summary && Object.entries(report.summary).map(([key, count]) => <div key={key} className="rounded-control border border-platforma-border bg-surface-card px-3 py-2 text-sm"><span className="text-platforma-muted">{outcomeLabel(key)}</span> <strong>{count}</strong></div>)}
    </div>
    {!!report.errors?.length && <Card padding="md" variant="danger"><h3 className="font-semibold">{label("errors")} · {report.errors.length}</h3><ul className="mt-2 max-h-64 space-y-2 overflow-auto">{report.errors.map(error => <li key={`${error.source_id}:${error.row}`} className="flex flex-wrap items-center gap-2 text-sm"><Button size="sm" variant="secondary" onClick={() => onEdit(error.source_id, error.row)}>{workspace.sources.find(source => source.id === error.source_id)?.filename} · {label("row")} {error.row}</Button><span className="break-words">{describeImportErrors(error.errors, t)}</span></li>)}</ul></Card>}
    <div className="flex flex-wrap items-end gap-3">
      <Select label={label("entity")} value={kind} options={importEntities.filter(entity => workspace.sources.some(source => source.entity_type === entity)).map(entity => ({ value: entity, label: label(entity) }))} onChange={event => { setKind(event.target.value as ImportEntity); setPage(1); }} />
      {kind === "appointments" && <div className="flex gap-2">{["table", "calendar"].map(item => <Button key={item} size="sm" variant={mode === item ? "primary" : "secondary"} onClick={() => setMode(item)}>{label(item)}</Button>)}</div>}
    </div>
    {mode === "calendar" && kind === "appointments" ? <ImportCalendar report={report} sources={workspace.sources} business={workspace.business} timezone={timezone} onSelect={setSelected} onEdit={onEdit} /> : <CrmDataTable contentClassName="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="bg-surface-muted"><tr><th className="px-3 py-2">{label("row")}</th>{columns.map(key => <th key={key} className="px-3 py-2">{fieldLabel(key)}</th>)}<th className="px-3 py-2">{label("result")}</th><th className="px-3 py-2">{label("card")}</th></tr></thead><tbody>{rows.slice((page - 1) * 50, page * 50).map(row => <tr key={row.reference} className="border-t border-platforma-border"><td className="px-3 py-2">{row.row}</td>{columns.map(key => <td key={key} className="max-w-64 truncate px-3 py-2">{displayImportValue(value(row, key))}</td>)}<td className="px-3 py-2">{outcomeLabel(row.outcome)}</td><td className="px-3 py-2"><Button variant="ghost" size="sm" onClick={() => setSelected(row)}>{label("card")}</Button></td></tr>)}</tbody></table></CrmDataTable>}
    {!rows.length && <p className="text-sm text-platforma-muted">{label("noRows")}</p>}
    <div className="flex justify-end gap-2"><Button size="sm" variant="secondary" disabled={page === 1} onClick={() => setPage(page - 1)}>{label("previous")}</Button><span className="self-center text-sm">{page} / {Math.max(1, Math.ceil(rows.length / 50))}</span><Button size="sm" variant="secondary" disabled={page * 50 >= rows.length} onClick={() => setPage(page + 1)}>{label("next")}</Button></div>
    <Modal open={!!selected} title={label("card")} onClose={() => setSelected(null)} size="lg">{selected && <Card padding="md"><h3 className="mb-4 text-lg font-semibold">{String(selected.values.full_name || selected.values.name || selected.values.client_name || label(selected.entity_type))}</h3><ImportEntityCard key={selected.reference} row={selected} workspace={workspace} />
      {!!selected.before_version && <section className="mt-4 space-y-2"><h4 className="text-sm font-semibold">{label("changes")}</h4><table className="w-full text-left text-sm"><thead><tr><th>{label("targetField")}</th><th>{label("before")}</th><th>{label("after")}</th></tr></thead><tbody>{[...Object.keys(selected.before || {}), ...Object.keys(selected.before_custom || {}).map(key => `custom.${key}`)].filter(key => {
        const before = key.startsWith("custom.") ? selected.before_custom?.[key.slice(7)]?.value : selected.before?.[key];
        const after = key.startsWith("custom.") ? selected.custom[key.slice(7)]?.value : selected.values[key];
        return JSON.stringify(before) !== JSON.stringify(after);
      }).map(key => <tr key={key} className="border-t border-platforma-border"><th className="py-2 font-medium">{fieldLabel(key)}</th><td className="break-words p-2">{displayImportValue(key.startsWith("custom.") ? selected.before_custom?.[key.slice(7)]?.value : selected.before?.[key])}</td><td className="break-words p-2">{displayImportValue(key.startsWith("custom.") ? selected.custom[key.slice(7)]?.value : selected.values[key])}</td></tr>)}</tbody></table></section>}
      <div className="mt-4 flex justify-end">{imported && link(selected) ? <Link className="text-sm font-semibold text-brand-700 underline" to={link(selected)!}>{label("open")}</Link> : <Button variant="secondary" onClick={() => { onEdit(selected.source_id, selected.row); setSelected(null); }}>{label("edit")}</Button>}</div></Card>}</Modal>
  </div>;
}
