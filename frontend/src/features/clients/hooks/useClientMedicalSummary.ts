import { useQuery } from "@tanstack/react-query";
import { getClientMedicalSummary } from "../../../api/clientMedicalSummary";

export function useClientMedicalSummary(businessId: number, clientId: number, userId: number, enabled: boolean) {
  return useQuery({
    queryKey: ["client-medical-overview", businessId, clientId, userId], enabled,
    retry: false, staleTime: 0,
    queryFn: ({ signal }) => getClientMedicalSummary(businessId, clientId, signal),
  });
}
