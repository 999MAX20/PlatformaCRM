import { CalendarArchiveDialog } from "./CalendarArchiveDialog";
import { CalendarStatusDialog } from "./CalendarStatusDialog";
import { CalendarRescheduleDialog } from "./CalendarRescheduleDialog";
import { CalendarBookingDialog } from "./CalendarBookingDialog";
import { useCalendarUrlState } from "./useCalendarUrlState";
import { useCalendarQueries } from "./useCalendarQueries";
import { useCalendarCommands } from "./useCalendarCommands";
import { Plus } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router";

import { getApiErrorMessage } from "../../api/client";

import { branchIntervals } from "./branchHours";

import { useActionFeedback } from "../../components/actions/useActionFeedback";

import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { useNotification } from "../../components/notifications/NotificationProvider";
import { Button } from "../../components/ui/Button";
import { CrmEntityDrawer } from "../../components/crm/CrmEntityDrawer";

import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { PageLoadPending } from "../../components/ui/PageLoadingBoundary";
import { dateInTimeZone, todayInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useCalendarCatalog } from "./useCalendarCatalog";

import { useClientCreateIntent } from "../../hooks/useClientCreateIntent";
import type { Appointment, Client, Task } from "../../types";
import { localeByLanguage } from "./calendarConstants";

import {
  getWeekday,
  getWorkingHoursFor,
  shiftCalendarPeriod,
} from "./calendarUtils";
import { AppointmentDrawerPanel } from "./components/AppointmentDrawerPanel";
import { ParticipationEntry } from "../medical/ParticipationEntry";
import { CalendarBoard } from "./components/CalendarBoard";
import { CalendarDayInspector } from "./components/CalendarDayInspector";
import { CalendarToolbar } from "./components/CalendarToolbar";
import { CalendarYearBoard } from "./components/CalendarYearBoard";
import { useAuth } from "../auth/AuthProvider";
import { canAccessAppointmentAction } from "./appointmentAccess";

export function CalendarPage() {
  const { t, language } = useI18n();
  const navigate = useNavigate();
  const showNotification = useNotification();
  const { notifyError } = useActionFeedback();
  const { setPageHeader } = usePageHeader();
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const canCreateAppointment = hasPermission(
    user,
    business?.id,
    "appointments",
    "create",
  );
  const canManageWorkingHours = hasPermission(
    user,
    business?.id,
    "settings",
    "update",
  );
  const canViewTasks = hasPermission(user, business?.id, "tasks", "view");
  const canViewClients = hasPermission(user, business?.id, "clients", "view");
  const canViewLeads = hasPermission(user, business?.id, "leads", "view");
  const { clients, services, resources, leads, workingHours } =
    useCalendarCatalog(business?.id, user?.id, canViewClients, canViewLeads);

  const {
    searchParams,
    setSearchParams,
    updateCalendar,
    branchFilter,
    date,
    periodDate,
    setDate,
    viewMode,
    setViewMode,
    serviceFilter,
    resourceFilter,
    statusFilter,
    appointmentIdFromUrl,
    calendarRange,
    businessTimeZone,
  } = useCalendarUrlState({ business });

  const [bookingOpen, setBookingOpen] = useState(false);
  const [bookingPrefill, setBookingPrefill] = useState<{
    source_conversation?: number | null;
    branch?: number | null;
    client?: number | null;
    service?: number | null;
    resource?: number | null;
    lead?: number | null;
    date?: string;
    slot?: string;
    hour?: number;
    source?: Appointment["source"];
  } | null>(null);
  const openLinkedAppointment = useCallback((client: Client | null) => {
    const sourceConversation = Number(searchParams.get("conversation"));
    setBookingPrefill({ client: client?.id, source: "manual",
      source_conversation: Number.isSafeInteger(sourceConversation) && sourceConversation > 0 ? sourceConversation : undefined });
    setBookingOpen(true);
  }, [searchParams]);
  const createContext = useClientCreateIntent({
    businessId: business?.id,
    allowed: canCreateAppointment,
    onOpen: openLinkedAppointment,
  });

  const [selectedAppointmentId, setSelectedAppointmentId] = useState<
    number | null
  >(null);
  const [cardAppointmentId, setCardAppointmentId] = useState<number | null>(null);
  const [inspectorOpen, setInspectorOpen] = useState(() =>
    searchParams.has("day") || ["day", "list"].includes(searchParams.get("view") || ""),
  );
  const [rescheduleTarget, setRescheduleTarget] = useState<Appointment | null>(
    null,
  );
  const [statusReasonTarget, setStatusReasonTarget] = useState<{
    appointment: Appointment;
    status: Appointment["status"];
  } | null>(null);
  const [statusReason, setStatusReason] = useState("");
  const [archiveTarget, setArchiveTarget] = useState<Appointment | null>(null);
  const [archiveReason, setArchiveReason] = useState("");

  const {
    branchesQuery,
    hasBranches,
    scheduleBranch,
    branchCatalog,
    tasks,
    appointments,
    yearSummary,
    outsideDay,
    inspectorAppointments,
    inspectorTasks,
    deepLinkedAppointment,
    dayAvailableSlots,
    dateExceptions,
  } = useCalendarQueries({
    business,
    userId: user?.id,
    canViewTasks,
    calendarRange,
    viewMode,
    inspectorOpen,
    businessTimeZone,
    branchFilter,
    serviceFilter,
    resourceFilter,
    statusFilter,
    date,
    appointmentIdFromUrl,
  });
  const previousBusiness = useRef(business?.id);
  useEffect(() => {
    if (previousBusiness.current !== business?.id) {
      setInspectorOpen(false);
      setSelectedAppointmentId(null);
      setBookingOpen(false);
      setRescheduleTarget(null);
      setStatusReasonTarget(null);
      setArchiveTarget(null);
      setSearchParams(
        (current) => {
          const next = new URLSearchParams(current);
          for (const key of [
            "branch",
            "appointment",
            "service",
            "resource",
            "status",
            "search",
            "day",
          ])
            next.delete(key);
          return next;
        },
        { replace: true },
      );
    }
    previousBusiness.current = business?.id;
  }, [business?.id, setSearchParams]);

  useEffect(() => {
    const appointment = deepLinkedAppointment.data;
    if (!appointment || appointment.business !== business?.id) return;
    setDate(
      dateInTimeZone(appointment.start_at, business?.timezone || "Asia/Almaty"),
    );
    setSelectedAppointmentId(appointment.id);
    setInspectorOpen(false); setCardAppointmentId(appointment.id);
  }, [business?.id, business?.timezone, deepLinkedAppointment.data, user?.id]);

  function setNotice(
    message: string | null,
    tone: "success" | "info" | "warning" | "danger" = "success",
  ) {
    if (!message) return;
    showNotification({ message, tone });
  }

  const { mutation, statusMutation, rescheduleMutation, archiveMutation } =
    useCalendarCommands({
      business,
      setBookingOpen,
      setDate,
      setSelectedAppointmentId,
      setInspectorOpen,
      setStatusReasonTarget,
      setStatusReason,
      setRescheduleTarget,
      setArchiveTarget,
      setArchiveReason,
      setNotice,
      notifyError,
      t,
    });

  useEffect(() => {
    setPageHeader({
      title: t("nav.calendar"),
      primaryAction: canCreateAppointment
        ? {
            label: t("calendar.newBooking"),
            icon: Plus,
            onClick: () => openBookingForDate(date),
          }
        : undefined,
    });
    return () => setPageHeader(null);
  }, [canCreateAppointment, date, setPageHeader, t]);

  if (!business) return <ErrorState message={t("calendar.noBusiness")} />;
  if (createContext.error) return <ErrorState message={createContext.error} />;
  if (createContext.isLoading) return <LoadingState scope="page" />;

  const appointmentItems = [...new Map([...(appointments.data || []), ...(outsideDay ? inspectorAppointments.data || [] : [])].map(item => [item.id, item])).values()];
  const clientItems = createContext.includeClient(clients.data || []);
  const serviceItems = services.data || [];
  const resourceItems = resources.data || [];
  const leadItems = leads.data || [];
  const workingHourItems = workingHours.data || [];
  const taskItems = [...new Map([...(tasks.data || []), ...(outsideDay ? inspectorTasks.data || [] : [])].map(item => [item.id, item])).values()] as Task[];
  const detailsEnabled = viewMode !== "year" || inspectorOpen || !!appointmentIdFromUrl;
  const locale = localeByLanguage[language];
  const todayValue = todayInTimeZone(businessTimeZone);
  const toolbar = <CalendarToolbar key={business.id} date={periodDate} viewMode={viewMode} locale={locale} todayValue={todayValue}
    filters={{ service: serviceFilter, resource: resourceFilter, status: statusFilter, branch: branchFilter }}
    serviceOptions={serviceItems.map(item => ({ value: String(item.id), label: item.name }))}
    resourceOptions={resourceItems.filter(item => item.resource_type === "staff").map(item => ({ value: String(item.id), label: item.name }))}
    branchOptions={(branchesQuery.data || []).map(item => ({ value: String(item.id), label: item.name }))}
    isServicesLoading={services.isLoading} isResourcesLoading={resources.isLoading}
    onDateChange={next => { setInspectorOpen(false); setSelectedAppointmentId(null); updateCalendar({ date: next, appointment: "" }); }}
    onViewModeChange={next => { setInspectorOpen(false); setSelectedAppointmentId(null); setViewMode(next); }}
    onShiftDate={direction => { setInspectorOpen(false); setSelectedAppointmentId(null); updateCalendar({ date: shiftCalendarPeriod(periodDate, direction, viewMode), appointment: "" }); }}
    onApplyFilters={filters => { setSelectedAppointmentId(null); updateCalendar({ ...filters, appointment: "" }); }} t={t} />;
  const isCalendarDataLoading =
    branchesQuery.isLoading ||
    branchCatalog.isLoading ||
    (detailsEnabled && appointments.isLoading) ||
    (viewMode === "year" && yearSummary.isLoading) ||
    clients.isLoading ||
    services.isLoading ||
    resources.isLoading ||
    leads.isLoading ||
    workingHours.isLoading ||
    (detailsEnabled && tasks.isLoading);
  const calendarDataError =
    branchesQuery.error ||
    branchCatalog.error ||
    (detailsEnabled && appointments.error) ||
    (viewMode === "year" && yearSummary.error) ||
    deepLinkedAppointment.error ||
    clients.error ||
    services.error ||
    resources.error ||
    leads.error ||
    workingHours.error ||
    (detailsEnabled && tasks.error);
  if (calendarDataError) {
    return (
      <>{toolbar}<div data-testid="calendar-error-state">
        <ErrorState
          error={calendarDataError}
          message={getApiErrorMessage(calendarDataError)}
          action={
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => {
                void Promise.all(
                  [
                    appointments,
                    yearSummary,
                    inspectorAppointments,
                    inspectorTasks,
                    deepLinkedAppointment,
                    branchesQuery,
                    branchCatalog,
                    clients,
                    services,
                    resources,
                    leads,
                    workingHours,
                    tasks,
                  ]
                    .filter((query) => query.isError)
                    .map((query) => query.refetch()),
                );
              }}
            >
              {t("common.retry")}
            </Button>
          }
        />
      </div></>
    );
  }
  const clientById = new Map(clientItems.map((client) => [client.id, client]));
  const serviceById = new Map(
    serviceItems.map((service) => [service.id, service]),
  );
  const resourceById = new Map(
    resourceItems.map((resource) => [resource.id, resource]),
  );
  const leadById = new Map(leadItems.map((lead) => [lead.id, lead]));

  const appointmentList = appointmentItems.filter((item) => {
    if (item.is_archived) return false;
    if (serviceFilter && item.service !== Number(serviceFilter)) return false;
    if (resourceFilter && item.resource !== Number(resourceFilter))
      return false;
    if (statusFilter && item.status !== statusFilter) return false;
    return true;
  });

  const dayAppointments = appointmentList
    .filter((item) => dateInTimeZone(item.start_at, businessTimeZone) === date)
    .sort(
      (a, b) => new Date(a.start_at).getTime() - new Date(b.start_at).getTime(),
    );
  const dayTasks = taskItems
    .filter(
      (task) =>
        !task.is_archived &&
        task.due_at &&
        dateInTimeZone(task.due_at, businessTimeZone) === date &&
        !["done", "cancelled"].includes(task.status),
    )
    .sort((a, b) => Date.parse(a.due_at!) - Date.parse(b.due_at!));
  const selectedAppointment =
    appointmentItems.find(
      (appointment) =>
        appointment.id === selectedAppointmentId && !appointment.is_archived,
    ) ||
    (deepLinkedAppointment.data?.id === selectedAppointmentId &&
    deepLinkedAppointment.data.business === business.id &&
    !deepLinkedAppointment.data.is_archived
      ? deepLinkedAppointment.data
      : null);
  const selectedResourceId = resourceFilter ? Number(resourceFilter) : null;
  const selectedDayHours = dateExceptions.data?.[0]
    ? { ...dateExceptions.data[0], weekday: getWeekday(date) }
    : getWorkingHoursFor(
        workingHourItems,
        getWeekday(date),
        selectedResourceId,
      );
  const branchDayLabel = scheduleBranch
    ? branchIntervals(branchCatalog.data, date, selectedResourceId)
        .map((item) => `${item.start}–${item.end}`)
        .join(", ") || t("calendar.freeDay")
    : "";
  const hoursLabel = hasBranches
    ? branchDayLabel
    : selectedDayHours && !selectedDayHours.is_day_off
      ? `${selectedDayHours.start_time.slice(0, 5)}–${selectedDayHours.end_time.slice(0, 5)}`
      : t("calendar.freeDay");
  const availableSlots =
    serviceFilter && resourceFilter && !dayAvailableSlots.isError
      ? dayAvailableSlots.data?.length
      : undefined;


  function selectAppointment(appointment: Appointment) {
    openAppointmentWorkspace(appointment);
  }

  function openAppointmentWorkspace(appointment: Appointment) {
    setInspectorOpen(false);
    setCardAppointmentId(appointment.id);
  }

  function closeAppointmentWorkspace() {
    setCardAppointmentId(null);
    const day = selectedAppointment ? dateInTimeZone(selectedAppointment.start_at, businessTimeZone) : date;
    requestAnimationFrame(() => document.querySelector<HTMLButtonElement>(`[data-calendar-day="${day}"]`)?.focus());
  }

  function selectMonthDay(nextDate: string) {
    updateCalendar({ day: nextDate, appointment: "" });
    setSelectedAppointmentId(null);
    setInspectorOpen(true);
  }

  function clearDeepLink() {
    setSearchParams(
      (current) => {
        const next = new URLSearchParams(current);
        next.delete("appointment");
        return next;
      },
      { replace: true },
    );
  }

  function closeInspector() {
    setInspectorOpen(false);
    setSelectedAppointmentId(null);
    setSearchParams(current => {
      const next = new URLSearchParams(current);
      next.delete("day");
      next.delete("appointment");
      return next;
    }, { replace: true });
    requestAnimationFrame(() =>
      document
        .querySelector<HTMLButtonElement>(`[data-calendar-day="${date}"]`)
        ?.focus(),
    );
  }

  function openBookingForDate(
    nextDate = date,
    hour?: number,
    resource?: number | null,
  ) {
    if (!canCreateAppointment) return;
    setBookingPrefill({
      date: nextDate,
      hour,
      service: serviceFilter ? Number(serviceFilter) : undefined,
      resource:
        resource ?? (resourceFilter ? Number(resourceFilter) : undefined),
    });
    setBookingOpen(true);
  }

  function getAppointmentActionLabel(status: Appointment["status"]) {
    if (status === "confirmed") return t("appointment.actionConfirm");
    if (status === "completed") return t("appointment.actionComplete");
    if (status === "cancelled") return t("appointment.actionCancel");
    if (status === "no_show") return t("appointment.actionNoShow");
    return t(`status.${status}`);
  }

  function getAllowedStatusActions(appointment: Appointment) {
    if (
      !canAccessAppointmentAction({
        appointment,
        resources: resourceItems,
        branches: branchesQuery.data,
        user,
        businessId: business?.id,
      })
    )
      return [] as Appointment["status"][];
    if (
      appointment.status === "created" ||
      appointment.status === "rescheduled"
    )
      return ["confirmed", "completed", "cancelled", "no_show"] as Appointment["status"][];
    if (appointment.status === "confirmed")
      return ["completed", "cancelled", "no_show"] as Appointment["status"][];
    return [] as Appointment["status"][];
  }

  function canRescheduleAppointment(appointment: Appointment) {
    return (
      canAccessAppointmentAction({
        appointment,
        resources: resourceItems,
        branches: branchesQuery.data,
        user,
        businessId: business?.id,
      }) && !["completed", "cancelled", "no_show"].includes(appointment.status)
    );
  }

  function canArchiveAppointment(appointment: Appointment) {
    return canAccessAppointmentAction({
      appointment,
      resources: resourceItems,
      branches: branchesQuery.data,
      user,
      businessId: business?.id,
      action: "delete",
    });
  }

  function openRepeatBooking(appointment: Appointment) {
    setBookingPrefill({
      date: todayInTimeZone(businessTimeZone),
      source_conversation: appointment.source_conversation,
      branch: appointment.branch || undefined,
      client: appointment.client,
      service: appointment.service,
      resource: appointment.resource || undefined,
      lead: appointment.lead || undefined,
      source: "manual",
    });
    setBookingOpen(true);
  }

  function shouldShowRepeatBooking(appointment: Appointment) {
    return (
      canCreateAppointment &&
      ["completed", "cancelled", "no_show"].includes(appointment.status)
    );
  }

  return (
    <>
      {toolbar}
      <PageLoadPending pending={isCalendarDataLoading} />
      {business && user?.capabilities?.[String(business.id)]?.modules?.medical_records === true ?
        <details className="mb-3 text-sm"><summary className="platforma-focus-ring flex min-h-11 cursor-pointer items-center text-platforma-subtle">{t("medical.participation.title")}</summary>
          <ParticipationEntry key={`${business.id}:${user.id}`} businessId={business.id} />
        </details> : null}
      <section
        data-testid={
          isCalendarDataLoading ? undefined : "calendar-workspace-ready"
        }
      >
        {viewMode === "year" ? <CalendarYearBoard date={date} periodDate={periodDate} today={todayValue} locale={locale}
          loading={yearSummary.isLoading} days={yearSummary.data?.days || []}
          onSelectDay={selectMonthDay} onNavigate={setDate}
          onOpenMonth={next => { setInspectorOpen(false); setSelectedAppointmentId(null); updateCalendar({ date: next, view: "month", appointment: "" }); }} t={t} /> : <CalendarBoard
          loading={isCalendarDataLoading}
          canViewTasks={canViewTasks}
          date={date}
          periodDate={periodDate}
          viewMode={viewMode}
          today={todayValue}
          locale={locale}
          timeZone={businessTimeZone}
          appointments={appointmentList}
          tasks={canViewTasks ? taskItems : []}
          onSelectDay={selectMonthDay}
          onNavigate={setDate}
          t={t}
        />}
      </section>
      <CalendarDayInspector
        open={inspectorOpen && !cardAppointmentId}
        loading={isCalendarDataLoading || (outsideDay && (inspectorAppointments.isLoading || (canViewTasks && inspectorTasks.isLoading)))}
        error={outsideDay ? inspectorAppointments.error || inspectorTasks.error : undefined}
        onRetry={() => { void inspectorAppointments.refetch(); if (canViewTasks) void inspectorTasks.refetch(); }}
        canViewTasks={canViewTasks}
        date={date}
        locale={locale}
        timeZone={businessTimeZone}
        dayAppointments={dayAppointments}
        dayTasks={canViewTasks ? dayTasks : []}
        clientById={clientById}
        serviceById={serviceById}
        resourceById={resourceById}
        selectedAppointmentId={selectedAppointment?.id || null}
        canCreate={canCreateAppointment}
        hoursLabel={hoursLabel}
        branchId={scheduleBranch}
        branches={branchesQuery.data || []}
        onBranchChange={value => { setSelectedAppointmentId(null); updateCalendar({ branch: value, appointment: "" }); }}
        availableSlots={availableSlots}
        hoursUrl={
          canManageWorkingHours
            ? hasBranches
              ? `/app/business/branches?branch=${scheduleBranch}&section=schedule`
              : "/app/business/working-hours"
            : undefined
        }
        onClose={closeInspector}
        onBack={() => {
          setSelectedAppointmentId(null);
          clearDeepLink();
        }}
        onDayChange={selectMonthDay}
        onBooking={openBookingForDate}
        onSelectAppointment={selectAppointment}
        onOpenCard={openAppointmentWorkspace}
        t={t}
      >
        {selectedAppointment ? (
          <><AppointmentDrawerPanel
            appointment={selectedAppointment}
            clientById={clientById}
            serviceById={serviceById}
            resourceById={resourceById}
            leadById={leadById}
            locale={locale}
            businessTimeZone={businessTimeZone}
            statusMutationPending={statusMutation.isPending}
            getAppointmentActionLabel={getAppointmentActionLabel}
            getAllowedStatusActions={getAllowedStatusActions}
            canRescheduleAppointment={canRescheduleAppointment}
            shouldShowRepeatBooking={shouldShowRepeatBooking}
            canArchiveAppointment={canArchiveAppointment}
            onRepeatBooking={openRepeatBooking}
            onStatusAction={(appointment, status) => {
              if (status === "cancelled" || status === "no_show" || (status === "completed" && Date.now() < new Date(appointment.end_at).getTime())) {
                setStatusReasonTarget({ appointment, status });
                setStatusReason("");
                return;
              }
              statusMutation.mutate({ id: appointment.id, status, expected_updated_at: appointment.updated_at });
            }}
            onReschedule={setRescheduleTarget}
            onOpenCard={openAppointmentWorkspace}
            onArchive={setArchiveTarget}
            t={t}
          />
          </>
        ) : null}
      </CalendarDayInspector>
      <CrmEntityDrawer entity={cardAppointmentId ? { type: "appointment", id: cardAppointmentId } : null} onClose={closeAppointmentWorkspace} />

      <CalendarBookingDialog
        t={t}
        bookingOpen={bookingOpen}
        setBookingOpen={setBookingOpen}
        setBookingPrefill={setBookingPrefill}
        business={business}
        clientItems={clientItems}
        serviceItems={serviceItems}
        resourceItems={resourceItems}
        leadItems={leadItems}
        bookingPrefill={bookingPrefill}
        date={date}
        branchFilter={branchFilter}
        mutation={mutation}
        businessTimeZone={businessTimeZone}
      />
      <CalendarRescheduleDialog
        t={t}
        rescheduleTarget={rescheduleTarget}
        setRescheduleTarget={setRescheduleTarget}
        business={business}
        resourceItems={resourceItems}
        rescheduleMutation={rescheduleMutation}
        businessTimeZone={businessTimeZone}
      />
      <CalendarStatusDialog
        t={t}
        statusReasonTarget={statusReasonTarget}
        setStatusReasonTarget={setStatusReasonTarget}
        setStatusReason={setStatusReason}
        statusReason={statusReason}
        statusMutation={statusMutation}
        getAppointmentActionLabel={getAppointmentActionLabel}
      />
      <CalendarArchiveDialog
        t={t}
        archiveTarget={archiveTarget}
        setArchiveTarget={setArchiveTarget}
        setArchiveReason={setArchiveReason}
        archiveReason={archiveReason}
        archiveMutation={archiveMutation}
      />
    </>
  );
}
