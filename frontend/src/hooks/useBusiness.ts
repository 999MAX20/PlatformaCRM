import { useQuery } from "@tanstack/react-query";
import { useEffect } from "react";

import { businessesApi } from "../api/businesses";
import { useAuth } from "../features/auth/AuthProvider";
import { setActiveBusinessTimeZone } from "../lib/format";
import { preferredInvitationBusiness } from "../lib/invitationBusiness";

export function useBusinesses() {
  const { user, businesses, isAuthenticated, isLoading, isMerchantUser } = useAuth();

  return useQuery({
    queryKey: ["businesses", user?.id],
    queryFn: businessesApi.list,
    enabled: isAuthenticated && isMerchantUser && !isLoading,
    initialData: businesses.length ? businesses : undefined,
    staleTime: 60_000,
  });
}

export function useActiveBusiness() {
  const query = useBusinesses();
  const { businesses, user } = useAuth();
  const fallbackBusiness = businesses[0] ?? null;
  const available = query.data ?? businesses;
  const preferred = preferredInvitationBusiness(user?.id);
  const business = available.find(item => String(item.id) === preferred) ?? available[0] ?? null;

  useEffect(() => {
    setActiveBusinessTimeZone(business?.timezone);
  }, [business?.timezone]);

  return {
    ...query,
    isLoading: query.isLoading && !fallbackBusiness,
    business,
  };
}
