import { createCrudApi } from "./crud";
import type { Business } from "../types";
import { apiClient } from "./client";

export const businessesApi = createCrudApi<Business>("/api/businesses/");

export async function getBookingResponsibleOptions(businessId: Business["id"]) {
  const { data } = await apiClient.get<Array<{ id: number; label: string }>>(`/api/businesses/${businessId}/booking-responsible-options/`);
  return data;
}
