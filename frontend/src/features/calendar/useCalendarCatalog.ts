import { useQuery } from "@tanstack/react-query";
import { clientsApi } from "../../api/clients";
import { leadsApi } from "../../api/leads";
import { resourcesApi } from "../../api/resources";
import { servicesApi } from "../../api/services";
import { workingHoursApi } from "../../api/workingHours";

// Calendar selectors must not share an unscoped first-page cache with other pages.
export function useCalendarCatalog(businessId: number | undefined, userId: number | undefined, canViewClients: boolean, canViewLeads: boolean) {
  const scope = ["calendar", businessId, userId];
  const params = { business: businessId };
  const clients = useQuery({ queryKey: ["clients", ...scope], queryFn: () => clientsApi.listAll(params), enabled: !!businessId && canViewClients });
  const leads = useQuery({ queryKey: ["leads", ...scope], queryFn: () => leadsApi.listAll(params), enabled: !!businessId && canViewLeads });
  const services = useQuery({ queryKey: ["services", ...scope], queryFn: () => servicesApi.listAll(params), enabled: !!businessId });
  const resources = useQuery({ queryKey: ["resources", ...scope], queryFn: async () => (await resourcesApi.options()).filter(item => item.business === businessId), enabled: !!businessId });
  const workingHours = useQuery({ queryKey: ["working-hours", ...scope], queryFn: () => workingHoursApi.listAll(params), enabled: !!businessId });
  return { clients, leads, services, resources, workingHours };
}
