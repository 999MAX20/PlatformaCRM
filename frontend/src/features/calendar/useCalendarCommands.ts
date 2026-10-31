import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useRef } from "react";
import { refreshAppointmentQueries } from "../../lib/appointmentCache";
import {
  appointmentsApi,
  type AppointmentCreatePayload,
} from "../../api/appointments";

import { useActionFeedback } from "../../components/actions/useActionFeedback";

import { dateInTimeZone } from "../../lib/format";
import { useI18n } from "../../lib/i18n";

import { useActiveBusiness } from "../../hooks/useBusiness";

import type { Appointment } from "../../types";

import type { Dispatch, SetStateAction } from "react";
type Args = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  setBookingOpen: Dispatch<SetStateAction<boolean>>;
  setDate: Dispatch<SetStateAction<string>>;
  setSelectedAppointmentId: Dispatch<SetStateAction<number | null>>;
  setInspectorOpen: Dispatch<SetStateAction<boolean>>;
  setStatusReasonTarget: Dispatch<
    SetStateAction<{
      appointment: Appointment;
      status: Appointment["status"];
    } | null>
  >;
  setStatusReason: Dispatch<SetStateAction<string>>;
  setRescheduleTarget: Dispatch<SetStateAction<Appointment | null>>;
  setArchiveTarget: Dispatch<SetStateAction<Appointment | null>>;
  setArchiveReason: Dispatch<SetStateAction<string>>;
  setNotice: (
    message: string | null,
    tone?: "success" | "info" | "warning" | "danger",
  ) => void;
  notifyError: ReturnType<typeof useActionFeedback>["notifyError"];
  t: ReturnType<typeof useI18n>["t"];
};
export function useCalendarCommands({
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
}: Args) {
  const queryClient = useQueryClient();
  const createAttempt = useRef<{ payload: string; key: string } | null>(null);
  function refreshAppointmentData(appointment?: Appointment) {
    return refreshAppointmentQueries(queryClient, appointment);
  }
  const mutation = useMutation({
    mutationFn: (payload: AppointmentCreatePayload) => {
      const fingerprint = JSON.stringify(payload);
      if (createAttempt.current?.payload !== fingerprint)
        createAttempt.current = { payload: fingerprint, key: crypto.randomUUID() };
      return appointmentsApi.createRecord(payload, createAttempt.current.key);
    },
    onSuccess: (appointment) => {
      createAttempt.current = null;
      setBookingOpen(false);
      if ("read_restricted" in appointment) {
        void refreshAppointmentData();
        setNotice(t("common.saved"));
        return;
      }
      void refreshAppointmentData(appointment);
      if (appointment.start_at)
        setDate(
          dateInTimeZone(
            appointment.start_at,
            business?.timezone || "Asia/Almaty",
          ),
        );
      setSelectedAppointmentId(appointment.id);
      setInspectorOpen(true);
      setNotice(t("calendar.createdNotice"));
    },
    onError: (error) => notifyError(error),
  });
  const statusMutation = useMutation({
    mutationFn: ({
      id,
      status,
      reason,
      expected_updated_at,
    }: {
      id: number;
      status: Appointment["status"];
      reason?: string;
      expected_updated_at: string;
    }) => {
      if (status === "confirmed") return appointmentsApi.confirm(id, expected_updated_at);
      if (status === "cancelled")
        return appointmentsApi.cancel(id, { reason: reason || "", expected_updated_at });
      if (status === "completed") return appointmentsApi.complete(id, expected_updated_at);
      if (status === "no_show")
        return appointmentsApi.noShow(id, { reason: reason || "", expected_updated_at });
      return appointmentsApi.get(id);
    },
    onSuccess: (appointment) => {
      refreshAppointmentData(appointment);
      setStatusReasonTarget(null);
      setStatusReason("");
      setNotice(t("appointments.actionDone"));
    },
    onError: (error) => notifyError(error, { actionLabel: t("common.refresh"), retry: () => {
      setStatusReasonTarget(null);
      return refreshAppointmentData();
    } }),
  });
  const rescheduleMutation = useMutation({
    mutationFn: appointmentsApi.reschedule,
    onSuccess: (appointment) => {
      refreshAppointmentData(appointment);
      setDate(
        dateInTimeZone(
          appointment.start_at,
          business?.timezone || "Asia/Almaty",
        ),
      );
      setSelectedAppointmentId(appointment.id);
      setInspectorOpen(true);
      setRescheduleTarget(null);
      setNotice(t("appointments.rescheduledNotice"));
    },
    onError: (error) =>
      notifyError(error, {
        actionLabel: t("common.refresh"),
        retry: () => { setRescheduleTarget(null); return refreshAppointmentData(); },
      }),
  });
  const archiveMutation = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      appointmentsApi.archive({ id, reason }),
    onSuccess: (appointment) => {
      refreshAppointmentData(appointment);
      setArchiveTarget(null);
      setArchiveReason("");
      setSelectedAppointmentId(null);
      setNotice(t("appointments.archive"));
    },
    onError: (error) => notifyError(error),
  });
  return {
    queryClient,
    refreshAppointmentData,
    mutation,
    statusMutation,
    rescheduleMutation,
    archiveMutation,
  };
}
