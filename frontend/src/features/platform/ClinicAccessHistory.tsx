import { useAuth } from "../auth/AuthProvider";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { Link } from "react-router";
import { platformClinicApi } from "../../api/platformClinic";
import { Button } from "../../components/ui/Button";
import { Card, CardHeader } from "../../components/ui/Card";
import { EmptyState, LoadingState } from "../../components/ui/StateViews";
import { useI18n } from "../../lib/i18n";
import { SupportError, retainSupportData, supportDate } from "../support/SupportUI";
import { ClinicPager, useClinicReadDenial } from "./ClinicReadUI";
import { businessDetailsFields } from "./BusinessDetailsForm";

const administrativeResourceLabels: Record<string, string> = {
  ownership: "clinicCrm.tab.ownership",
  account_recovery: "clinicCrm.tab.recovery",
  employee_access: "clinicCrm.tab.employees",
  billing_orders: "clinicCrm.tab.billing",
};

export function ClinicAccessHistory({ business, timezone, onDenied }: { business: string; timezone: string; onDenied: (error: unknown) => void }) {
  const { t, language } = useI18n();
  const { user } = useAuth();
  const [page, setPage] = useState(1);
  const list = useQuery({ queryKey: ["platform-clinic-access", business, page], queryFn: () => platformClinicApi.access(business, page), gcTime: 0, retry: false });
  useClinicReadDenial(list.error, onDenied);
  return <Card data-testid="clinic-access-history">
    <CardHeader><div className="flex flex-wrap items-center justify-between gap-3"><h2 className="font-semibold">{t("clinicCrm.accessHistory")}</h2><Button variant="secondary" onClick={() => list.refetch()} isLoading={list.isFetching}>{t("common.refresh")}</Button></div></CardHeader>
    {user && <p className="break-words border-b border-platforma-border px-4 pb-3 text-sm text-platforma-subtle">{user.full_name || user.email} · {user.role === "platform_admin" || user.role === "platform_manager" ? t(`clinicCrm.value.${user.role}`) : t("platform.title")}</p>}
    {list.isError && <SupportError error={list.error} retry={() => list.refetch()} />}
    {list.isPending ? <LoadingState /> : list.isError && (!list.data || !retainSupportData(list.error)) ? null : list.data && <>
      {!list.data.results.length ? <EmptyState title={t("clinicCrm.empty")} /> : <ul className="divide-y divide-platforma-border">{list.data.results.map(item => {
        const [kind, section] = item.resource.split("/");
        return <li className="flex flex-wrap justify-between gap-2 p-4 text-sm" key={item.id}><div className="min-w-0 break-words"><p className="font-medium">{item.actor || t("platform.common.noName")}</p><p className="mt-1 text-platforma-subtle">{kind === "access_log" ? t("clinicCrm.accessHistory") : t(administrativeResourceLabels[kind] || `clinicCrm.kind.${kind}`)}{section && ` · ${t(`clinicCrm.section.${section}`)}`}{item.record_id && ` · #${item.record_id}`}</p>{item.correction && <div className="mt-2 space-y-1"><p>{t("businessDetails.corrected")}: {item.correction.changed_fields.map(field => { const label = businessDetailsFields.find(item => item.key === field)?.label; return label ? (label.includes(".") ? t(label) : label) : field; }).join(", ")}</p><p>{item.correction.reason}</p><Link to={`/platform/support/${item.correction.support_case_id}`} className="platforma-focus-ring inline-flex min-h-10 items-center text-brand-700">{t("businessDetails.caseId")} #{item.correction.support_case_id}</Link></div>}</div><time className="text-xs text-platforma-faint" dateTime={item.created_at}>{supportDate(item.created_at, language, timezone)}</time></li>;
      })}</ul>}
      <ClinicPager page={page} count={list.data.count} change={setPage} />
    </>}
  </Card>;
}
