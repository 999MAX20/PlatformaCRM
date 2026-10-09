import { useState } from "react";
import { SettingsSection, SettingsTabs } from "../components/SettingsLayout";
import { SettingsQueryState } from "../components/SettingsQueryState";
import { auditEventTitle, loginStatusLabel, riskClass, riskLabel } from "../settingsUtils";
import type { SettingsModel } from "../useSettingsModel";

export function SecuritySection({ model }: { model: SettingsModel; }) {
  const { t, activeSettingsSection, securityRisk, auditLogs, loginHistory, supportGrants, locale, business } = model;
  const [tab, setTab] = useState<"audit" | "logins" | "support">("audit");
  const date = (value: string) => new Date(value).toLocaleString(locale, { timeZone: business?.timezone || undefined });
  const metrics = [
    { label: t("settings.highRisk"), value: securityRisk.data ? securityRisk.data.risk_counts.high + securityRisk.data.risk_counts.critical : undefined },
    { label: t("settings.failedLogins"), value: securityRisk.data?.failed_logins },
    { label: t("settings.support"), value: securityRisk.data?.active_support_grants },
  ];
  return <SettingsSection id="security-center" active={activeSettingsSection} title={t("settings.section.security-center")}>
    <div className="space-y-4 p-4 sm:p-5">
      <div className="grid gap-4 border-b border-platforma-border pb-5 sm:grid-cols-3">
        {metrics.map(metric => <div key={metric.label}><p className="text-xs text-platforma-subtle">{metric.label}</p><p className="mt-1 text-[22px] font-bold tabular-nums">{securityRisk.isLoading || securityRisk.isError ? "—" : metric.value?.toLocaleString(locale) ?? "—"}</p></div>)}
      </div>
      <SettingsQueryState queries={[securityRisk]} />
      <p className="text-xs leading-5 text-platforma-subtle">{t("settings.securityPeriod")}</p>
      <SettingsTabs value={tab} onChange={setTab} label={t("settings.section.security-center")} items={[
        { value: "audit", label: t("settings.redesign.auditTab") },
        { value: "logins", label: t("settings.redesign.loginsTab") },
        { value: "support", label: t("settings.redesign.supportTab") },
      ]} />
      {tab === "audit" && <>
        <SettingsQueryState queries={[auditLogs]} />
        {auditLogs.isSuccess && <div className="divide-y divide-platforma-border">
          {(auditLogs.data || []).map(log => <div key={log.id} className="flex items-start justify-between gap-3 py-4">
            <div className="min-w-0"><p className="text-sm font-semibold">{auditEventTitle(log.action, log.entity_type, t)} #{log.entity_id}</p><p className="mt-1 break-words text-xs text-platforma-subtle">{log.actor_email || t("settings.systemActor")} · {date(log.created_at)}</p></div>
            <span className={riskClass(log.risk_level)}>{riskLabel(log.risk_level, t)}</span>
          </div>)}
          {!auditLogs.data?.length && <p className="py-8 text-sm text-platforma-subtle">{t("settings.noAuditEvents")}</p>}
        </div>}
      </>}
      {tab === "logins" && <>
        <SettingsQueryState queries={[loginHistory]} />
        {loginHistory.isSuccess && <div className="divide-y divide-platforma-border">
          {(loginHistory.data || []).map(item => <div key={item.id} className="flex items-start justify-between gap-3 py-4">
            <div className="min-w-0"><p className="break-all text-sm font-semibold">{item.email || item.user_email}</p><p className="mt-1 text-xs text-platforma-subtle">{item.ip_address || t("settings.noIp")} · {date(item.created_at)}</p></div>
            <span className={"shrink-0 text-xs font-semibold " + (item.status === "success" ? "text-platforma-success" : "text-platforma-danger")}>{loginStatusLabel(item.status, t)}</span>
          </div>)}
          {!loginHistory.data?.length && <p className="py-8 text-sm text-platforma-subtle">{t("settings.noLoginHistory")}</p>}
        </div>}
      </>}
      {tab === "support" && <>
        <SettingsQueryState queries={[supportGrants]} />
        {supportGrants.isSuccess && <div className="divide-y divide-platforma-border">
          {(supportGrants.data || []).map(grant => <div key={grant.id} className="flex flex-wrap items-start justify-between gap-3 py-4">
            <div><p className="break-all text-sm font-semibold">{grant.user_email}</p><p className="mt-1 text-xs text-platforma-subtle">{t("settings.until")} {date(grant.expires_at)}</p></div>
            <span className="text-xs text-platforma-subtle">{t(grant.is_active ? new Date(grant.expires_at).getTime() > Date.now() ? "settings.active" : "settings.expired" : "settings.inactive")}</span>
          </div>)}
          {!supportGrants.data?.length && <p className="py-8 text-sm text-platforma-subtle">{t("settings.noSupportGrants")}</p>}
        </div>}
      </>}
    </div>
  </SettingsSection>;
}
