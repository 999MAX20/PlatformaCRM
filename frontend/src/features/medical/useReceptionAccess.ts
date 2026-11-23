import { useQuery } from "@tanstack/react-query";
import { medicalPatientsApi } from "../../api/medicalPatients";
import { useActiveBusiness } from "../../hooks/useBusiness";
import { useAuth } from "../auth/AuthProvider";

export function useReceptionAccess() {
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const enabled = !!business && !!user && !user.is_platform_user &&
    (business.business_type === "dentistry" || user.capabilities?.[String(business.id)]?.modules?.medical_records === true);
  const query = useQuery({ queryKey: ["medical-reception-access", user?.id, business?.id],
    queryFn: ({ signal }) => medicalPatientsApi.searchAccess(Number(business?.id), signal),
    enabled, retry: false, staleTime: 0, gcTime: 0, refetchOnWindowFocus: true });
  return { ...query, allowed: enabled && query.isSuccess && !query.isError && !!query.data.branches.length };
}
