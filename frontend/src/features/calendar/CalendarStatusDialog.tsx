import { useCalendarCommands } from "./useCalendarCommands";

import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";

import { useI18n } from "../../lib/i18n";

import type { Appointment } from "../../types";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  t: ReturnType<typeof useI18n>["t"];
  statusReasonTarget: {
    appointment: Appointment;
    status:
      | "created"
      | "confirmed"
      | "cancelled"
      | "rescheduled"
      | "completed"
      | "no_show";
  } | null;
  setStatusReasonTarget: Dispatch<
    SetStateAction<{
      appointment: Appointment;
      status:
        | "created"
        | "confirmed"
        | "cancelled"
        | "rescheduled"
        | "completed"
        | "no_show";
    } | null>
  >;
  setStatusReason: Dispatch<SetStateAction<string>>;
  statusReason: string;
  statusMutation: ReturnType<typeof useCalendarCommands>["statusMutation"];
  getAppointmentActionLabel: (
    status:
      | "created"
      | "confirmed"
      | "cancelled"
      | "rescheduled"
      | "completed"
      | "no_show",
  ) => string;
};
export function CalendarStatusDialog({
  t,
  statusReasonTarget,
  setStatusReasonTarget,
  setStatusReason,
  statusReason,
  statusMutation,
  getAppointmentActionLabel,
}: Props) {
  return (
    <Modal
      title={t("appointments.statusReasonTitle")}
      open={Boolean(statusReasonTarget)}
      onClose={() => {
        setStatusReasonTarget(null);
        setStatusReason("");
      }}
    >
      <div className="space-y-4">
        <Input
          label={t("appointments.statusReason")}
          value={statusReason}
          onChange={(event) => setStatusReason(event.target.value)}
          placeholder={t("appointments.statusReasonPlaceholder")}
        />
        <div className="flex justify-end gap-2">
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              setStatusReasonTarget(null);
              setStatusReason("");
            }}
          >
            {t("common.back")}
          </Button>
          <Button
            type="button"
            variant="warning"
            isLoading={statusMutation.isPending}
            disabled={!statusReason.trim()}
            onClick={() => {
              if (!statusReasonTarget) return;
              statusMutation.mutate({
                id: statusReasonTarget.appointment.id,
                status: statusReasonTarget.status,
                reason: statusReason.trim(),
              });
            }}
          >
            {statusReasonTarget
              ? getAppointmentActionLabel(statusReasonTarget.status)
              : t("appointments.actions")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
