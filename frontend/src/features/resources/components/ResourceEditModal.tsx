import { CustomEntityFields } from "../../../components/crm/CustomEntityFields";
import { CalendarCheck2, CalendarClock } from "lucide-react";
import { useEffect, useState } from "react";

import { ResourceForm } from "../../../components/forms/ResourceForm";
import { Button } from "../../../components/ui/Button";
import { Modal } from "../../../components/ui/Modal";
import { ErrorState, SkeletonBlock } from "../../../components/ui/StateViews";
import { StatusNotice } from "../../../components/ui/StatusNotice";
import { useI18n } from "../../../lib/i18n";
import type { Id, Resource, TeamMember, WorkingHours } from "../../../types";
import { ResourceStatusBadge } from "./ResourceStatusBadge";
import { SpecialistLifecycle } from "./SpecialistLifecycle";
import { useQuery } from "@tanstack/react-query";
import { branchesApi } from "../../../api/branches";
import { Link, useSearchParams } from "react-router";
import { StaffAccounts } from "../../business/components/StaffAccounts";
import { StaffAssignments } from "../../business/components/StaffAssignments";

const FORM_ID = "resource-edit-form";
const weekdayKeys = [
  "weekday.monShort",
  "weekday.tueShort",
  "weekday.wedShort",
  "weekday.thuShort",
  "weekday.friShort",
  "weekday.satShort",
  "weekday.sunShort",
];

function compactTime(value: string) {
  return value.slice(0, 5);
}

export function ResourceEditModal({
  resource,
  businessId,
  teamMembers,
  workingHours,
  scheduleLoading,
  scheduleError,
  canManage,
  isSaving,
  error,
  onSubmit,
  onClose,
  onDirtyChange,
  onOpenSchedule,
}: {
  resource: Resource | null;
  businessId: Id;
  teamMembers: TeamMember[];
  workingHours: WorkingHours[];
  scheduleLoading: boolean;
  scheduleError?: string;
  canManage: boolean;
  isSaving: boolean;
  error?: unknown;
  onSubmit: (payload: Partial<Resource>) => Promise<unknown>;
  onClose: () => void;
  onDirtyChange: (isDirty: boolean) => void;
  onOpenSchedule: () => void;
}) {
  const { t } = useI18n();
  const [params] = useSearchParams();
  const branches = useQuery({ queryKey: ["branches", businessId], queryFn: () => branchesApi.listAll({ business: businessId }), enabled: !!resource });
  const [resetVersion, setResetVersion] = useState(0);
  const [isDirty, setIsDirty] = useState(false);
  const [fieldsDirty, setFieldsDirty] = useState(false);
  const [assignmentsDirty, setAssignmentsDirty] = useState(false);
  useEffect(() => { onDirtyChange(isDirty || fieldsDirty || assignmentsDirty); }, [isDirty, fieldsDirty, assignmentsDirty, onDirtyChange]);

  useEffect(() => {
    setResetVersion(0);
    setIsDirty(false);
    setFieldsDirty(false);
    setAssignmentsDirty(false);
  }, [onDirtyChange, resource?.id]);

  if (!resource) return null;

  function handleDirtyChange(nextDirty: boolean) {
    setIsDirty(nextDirty);

  }

  function resetForm() {
    setResetVersion((current) => current + 1);
    handleDirtyChange(false);
  }

  const scheduleByDay = new Map(workingHours.map((item) => [item.weekday, item]));

  return (
    <Modal
      title={resource.name}
      open
      onClose={() => { if (!isSaving) onClose(); }}
      size="xl"
      closeOnBackdrop={!isSaving}
      testId="resource-edit-modal"
      bodyClassName="p-0"
    >
      <div className="grid gap-4 p-4 sm:p-5 lg:grid-cols-[minmax(0,1fr)_minmax(360px,0.9fr)]">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2">
            <ResourceStatusBadge resource={resource} size="sm" />
            <p className="text-sm text-platforma-subtle">{t("resources.inspectorSubtitle")}</p>
          </div>
          {error ? <ErrorState error={error} /> : null}
          {!canManage ? (
            <StatusNotice tone="warning" title={t("resources.readOnlyTitle")} description={t("resources.readOnlyText")} />
          ) : null}
          <ResourceForm
            branches={branches.data}
            key={`${resource.id}:${resource.updated_at}:${resetVersion}`}
            formId={FORM_ID}
            businessId={businessId}
            initial={resource}
            physicalOnly={resource.resource_type !== "staff"}
            staffOnly={resource.resource_type === "staff"}
            teamMembers={teamMembers}
            disabled={!canManage || !!resource.retired_at}
            showContextHint={false}
            showSubmit={false}
            onDirtyChange={handleDirtyChange}
            onSubmit={onSubmit}
          />
          {resource.resource_type === "staff" && <>
            <CustomEntityFields business={businessId} kind="specialist" id={resource.id} readOnly={!canManage || !!resource.retired_at} onDirtyChange={setFieldsDirty} />
            <StaffAccounts businessId={businessId} linkedUser={resource.linked_user || null} />
            {branches.error ? <ErrorState error={branches.error} /> : <StaffAssignments resource={resource} branches={branches.data || []} onDirtyChange={setAssignmentsDirty} />}
          </>}
        </div>

        <div className="space-y-4">
          {resource.resource_type === "staff" && <SpecialistLifecycle resource={resource} canManage={canManage} />}
          <section className="rounded-card border border-platforma-border bg-surface-card p-4 shadow-xs">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-brand-50 text-brand-700">
                <CalendarCheck2 aria-hidden="true" size={19} />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-platforma-ink">{t("resources.usageTitle")}</h3>
                <p className="mt-1 text-sm leading-5 text-platforma-subtle">
                  {t("resources.usageText", { count: resource.appointment_count || 0 })}
                </p>
              </div>
            </div>
          </section>

          <section className="rounded-card border border-platforma-border bg-surface-card p-4 shadow-xs">
            <div className="flex items-start gap-3">
              <div className="grid h-10 w-10 shrink-0 place-items-center rounded-control bg-brand-50 text-brand-700">
                <CalendarClock aria-hidden="true" size={19} />
              </div>
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-semibold text-platforma-ink">{t("resources.scheduleTitle")}</h3>
                {branches.data?.length ? <Link className="mt-3 inline-flex text-sm font-semibold text-brand-700 underline" to={`/app/business/working-hours?resource=${resource.id}&view=${resource.resource_type === "staff" ? "staff" : "physical"}${resource.branch || params.get("branch") ? `&branch=${resource.branch || params.get("branch")}` : ""}`}>{t("branches.schedule")}</Link> : scheduleLoading ? (
                  <div className="mt-3 space-y-2" aria-busy="true">
                    <SkeletonBlock className="h-8" />
                    <SkeletonBlock className="h-8" />
                  </div>
                ) : scheduleError ? (
                  <div className="mt-3"><ErrorState message={scheduleError} /></div>
                ) : workingHours.length ? (
                  <div className="mt-3 grid grid-cols-7 overflow-hidden rounded-control border border-platforma-border">
                    {weekdayKeys.map((key, weekday) => {
                      const schedule = scheduleByDay.get(weekday);
                      return (
                        <div key={key} className="min-w-0 border-r border-platforma-border px-1.5 py-2 text-center last:border-r-0">
                          <p className="text-[10px] font-semibold text-platforma-faint">{t(key)}</p>
                          <p className="mt-1 text-[10px] font-semibold leading-3 text-platforma-text">
                            {!schedule || schedule.is_day_off ? t("workingHours.dayOff") : (
                              <><span className="block">{compactTime(schedule.start_time)}</span><span className="block">{compactTime(schedule.end_time)}</span></>
                            )}
                          </p>
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <p className="mt-2 text-sm leading-5 text-platforma-subtle">{t("workingHours.usesBusinessSchedule")}</p>
                )}
                <button
                  type="button"
                  onClick={onOpenSchedule}
                  hidden={!!branches.data?.length}
                  className="platforma-focus-ring mt-3 inline-flex rounded-control text-sm font-semibold text-brand-700 hover:text-brand-800"
                >
                  {t("resources.openSchedule")}
                </button>
              </div>
            </div>
          </section>
        </div>
      </div>

      <div className="sticky bottom-0 flex items-center justify-end gap-2 border-t border-platforma-border bg-surface-card px-4 py-3 sm:px-5">
        {canManage && !resource.retired_at ? (
          <>
            <Button type="button" variant="secondary" disabled={!isDirty || isSaving} onClick={resetForm}>{t("common.cancel")}</Button>
            <Button type="submit" form={FORM_ID} disabled={!isDirty} isLoading={isSaving}>{t("resources.save")}</Button>
          </>
        ) : (
          <Button type="button" variant="secondary" onClick={onClose}>{t("common.close")}</Button>
        )}
      </div>
    </Modal>
  );
}
