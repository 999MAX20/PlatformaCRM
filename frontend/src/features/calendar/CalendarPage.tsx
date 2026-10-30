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

import { Select } from "../../components/ui/Select";
import { branchIntervals } from "./branchHours";

import { useActionFeedback } from "../../components/actions/useActionFeedback";

import { usePageHeader } from "../../components/layout/PageHeaderContext";
import { useNotification } from "../../components/notifications/NotificationProvider";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";

import { ErrorState, LoadingState } from "../../components/ui/StateViews";
import { dateInTimeZone, todayInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";
import { hasPermission } from "../../lib/permissions";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useCalendarCatalog } from "./useCalendarCatalog";

import { useClientCreateIntent } from "../../hooks/useClientCreateIntent";
import type { Appointment, Client, Task } from "../../types";
import { localeByLanguage } from "./calendarConstants";

import {
  formatTimeZoneLabel,
  getWeekday,
  getWorkingHoursFor,
  shiftCalendarPeriod,
} from "./calendarUtils";
import { AppointmentDrawerPanel } from "./components/AppointmentDrawerPanel";
import { CalendarBoard } from "./components/CalendarBoard";
import { CalendarDayInspector } from "./components/CalendarDayInspector";
import {
  ActiveCalendarFilters,
  type ActiveCalendarFilterChip,
} from "./components/CalendarFilters";
import { CalendarToolbar } from "./components/CalendarToolbar";
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
    branchFilter,
    date,
    setDate,
    viewMode,
    setViewMode,
    serviceFilter,
    setServiceFilter,
    resourceFilter,
    setResourceFilter,
    statusFilter,
    setStatusFilter,
    search,
    setSearch,
    appointmentIdFromUrl,
    calendarRange,
    businessTimeZone,
  } = useCalendarUrlState({ business });

  const [bookingOpen, setBookingOpen] = useState(false);
  const [bookingPrefill, setBookingPrefill] = useState<{
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
    setBookingPrefill({ client: client?.id, source: "manual" });
    setBookingOpen(true);
  }, []);
  const createContext = useClientCreateIntent({
    businessId: business?.id,
    allowed: canCreateAppointment,
    onOpen: openLinkedAppointment,
  });

  const [selectedAppointmentId, setSelectedAppointmentId] = useState<
    number | null
  >(null);
  const [inspectorOpen, setInspectorOpen] = useState(() =>
    ["day", "list"].includes(searchParams.get("view") || ""),
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
    branchCatalog,
    tasks,
    appointments,
    deepLinkedAppointment,
    dayAvailableSlots,
    dateExceptions,
  } = useCalendarQueries({
    business,
    userId: user?.id,
    canViewTasks,
    calendarRange,
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
      setServiceFilter("");
      setResourceFilter("");
      setStatusFilter("");
      setSearch("");
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
    setInspectorOpen(true);
  }, [business?.id, business?.timezone, deepLinkedAppointment.data]);

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

  const appointmentItems = appointments.data || [];
  const clientItems = createContext.includeClient(clients.data || []);
  const serviceItems = services.data || [];
  const resourceItems = resources.data || [];
  const leadItems = leads.data || [];
  const workingHourItems = workingHours.data || [];
  const taskItems = (tasks.data || []) as Task[];
  const isCalendarDataLoading =
    branchesQuery.isLoading ||
    branchCatalog.isLoading ||
    appointments.isLoading ||
    clients.isLoading ||
    services.isLoading ||
    resources.isLoading ||
    leads.isLoading ||
    workingHours.isLoading ||
    tasks.isLoading;
  const calendarDataError =
    branchesQuery.error ||
    branchCatalog.error ||
    appointments.error ||
    deepLinkedAppointment.error ||
    clients.error ||
    services.error ||
    resources.error ||
    leads.error ||
    workingHours.error ||
    tasks.error;
  if (calendarDataError) {
    return (
      <div data-testid="calendar-error-state">
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
      </div>
    );
  }
  const locale = localeByLanguage[language];
  const todayValue = todayInTimeZone(businessTimeZone);
  const clientById = new Map(clientItems.map((client) => [client.id, client]));
  const serviceById = new Map(
    serviceItems.map((service) => [service.id, service]),
  );
  const resourceById = new Map(
    resourceItems.map((resource) => [resource.id, resource]),
  );
  const leadById = new Map(leadItems.map((lead) => [lead.id, lead]));

  const appointmentList = appointmentItems.filter((item) => {
    const client = clientById.get(item.client);
    const service = serviceById.get(item.service);
    const resource = item.resource ? resourceById.get(item.resource) : null;
    const query = search.trim().toLowerCase();
    if (item.is_archived) return false;
    if (serviceFilter && item.service !== Number(serviceFilter)) return false;
    if (resourceFilter && item.resource !== Number(resourceFilter))
      return false;
    if (statusFilter && item.status !== statusFilter) return false;
    if (!query) return true;
    return [
      client?.full_name || item.client_name,
      service?.name || item.service_name,
      resource?.name || item.resource_name,
      item.source,
      item.notes,
    ]
      .filter(Boolean)
      .some((value) => String(value).toLowerCase().includes(query));
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
  const branchDayLabel = branchFilter
    ? branchIntervals(branchCatalog.data, date, selectedResourceId)
        .map((item) => `${item.start}–${item.end}`)
        .join(", ") || t("calendar.freeDay")
    : t("branches.choose");
  const hoursLabel = hasBranches
    ? branchDayLabel
    : selectedDayHours && !selectedDayHours.is_day_off
      ? `${selectedDayHours.start_time.slice(0, 5)}–${selectedDayHours.end_time.slice(0, 5)}`
      : t("calendar.freeDay");
  const availableSlots =
    serviceFilter && resourceFilter && !dayAvailableSlots.isError
      ? dayAvailableSlots.data?.length
      : undefined;
  const timeZoneLabel = formatTimeZoneLabel(businessTimeZone);

  function shiftDate(days: number) {
    setDate(shiftCalendarPeriod(date, days, viewMode));
  }

  function selectAppointment(appointment: Appointment) {
    setSelectedAppointmentId(appointment.id);
    setInspectorOpen(true);
    setDate(dateInTimeZone(appointment.start_at, businessTimeZone));
  }

  function openAppointmentWorkspace(appointment: Appointment) {
    navigate(`/app/calendar/${appointment.id}`);
  }

  function selectMonthDay(nextDate: string) {
    setDate(nextDate);
    clearDeepLink();
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
    clearDeepLink();
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
      return ["confirmed", "cancelled"] as Appointment["status"][];
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
      date: dateInTimeZone(appointment.start_at, businessTimeZone),
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

  const serviceFilterOptions = serviceItems.map((service) => ({
    value: String(service.id),
    label: service.name,
  }));
  const resourceFilterOptions = resourceItems.map((resource) => ({
    value: String(resource.id),
    label: resource.name,
  }));
  const activeFilterChips = [
    serviceFilter
      ? {
          key: "service",
          label:
            serviceById.get(Number(serviceFilter))?.name ||
            t("calendar.allServices"),
          clear: () => setServiceFilter(""),
        }
      : null,
    resourceFilter
      ? {
          key: "resource",
          label:
            resourceById.get(Number(resourceFilter))?.name ||
            t("calendar.allResources"),
          clear: () => setResourceFilter(""),
        }
      : null,
    statusFilter
      ? {
          key: "status",
          label: t(`status.${statusFilter}`),
          clear: () => setStatusFilter(""),
        }
      : null,
    search.trim()
      ? { key: "search", label: search.trim(), clear: () => setSearch("") }
      : null,
  ].filter(Boolean) as ActiveCalendarFilterChip[];

  function clearAllFilters() {
    setServiceFilter("");
    setResourceFilter("");
    setStatusFilter("");
    setSearch("");
  }

  return (
    <>
      <CalendarToolbar
        date={date}
        viewMode={viewMode}
        locale={locale}
        todayValue={todayValue}
        serviceFilter={serviceFilter}
        resourceFilter={resourceFilter}
        statusFilter={statusFilter}
        serviceOptions={serviceFilterOptions}
        resourceOptions={resourceFilterOptions}
        isServicesLoading={services.isLoading}
        isResourcesLoading={resources.isLoading}
        onDateChange={setDate}
        onViewModeChange={setViewMode}
        onShiftDate={shiftDate}
        onServiceChange={setServiceFilter}
        onResourceChange={setResourceFilter}
        onStatusChange={setStatusFilter}
        t={t}
      >
        <div className="w-full min-w-0 sm:min-w-64 sm:flex-1">
          <Input
            aria-label={t("calendar.searchPlaceholder")}
            placeholder={t("calendar.searchPlaceholder")}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        </div>
        {hasBranches && (
          <div className="min-w-0 flex-1 sm:w-64 sm:flex-none">
            <Select
              aria-label={t("branches.branch")}
              value={branchFilter}
              onChange={(event) =>
                setSearchParams((current) => {
                  const next = new URLSearchParams(current);
                  if (event.target.value)
                    next.set("branch", event.target.value);
                  else next.delete("branch");
                  return next;
                })
              }
              options={[
                { value: "", label: t("branches.all") },
                ...(branchesQuery.data || []).map((branch) => ({
                  value: branch.id,
                  label: branch.name,
                })),
              ]}
            />
          </div>
        )}
      </CalendarToolbar>
      <p className="mb-2 text-right text-xs text-platforma-muted">
        {businessTimeZone} · {timeZoneLabel}
      </p>
      <ActiveCalendarFilters
        chips={activeFilterChips}
        onClearAll={clearAllFilters}
        t={t}
      />
      {isCalendarDataLoading && <LoadingState />}
      <section
        data-testid={
          isCalendarDataLoading ? undefined : "calendar-workspace-ready"
        }
      >
        <CalendarBoard
          loading={isCalendarDataLoading}
          canViewTasks={canViewTasks}
          date={date}
          viewMode={viewMode}
          today={todayValue}
          locale={locale}
          timeZone={businessTimeZone}
          appointments={appointmentList}
          tasks={canViewTasks ? taskItems : []}
          onSelectDay={selectMonthDay}
          onNavigate={setDate}
          t={t}
        />
      </section>
      <CalendarDayInspector
        open={inspectorOpen}
        loading={isCalendarDataLoading}
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
        availableSlots={availableSlots}
        hoursUrl={
          canManageWorkingHours
            ? hasBranches
              ? `/app/business/branches?branch=${branchFilter}&section=schedule`
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
          <AppointmentDrawerPanel
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
              if (status === "cancelled" || status === "no_show") {
                setStatusReasonTarget({ appointment, status });
                setStatusReason("");
                return;
              }
              statusMutation.mutate({ id: appointment.id, status });
            }}
            onReschedule={setRescheduleTarget}
            onOpenCard={openAppointmentWorkspace}
            onArchive={setArchiveTarget}
            t={t}
          />
        ) : null}
      </CalendarDayInspector>

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
