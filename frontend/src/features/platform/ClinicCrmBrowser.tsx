import { useQuery } from "@tanstack/react-query";
import { Link, useLocation } from "react-router";
import { useEffect, useRef, useState, type ReactNode } from "react";
import { LockKeyhole } from "lucide-react";
import { clinicKinds, platformClinicApi, type ClinicKind, type ClinicRecord } from "../../api/platformClinic";
import { Button } from "../../components/ui/Button";
import { Card, CardBody } from "../../components/ui/Card";
import { Input } from "../../components/ui/Input";
import { Select } from "../../components/ui/Select";
import { Tabs } from "../../components/ui/Tabs";
import { EmptyState, LoadingState } from "../../components/ui/StateViews";
import { useDebouncedValue } from "../../hooks/useDebouncedValue";
import { useI18n } from "../../lib/i18n";
import { SupportError, retainSupportData, supportDate } from "../support/SupportUI";
import { ClinicPager, ClinicValueView, clinicStatuses, useClinicReadDenial } from "./ClinicReadUI";

type Props = { business: string; timezone: string; connections: boolean; params: URLSearchParams; update: (values: Record<string, string>) => void; onDenied: (error: unknown) => void };
export function ClinicCrmBrowser({ business, timezone, connections, params, update, onDenied }: Props) {
  const { t } = useI18n();
  const kinds = connections ? clinicKinds.slice(7) : clinicKinds.slice(0, 7);
  const kind = kinds.find(value => value === params.get("entity")) || kinds[0];
  const record = Number(params.get("record")) || 0;
  const list = useClinicRecords(business, kind, params);
  useClinicReadDenial(list.error, onDenied);
  const changeKind = (value: string) => update({ entity: value, record: "", page: "", search: "", status: "", archive: "", client: "" });
  const kindSelector = <Select aria-label={t("clinicCrm.records")} value={kind} options={kinds.map(value => ({ value, label: t(`clinicCrm.kind.${value}`) }))} onChange={event => changeKind(event.target.value)} className="w-full sm:w-44" />;
  return <div className="space-y-4" data-testid="clinic-crm">
    {connections && <Link className="platforma-focus-ring inline-block text-sm font-medium text-brand-700" to={`/platform/operations?section=connectors&business=${business}`}>{t("platform.nav.operations")}</Link>}
    <div className={record ? "grid items-start gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)]" : "min-w-0"}>
      <div className={record ? "hidden min-w-0 xl:block" : "min-w-0"} data-testid="clinic-record-list">
        <ClinicRecordList key={kind} business={business} timezone={timezone} kind={kind} params={params} update={update} onDenied={onDenied} kindSelector={kindSelector} list={list} />
      </div>
      {record > 0 && <div className="min-w-0 space-y-3">
        <div className="xl:hidden">{kindSelector}</div>
        <ClinicRecordDetail key={`${kind}-${record}`} business={business} timezone={timezone} kind={kind} record={record} enabled={!list.isFetching} params={params} update={update} onDenied={onDenied} />
      </div>}
    </div>
  </div>;
}

function useClinicRecords(business: string, kind: ClinicKind, params: URLSearchParams) {
  const search = params.get("search") || "";
  const needle = useDebouncedValue(search, 250);
  const page = Math.max(1, Math.floor(Number(params.get("page")) || 1));
  const size = [10, 20, 50].includes(Number(params.get("page_size"))) ? Number(params.get("page_size")) : 20;
  const status = params.get("status") || "";
  const archive = params.get("archive") || "active";
  const client = params.get("client") || "";
  const list = useQuery({ queryKey: ["platform-clinic-crm", business, kind, needle, status, archive, client, page, size],
    queryFn: () => platformClinicApi.list(business, kind, { search: needle, ...(status ? { status } : {}), archive, ...(client ? { client } : {}), page, page_size: size }), gcTime: 0, retry: false });
  return list;
}

function ClinicRecordList({ business, timezone, kind, params, update, kindSelector, list }: Omit<Props, "connections"> & { kind: ClinicKind; kindSelector: ReactNode; list: ReturnType<typeof useClinicRecords> }) {
  const { t } = useI18n();
  const location = useLocation();
  const search = params.get("search") || "";
  const page = Math.max(1, Math.floor(Number(params.get("page")) || 1));
  const size = [10, 20, 50].includes(Number(params.get("page_size"))) ? Number(params.get("page_size")) : 20;
  const status = params.get("status") || "";
  const archive = params.get("archive") || "active";
  const client = params.get("client") || "";
  return <div className="space-y-4">
    <div className="flex flex-wrap items-center gap-2 [&>label]:w-full sm:[&>label]:w-auto">
      {kindSelector}
      <Input aria-label={t("clinicCrm.search")} placeholder={t("clinicCrm.search")} value={search} maxLength={200} onChange={event => update({ search: event.target.value, page: "" })} className="sm:w-72" />
      {clinicStatuses[kind].length > 0 && <Select aria-label={t("supportCases.statusLabel")} value={status} options={[{ value: "", label: t("supportCases.allStatuses") }, ...clinicStatuses[kind].map(value => ({ value, label: t(`clinicCrm.value.${value}`) }))]} onChange={event => update({ status: event.target.value, page: "" })} className="w-full sm:w-48" />}
      {!(["payments", "connectors", "channels"] as ClinicKind[]).includes(kind) && <Select aria-label={t("clinicCrm.archive")} value={archive} options={["active", "archived", "all"].map(value => ({ value, label: t(`clinicCrm.archive.${value}`) }))} onChange={event => update({ archive: event.target.value, page: "" })} className="w-full sm:w-36" />}
      <Button variant="secondary" onClick={() => list.refetch()} isLoading={list.isFetching}>{t("common.refresh")}</Button>
      {(search || status || client || archive !== "active") && <Button variant="ghost" onClick={() => update({ search: "", status: "", client: "", archive: "", page: "" })}>{t("tasks.resetFilters")}</Button>}
      <p className="flex items-center gap-2 text-xs text-platforma-subtle sm:ml-auto"><LockKeyhole size={14} aria-hidden="true" />{t("clinicCrm.readOnly")}</p>
    </div>
    {client && <p className="text-sm">{t("clinicCrm.field.client")} #{client}</p>}
    {list.isError && <SupportError error={list.error} retry={() => list.refetch()} />}
    {list.isPending ? <LoadingState /> : list.isError && (!list.data || !retainSupportData(list.error)) ? null : list.data && <Card variant="outlined">
      {kind === "clients" && <div className="hidden grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.5fr)] gap-3 border-b border-platforma-border bg-surface-muted px-4 py-3 text-xs text-platforma-subtle sm:grid" aria-hidden="true">{["full_name", "phone", "email"].map(field => <span key={field}>{t(`clinicCrm.field.${field}`)}</span>)}</div>}
      {!list.data.results.length ? <EmptyState title={t("clinicCrm.empty")} /> : <ul className="divide-y divide-platforma-border">{list.data.results.map(row => {
        const next = new URLSearchParams(params); next.set("record", String(row.id));
        const selected = Number(params.get("record")) === row.id;
        return <li key={row.id} className={`grid gap-3 px-4 py-3 ${kind === "clients" ? "sm:grid-cols-[minmax(0,1.2fr)_minmax(0,1fr)_minmax(0,1.5fr)]" : "sm:grid-cols-2"} ${selected ? "bg-brand-50" : "hover:bg-surface-hover"}`} data-testid="clinic-record-row">
          <div className="min-w-0"><Link aria-current={selected ? "true" : undefined} className="platforma-focus-ring break-words text-sm font-semibold text-brand-700" to={`${location.pathname}?${next}`} state={location.state}>{kind === "channels" ? <ClinicValueView name="channel" value={row.title} timezone={timezone} /> : row.title}</Link><p className="mt-1 text-xs text-platforma-faint">#{row.id}{row.is_archived ? ` · ${t("clinicCrm.archive.archived")}` : ""}</p>
            {kind !== "clients" && <div className="mt-1 space-y-1 text-xs text-platforma-subtle">{row.status && <p><ClinicValueView name="status" value={row.status} timezone={timezone} /></p>}{row.relations.filter(item => item.field === "client" || item.field === "stage").map(item => <p className="break-words" key={item.field}>{t(`clinicCrm.field.${item.field}`)}: {item.label}</p>)}{row.people.slice(0, 1).map(item => <p className="break-words" key={item.field}>{t(`clinicCrm.field.${item.field}`)}: {item.name}</p>)}</div>}
          </div>
          {kind === "clients" ? ["phone", "email"].map(name => <dl className="min-w-0 text-sm" key={name}><dt className="text-xs text-platforma-faint sm:sr-only">{t(`clinicCrm.field.${name}`)}</dt><dd className="break-words"><ClinicValueView name={name} value={row.fields[name]} timezone={timezone} /></dd></dl>) : <dl className="min-w-0 space-y-1 text-sm">{Object.entries(row.fields).map(([name, value]) => <div key={name} className="break-words"><dt className="inline text-platforma-faint">{t(`clinicCrm.field.${name}`)}: </dt><dd className="inline"><ClinicValueView name={name} value={value} timezone={timezone} /></dd></div>)}</dl>}
        </li>;
      })}</ul>}
      <ClinicPager page={page} count={list.data.count} size={size} change={value => update({ page: String(value) })} changeSize={value => update({ page_size: String(value), page: "" })} />
    </Card>}
  </div>;
}

function ClinicRecordDetail({ business, timezone, kind, record, enabled, params, update, onDenied }: Omit<Props, "connections"> & { kind: ClinicKind; record: number; enabled: boolean }) {
  const { t } = useI18n();
  const location = useLocation();
  const detail = useQuery({ queryKey: ["platform-clinic-record", business, kind, record], queryFn: () => platformClinicApi.detail(business, kind, record), enabled, gcTime: 0, retry: false });
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => { if (detail.data) heading.current?.focus(); }, [detail.data?.id]);
  useClinicReadDenial(detail.error, onDenied);
  const back = new URLSearchParams(params); back.delete("record");
  const fields = detail.data ? Object.entries({ status: detail.data.status, ...detail.data.fields, created_at: detail.data.created_at, updated_at: detail.data.updated_at }) : [];
  const isPrimary = ([name, value]: (typeof fields)[number]) => !["full_name", "title", "created_at", "updated_at"].includes(name) && ((value !== null && value !== undefined && value !== "") || ["phone", "email"].includes(name));
  const renderField = ([name, value]: (typeof fields)[number]) => <div className="min-w-0" key={name}><dt className="text-xs text-platforma-faint">{t(`clinicCrm.field.${name}`)}</dt><dd className="mt-1 whitespace-pre-wrap break-words text-sm"><ClinicValueView name={name} value={value} timezone={timezone} /></dd></div>;
  return <div className="space-y-4" data-testid="clinic-record-detail">
    <div className="flex flex-wrap items-center justify-between gap-3"><Link className="platforma-focus-ring text-sm font-medium text-brand-700" to={`${location.pathname}?${back}`} state={location.state}>{t("clinicCrm.back")}</Link><Button variant="secondary" onClick={() => detail.refetch()} isLoading={detail.isFetching}>{t("common.refresh")}</Button></div>
    {detail.isError && <SupportError error={detail.error} retry={() => detail.refetch()} />}
    {detail.isPending ? <LoadingState /> : detail.isError && (!detail.data || !retainSupportData(detail.error)) ? null : detail.data && <>
      <Card variant="outlined"><CardBody className="space-y-4 p-4"><h2 ref={heading} tabIndex={-1} className="platforma-focus-ring rounded-control break-words text-lg font-semibold">{kind === "channels" ? <ClinicValueView name="channel" value={detail.data.title} timezone={timezone} /> : detail.data.title} <span className="text-sm font-normal text-platforma-faint">#{record}</span></h2>
        <dl className="grid gap-3 sm:grid-cols-2">{fields.filter(isPrimary).map(renderField)}
        {detail.data.people.map(person => <div className="min-w-0" key={person.field}><dt className="text-xs text-platforma-faint">{t(`clinicCrm.field.${person.field}`)}</dt><dd className="mt-1 break-words text-sm">{person.name}{!person.active && ` · ${t("clinicCrm.inactive")}`}</dd></div>)}</dl>
        {detail.data.relations.length > 0 && <div className="flex flex-wrap gap-3">{detail.data.relations.map(relation => <div key={relation.field} className="min-w-0 text-sm"><span className="text-platforma-faint">{t(`clinicCrm.field.${relation.field}`)}: </span>{relation.kind ? <button className="platforma-focus-ring break-words text-brand-700" onClick={() => update({ entity: relation.kind!, record: String(relation.id), page: "", client: "", search: "", status: "", archive: "" })}>{relation.label}</button> : <span className="break-words">{relation.label}</span>}</div>)}</div>}
        <details className="border-t border-platforma-border pt-2"><summary className="platforma-focus-ring cursor-pointer rounded-control py-1 text-sm text-platforma-subtle">{t("clinicCrm.moreDetails")}</summary><dl className="mt-3 grid gap-3 sm:grid-cols-2">{fields.filter(field => !isPrimary(field)).map(renderField)}</dl></details>
      </CardBody></Card>
      {kind === "clients" && <nav aria-label={t("clinicCrm.related")} className="flex flex-wrap gap-2">{clinicKinds.slice(1, 7).map(target => <Button variant="secondary" key={target} onClick={() => update({ entity: target, record: "", client: String(record), page: "", search: "", status: "", archive: "all" })}>{t(`clinicCrm.kind.${target}`)}</Button>)}</nav>}
      {Boolean(detail.data.sections?.length) && <ClinicRecordChildren business={business} timezone={timezone} record={detail.data} onAccessError={onDenied} />}
    </>}
  </div>;
}

function ClinicRecordChildren({ business, timezone, record, onAccessError }: { business: string; timezone: string; record: ClinicRecord; onAccessError: (error: unknown) => void }) {
  const { t, language } = useI18n();
  const [section, setSection] = useState(record.sections![0]);
  const [page, setPage] = useState(1);
  const list = useQuery({ queryKey: ["platform-clinic-children", business, record.kind, record.id, section, page], queryFn: () => platformClinicApi.children(business, record.kind, record.id, section, page), gcTime: 0, retry: false });
  useClinicReadDenial(list.error, onAccessError);
  return <Card>
    <Tabs value={section} options={record.sections!.map(value => ({ value, label: t(`clinicCrm.section.${value}`) }))} ariaLabel={t("clinicCrm.related")} idPrefix="clinic-children" appearance="underline" onChange={value => { setSection(value); setPage(1); }} />
    <section role="tabpanel" id={`clinic-children-panel-${section}`} aria-labelledby={`clinic-children-tab-${section}`}>
      <div className="flex justify-end p-3"><Button variant="secondary" onClick={() => list.refetch()} isLoading={list.isFetching}>{t("common.refresh")}</Button></div>
      {list.isError && <SupportError error={list.error} retry={() => list.refetch()} />}
      {list.isPending ? <LoadingState /> : list.isError && (!list.data || !retainSupportData(list.error)) ? null : list.data && <>
        {!list.data.results.length ? <EmptyState title={t("clinicCrm.empty")} /> : <ul className="divide-y divide-platforma-border">{list.data.results.map(item => <li className="space-y-2 p-4" key={item.id}>
          <div className="flex flex-wrap gap-2 text-xs text-platforma-faint"><span>{supportDate(item.created_at, language, timezone)}</span>{item.author && <span>{item.author}</span>}{["direction", "sender_type", "status"].map(name => item[name as keyof typeof item] ? <span key={name}><ClinicValueView name={name} value={item[name as "direction" | "sender_type" | "status"]} timezone={timezone} /></span> : null)}</div>
          {item.label && <p className="break-words text-sm font-medium">{item.label}</p>}{"value" in item && <p className="whitespace-pre-wrap break-words text-sm"><ClinicValueView name="value" value={item.value} timezone={timezone} /></p>}{item.text && <p className="whitespace-pre-wrap break-words text-sm">{item.text}</p>}
        </li>)}</ul>}
        <ClinicPager page={page} count={list.data.count} change={setPage} />
      </>}
    </section>
  </Card>;
}
