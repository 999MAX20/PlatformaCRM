import { useQuery } from "@tanstack/react-query";
import { appointmentsApi } from "../../api/appointments";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { dateInTimeZone } from "../../lib/format";
import { useAuth } from "../auth/AuthProvider";

export function useAppointmentYears(today: string, enabled = true) {
  const { business } = useActiveBusiness();
  const { user } = useAuth();
  const current = Number(today.slice(0, 4));
  const zone = business?.timezone || "Asia/Qyzylorda";
  const query = useQuery({
    queryKey: ["appointments", "year-range", business?.id, user?.id, zone],
    enabled: enabled && !!business?.id && !!user?.id,
    queryFn: async () => {
      const [first, last] = await Promise.all([
        appointmentsApi.workspace({ business: business!.id, ordering: "start_at", page_size: 1 }),
        appointmentsApi.workspace({ business: business!.id, ordering: "-start_at", page_size: 1 }),
      ]);
      const year = (value?: string) => value ? Number(dateInTimeZone(value, zone).slice(0, 4)) : undefined;
      return { first: year(first.results[0]?.start_at), last: year(last.results[0]?.start_at) };
    },
  });
  // These are quick-navigation bounds, never validation limits on selected dates.
  return { from: Math.min(query.data?.first ?? current, current), to: Math.max(query.data?.last ?? current, current + 5) };
}
