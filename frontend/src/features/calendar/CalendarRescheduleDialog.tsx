import { useCalendarUrlState } from "./useCalendarUrlState";

import { useCalendarCommands } from "./useCalendarCommands";

import { AppointmentRescheduleForm } from "../../components/forms/AppointmentRescheduleForm";

import { Modal } from "../../components/ui/Modal";

import { useI18n } from "../../lib/i18n";

import { useActiveBusiness } from "../../hooks/useBusiness";

import type { Appointment, Resource } from "../../types";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  t: ReturnType<typeof useI18n>["t"];
  rescheduleTarget: Appointment | null;
  setRescheduleTarget: Dispatch<SetStateAction<Appointment | null>>;
  business: ReturnType<typeof useActiveBusiness>["business"];
  resourceItems: Resource[];
  rescheduleMutation: ReturnType<
    typeof useCalendarCommands
  >["rescheduleMutation"];
  businessTimeZone: ReturnType<typeof useCalendarUrlState>["businessTimeZone"];
};
export function CalendarRescheduleDialog({
  t,
  rescheduleTarget,
  setRescheduleTarget,
  business,
  resourceItems,
  rescheduleMutation,
  businessTimeZone,
}: Props) {
  return (
    <Modal
      title={t("appointments.rescheduleTitle")}
      open={Boolean(rescheduleTarget)}
      onClose={() => setRescheduleTarget(null)}
    >
      {rescheduleTarget ? (
        <AppointmentRescheduleForm
          appointment={rescheduleTarget}
          businessId={business.id}
          resources={resourceItems}
          onCancel={() => setRescheduleTarget(null)}
          onSubmit={(payload) =>
            rescheduleMutation.mutateAsync({
              id: rescheduleTarget.id,
              payload,
            })
          }
          isSubmitting={rescheduleMutation.isPending}
          timeZone={businessTimeZone}
        />
      ) : null}
    </Modal>
  );
}
