import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { appointmentMessageSettingsApi } from "../../api/appointments";

import { useActiveBusiness } from "../../hooks/useBusiness";

import type { AppointmentMessageSetting } from "../../types";

type Context = {
  business: ReturnType<typeof useActiveBusiness>["business"];
  canManageSettings: boolean;
  activeSettingsSection: string;
  queryClient: ReturnType<typeof useQueryClient>;
};

export function useSettingsMessages({ business, canManageSettings, activeSettingsSection, queryClient }: Context) {
const [appointmentMessageDrafts, setAppointmentMessageDrafts] = useState<
    Record<number, Partial<AppointmentMessageSetting>>
  >({});

const appointmentMessageSettings = useQuery({
    queryKey: ["appointment-message-settings", business?.id],
    queryFn: () =>
      appointmentMessageSettingsApi.list({ business: business?.id }),
    enabled: activeSettingsSection === "appointment-messages" && Boolean(business?.id && canManageSettings),
  });

const appointmentMessageMutation = useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: number;
      payload: Partial<AppointmentMessageSetting>;
    }) => appointmentMessageSettingsApi.update({ id, payload }),
    onSuccess: (saved, { id, payload }) => {
      queryClient.setQueryData<AppointmentMessageSetting[]>(["appointment-message-settings", business?.id], (rows) => rows?.map((row) => Number(row.id) === id ? saved : row));
      setAppointmentMessageDrafts((current) => {
        const remaining = { ...current[id] };
        for (const key of Object.keys(payload) as Array<keyof AppointmentMessageSetting>) {
          if (remaining[key] === payload[key]) delete remaining[key];
        }
        const next = { ...current };
        if (Object.keys(remaining).length) next[id] = remaining;
        else delete next[id];
        return next;
      });
      queryClient.invalidateQueries({
        queryKey: ["appointment-message-settings"],
      });
    },
  });

const appointmentMessages = appointmentMessageSettings.data || [];

const appointmentMessageValue = <K extends keyof AppointmentMessageSetting>(
    setting: AppointmentMessageSetting,
    key: K,
  ): AppointmentMessageSetting[K] => {
    return (
      (appointmentMessageDrafts[Number(setting.id)]?.[key] as
        AppointmentMessageSetting[K] | undefined) ?? setting[key]
    );
  };
return { appointmentMessageDrafts, setAppointmentMessageDrafts, appointmentMessageSettings, appointmentMessageMutation, appointmentMessages, appointmentMessageValue };
}
