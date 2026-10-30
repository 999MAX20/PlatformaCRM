import { useCalendarUrlState } from "./useCalendarUrlState";

import { useCalendarCommands } from "./useCalendarCommands";

import { AppointmentForm } from "../../components/forms/AppointmentForm";

import { Modal } from "../../components/ui/Modal";

import { useI18n } from "../../lib/i18n";

import { useActiveBusiness } from "../../hooks/useBusiness";

import type { Client, Service, Resource, Lead } from "../../types";

import type { Dispatch, SetStateAction } from "react";
type Props = {
  t: ReturnType<typeof useI18n>["t"];
  bookingOpen: boolean;
  setBookingOpen: Dispatch<SetStateAction<boolean>>;
  setBookingPrefill: Dispatch<
    SetStateAction<{
      branch?: number | null | undefined;
      client?: number | null | undefined;
      service?: number | null | undefined;
      resource?: number | null | undefined;
      lead?: number | null | undefined;
      date?: string | undefined;
      slot?: string | undefined;
      hour?: number | undefined;
      source?:
        | "website"
        | "telegram"
        | "whatsapp"
        | "instagram"
        | "manual"
        | "bot"
        | undefined;
    } | null>
  >;
  business: ReturnType<typeof useActiveBusiness>["business"];
  clientItems: Client[];
  serviceItems: Service[];
  resourceItems: Resource[];
  leadItems: Lead[];
  bookingPrefill: {
    branch?: number | null | undefined;
    client?: number | null | undefined;
    service?: number | null | undefined;
    resource?: number | null | undefined;
    lead?: number | null | undefined;
    date?: string | undefined;
    slot?: string | undefined;
    hour?: number | undefined;
    source?:
      | "website"
      | "telegram"
      | "whatsapp"
      | "instagram"
      | "manual"
      | "bot"
      | undefined;
  } | null;
  date: ReturnType<typeof useCalendarUrlState>["date"];
  branchFilter: ReturnType<typeof useCalendarUrlState>["branchFilter"];
  mutation: ReturnType<typeof useCalendarCommands>["mutation"];
  businessTimeZone: ReturnType<typeof useCalendarUrlState>["businessTimeZone"];
};
export function CalendarBookingDialog({
  t,
  bookingOpen,
  setBookingOpen,
  setBookingPrefill,
  business,
  clientItems,
  serviceItems,
  resourceItems,
  leadItems,
  bookingPrefill,
  date,
  branchFilter,
  mutation,
  businessTimeZone,
}: Props) {
  return (
    <Modal
      title={t("calendar.newBooking")}
      open={bookingOpen}
      onClose={() => {
        setBookingOpen(false);
        setBookingPrefill(null);
      }}
    >
      <AppointmentForm
        businessId={business.id}
        clients={clientItems}
        services={serviceItems}
        resources={resourceItems}
        leads={leadItems}
        prefill={{
          ...(bookingPrefill || { date }),
          branch:
            bookingPrefill?.branch ||
            (branchFilter ? Number(branchFilter) : undefined),
        }}
        onSubmit={(payload) => mutation.mutateAsync(payload)}
        timeZone={businessTimeZone}
      />
    </Modal>
  );
}
