import { apiClient } from "./client";

export type BillingBuyer = { kind: "person" | "company" | "sole_trader"; name: string; tax_id: string; email: string };
export type BillingOffer = { id: string; plan: string; amount: string; currency: string; period_start: string; period_end: string; expires_at: string };
export type BillingOrder = BillingOffer & {
  buyer: BillingBuyer; seller: Record<string, string>; created_at: string; payment_status: string; application_status: string;
  application_code: string; applied_at: string | null; receipt_count: number;
  attempts: { id: string; status: string; failure_code: string; checkout_url?: string }[];
  receipts: { id: number; source: string; amount: string; currency: string; status: string; received_at: string; reference?: string; confirmed_by?: number | null; support_case_id?: number | null; reason?: string }[];
  events: { kind: string; code: string; created_at: string; actor?: number | null; support_case_id?: number | null; reason?: string }[];
};
export type BillingSnapshot = { enabled: boolean; can_confirm_bank: boolean; card_available: boolean; offers: BillingOffer[]; orders: BillingOrder[]; count: number; page: number;
  subscription: { plan: string; status: string; next_payment_at: string | null; technical_entitlements: { metric: string; value: number; limit: number | null }[] } | null;
  business_status: string; commercial_expiry_enforced: boolean };
export type PaymentAction = "confirm-bank" | "recover" | "reconcile";
export type PaymentCommand = { support_case_id: number; reason: string; reference?: string; amount?: string; currency?: string; received_at?: string };
const root = (business: string, platform = false) => platform ? `/api/platform/merchants/${business}/billing-orders/` : `/api/billing/businesses/${business}/orders/`;
export const billingCommerceApi = {
  get: async (business: string, platform = false, page = 1) => (await apiClient.get<BillingSnapshot>(root(business, platform), { params: { page } })).data,
  create: async (business: string, values: { request_id: string; offer_id: string; buyer: BillingBuyer }) => (await apiClient.post<BillingOrder>(root(business), values)).data,
  card: async (business: string, order: string, action: "checkout" | "reconcile") => (await apiClient.post<BillingSnapshot>(`${root(business)}${order}/${action}/`, {})).data,
  action: async (business: string, order: string, action: PaymentAction, values: PaymentCommand, token: string) =>
    (await apiClient.post<BillingOrder>(`${root(business, true)}${order}/${action}/`, values, { headers: { "X-Zani-MFA-Step-Up": token } })).data,
};
