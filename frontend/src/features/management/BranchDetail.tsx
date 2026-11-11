import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router";
import { branchesApi, type Branch } from "../../api/branches";
import type { ManagementCatalog, ManagementKind } from "../../api/management";
import { Button } from "../../components/ui/Button";
import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { todayInTimeZone } from "../../lib/format";
import type { Id } from "../../types";
import { scheduleCell, weekDates, weekdayKeys } from "../business/schedule";
import { EntityActions } from "./EntityActions";

export function BranchDetail({ branch, data, business, edit, openEntity }: { branch: Branch; data: ManagementCatalog; business: Id; edit: () => void; openEntity: (kind: ManagementKind, id: Id) => void }) {
  const { t } = useI18n();
  const config = useQuery({ queryKey: ["branch-configuration", branch.id], queryFn: () => branchesApi.configuration(branch.id) });
  const days = weekDates(todayInTimeZone(data.timezone));
  const services = data.services.filter(service => data.offers.some(offer => offer.branch === branch.id && offer.service === service.id && offer.is_active));
  const staff = data.resources.filter(resource => data.assignments.some(link => link.branch === branch.id && link.resource === resource.id && link.is_active));
  const rooms = data.resources.filter(resource => resource.branch === branch.id && resource.resource_type !== "staff" && !resource.archived_at);
  return <article className="min-w-0 space-y-6">
    <div className="flex flex-wrap items-start justify-between gap-4 border-b border-platforma-border pb-5">
      <div className="min-w-0 space-y-2"><h3 className="break-words text-xl font-semibold">{branch.name}</h3><p className="break-words text-sm text-platforma-subtle">{[branch.city, branch.address].filter(Boolean).join(", ") || t("management.notSpecified")}</p><p className="text-sm">{branch.phone || t("management.noPhone")}</p><p className="text-xs text-platforma-subtle">{t(branch.archived_at ? "management.archived" : branch.is_active ? "management.active" : "management.inactive")}</p></div>
      <EntityActions business={business} kind="branches" id={branch.id} name={branch.name} active={branch.is_active} archived={!!branch.archived_at} canManage={branch.can_manage} canDelete={data.can_delete} edit={edit} />
    </div>
    <div className="grid min-w-0 gap-7 xl:grid-cols-2">
      <section className="min-w-0 space-y-3"><h4 className="text-sm font-semibold">{t("branches.openingHours")}</h4><p className="text-xs text-platforma-subtle">{data.timezone}</p>
        {config.isPending ? <LoadingState /> : config.error ? <ErrorState error={config.error} action={<Button onClick={() => void config.refetch()}>{t("common.retry")}</Button>} /> : config.data && <dl className="divide-y divide-platforma-border">{days.map((date, index) => {
          const cell = scheduleCell({ automatic: !!branch.uses_business_defaults, config: config.data!, hours: [], exceptions: [], resource: null, date });
          return <div key={date} className="flex justify-between gap-3 py-2 text-sm"><dt>{t(weekdayKeys[index])}</dt><dd className="text-right tabular-nums">{cell.intervals.map(row => `${row.start}–${row.end}`).join(", ") || t(cell.configured ? "workingHours.dayOff" : "branches.scheduleMissing")}</dd></div>;
        })}</dl>}
        <Link className="platforma-focus-ring inline-flex min-h-11 items-center text-sm text-brand-700 underline" to={`/app/business/working-hours?branch=${branch.id}&view=opening`}>{t("management.editSchedule")}</Link>
      </section>
      <div className="min-w-0 space-y-6">{([{ kind: "services", title: "nav.services", rows: services }, { kind: "staff", title: "management.specialists", rows: staff }, { kind: "rooms", title: "management.rooms", rows: rooms }] as const).map(group => <section key={group.kind} className="min-w-0 space-y-2"><h4 className="text-sm font-semibold">{t(group.title)}</h4>
        {group.rows.length ? <div className="flex flex-wrap gap-x-4 gap-y-1">{group.rows.map(row => <button key={row.id} disabled={!row.can_manage} type="button" className="platforma-focus-ring min-h-11 break-words text-left text-sm text-brand-700 underline" onClick={() => openEntity(group.kind, row.id)}>{row.name}</button>)}</div> : <p className="text-sm text-platforma-subtle">{t("management.notAssigned")}</p>}
      </section>)}</div>
    </div>
  </article>;
}
