import type { CurrentUser, Id, Lead } from "../types";
import type { OfflineLeadAction } from "../features/leads/types";

const PREFIX = "platforma:leads:v1:";
const LEGACY_KEYS = ["zani_leads_cache", "zani_leads_offline_queue"];

export type LeadOfflineScope = { key: string; identity: string; userId: Id; businessId: Id };
export type LeadOfflineData = { leads: Lead[]; queue: OfflineLeadAction[] };

export function leadOfflineScope(user: CurrentUser | null, businessId?: Id): LeadOfflineScope | null {
  if (!user || !businessId) return null;
  return {
    key: `${PREFIX}${user.id}:${businessId}`,
    userId: user.id,
    businessId,
    // A remounted workspace must not recover data from a broader access profile.
    identity: JSON.stringify([user.id, businessId, user.role, user.is_platform_user,
      user.is_merchant_user, user.memberships, user.effective_permissions, user.capabilities]),
  };
}

function removeLegacyData() {
  for (const key of LEGACY_KEYS) localStorage.removeItem(key);
}

export function clearLeadOfflineStorage() {
  try {
    removeLegacyData();
    const keys = Array.from({ length: localStorage.length }, (_, index) => localStorage.key(index));
    for (const key of keys) if (key?.startsWith(PREFIX)) localStorage.removeItem(key);
  } catch {
    // Restricted storage must not prevent terminating the authenticated session.
  }
}

export function readLeadOfflineData(scope: LeadOfflineScope | null): LeadOfflineData {
  const empty = { leads: [], queue: [] };
  try {
    // Old records have no trustworthy owner; never migrate them into this session.
    removeLegacyData();
    if (!scope) return empty;
    const stored = JSON.parse(localStorage.getItem(scope.key) || "null");
    if (stored?.identity !== scope.identity || !Array.isArray(stored.leads) || !Array.isArray(stored.queue)) {
      localStorage.removeItem(scope.key);
      return empty;
    }
    return {
      leads: stored.leads.filter((lead: Lead | null) => lead?.business === scope.businessId),
      queue: stored.queue,
    };
  } catch {
    return empty;
  }
}

export function writeLeadOfflineData(scope: LeadOfflineScope, data: LeadOfflineData) {
  try {
    localStorage.setItem(scope.key, JSON.stringify({
      identity: scope.identity,
      leads: data.leads.filter(lead => lead.business === scope.businessId).slice(0, 50),
      queue: data.queue,
    }));
    return true;
  } catch {
    return false;
  }
}
