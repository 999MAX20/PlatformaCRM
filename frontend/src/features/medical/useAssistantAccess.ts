import { useQuery } from "@tanstack/react-query";
import { medicalAssistantsApi } from "../../api/medicalAssistants";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";

export function useAssistantAccess() {
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const enabled = !!business && !!user && !user.is_platform_user &&
    (business.business_type === "dentistry" || user.capabilities?.[String(business.id)]?.modules?.medical_records === true);
  const query = useQuery({ queryKey: ["medical-assistant-access", user?.id, business?.id],
    queryFn: ({ signal }) => medicalAssistantsApi.mine({ business_id: Number(business?.id), limit: 1 }, signal),
    enabled, retry: false, staleTime: 0, gcTime: 0, refetchOnWindowFocus: true });
  return { allowed: enabled && query.isSuccess && !query.isError };
}
