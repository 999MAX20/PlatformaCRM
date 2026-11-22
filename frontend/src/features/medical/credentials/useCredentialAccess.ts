import { useQuery } from "@tanstack/react-query";
import { medicalCredentialsApi } from "../../../api/medicalCredentials";
import { useActiveBusiness } from "../../../hooks/useBusiness";
import { useAuth } from "../../auth/AuthProvider";
import { medicalRoleDenied } from "../roles/useMedicalRolePage";

export function useCredentialAccess() {
  const { user } = useAuth();
  const { business } = useActiveBusiness();
  const enabled = !!business && !!user && !user.is_platform_user &&
    (business.business_type === "dentistry" || user.capabilities?.[String(business.id)]?.modules?.medical_records === true);
  const query = useQuery({ queryKey: ["medical-credential-access", user?.id, business?.id],
    queryFn: ({ signal }) => medicalCredentialsApi.access(Number(business?.id), signal),
    enabled, retry: false, staleTime: 0, gcTime: 0, refetchOnWindowFocus: true });
  return { ...query, allowed: enabled && !medicalRoleDenied(query.error) && query.data?.actions.view === true,
    checking: enabled && query.isPending };
}
