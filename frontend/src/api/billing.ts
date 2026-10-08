import { apiClient, unwrapList } from "./client";
import type { EntitlementSummaryItem, Id, Subscription, SubscriptionPlan, UsageSummaryItem } from "../types";

export const billingApi = {
  plans: async () => {
    const { data } = await apiClient.get<SubscriptionPlan[] | { results: SubscriptionPlan[] }>("/api/billing/plans/");
    return unwrapList(data);
  },
  currentSubscription: async (business: Id) => {
    const { data } = await apiClient.get<Subscription | null>("/api/billing/current-subscription/", { params: { business } });
    return data;
  },
  usageSummary: async (business: Id) => {
    const { data } = await apiClient.get<UsageSummaryItem[] | { results: UsageSummaryItem[] }>("/api/billing/usage-summary/", { params: { business } });
    return unwrapList(data);
  },
  entitlements: async (business: Id) => {
    const { data } = await apiClient.get<EntitlementSummaryItem[] | { results: EntitlementSummaryItem[] }>("/api/billing/entitlements/", { params: { business } });
    return unwrapList(data);
  },
  updateSettings: async (payload: Pick<Partial<Subscription>, "billing_email" | "payment_method" | "invoice_details_json"> & { business: Id }) => {
    const { data } = await apiClient.patch<Subscription>("/api/billing/current-subscription/settings/", payload);
    return data;
  },
  requestPlanChange: async (plan: Id, business: Id) => {
    const { data } = await apiClient.post<Subscription>("/api/billing/current-subscription/change-plan/", { plan, business });
    return data;
  },
  pause: async (business: Id) => {
    const { data } = await apiClient.post<Subscription>("/api/billing/current-subscription/pause/", { business });
    return data;
  },
  resume: async (business: Id) => {
    const { data } = await apiClient.post<Subscription>("/api/billing/current-subscription/resume/", { business });
    return data;
  },
  cancel: async (business: Id) => {
    const { data } = await apiClient.post<Subscription>("/api/billing/current-subscription/cancel/", { business });
    return data;
  },
};
