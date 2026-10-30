type RouteDescriptor = {
  path: string;
  segment: string;
  label: string;
  resource?: string;
  action?: string;
  menuResource?: string;
};

/** Shared navigation data; feature guards and business behavior stay in their modules. */
export const routeMetadata = {
  dashboard: { path: "/app/dashboard", segment: "dashboard", label: "nav.dashboard" },
  leads: { path: "/app/leads", segment: "leads", label: "nav.leads", resource: "leads" },
  deals: { path: "/app/deals", segment: "deals", label: "nav.deals", resource: "deals" },
  clients: { path: "/app/clients", segment: "clients", label: "nav.clients", resource: "clients" },
  tasks: { path: "/app/tasks", segment: "tasks", label: "nav.tasks", resource: "tasks" },
  calendar: { path: "/app/calendar", segment: "calendar", label: "nav.calendar", resource: "appointments" },
  conversations: { path: "/app/conversations", segment: "conversations", label: "nav.conversations", resource: "conversations" },
  aiAgents: { path: "/app/ai-agents", segment: "ai-agents", label: "nav.aiAgents", menuResource: "ai_automation" },
  integrations: { path: "/app/integrations", segment: "integrations", label: "nav.integrations", resource: "integrations" },
  business: { path: "/app/business", segment: "business", label: "nav.business", resource: "settings" },
  services: { path: "/app/business/services", segment: "business/services", label: "nav.services", resource: "settings" },
  resources: { path: "/app/business/resources", segment: "business/resources", label: "nav.resources", resource: "settings" },
  workingHours: { path: "/app/business/working-hours", segment: "business/working-hours", label: "nav.workingHours", resource: "settings" },
  analytics: { path: "/app/analytics", segment: "analytics", label: "nav.analytics", resource: "analytics" },
  timeline: { path: "/app/timeline", segment: "timeline", label: "nav.timeline", resource: "analytics" },
  settings: { path: "/app/settings", segment: "settings", label: "nav.settings", resource: "settings", action: "update" },
  account: { path: "/app/account", segment: "account", label: "nav.account" },
  support: { path: "/app/support", segment: "support", label: "supportCases.title" },
} satisfies Record<string, RouteDescriptor>;

export type MerchantRouteId = keyof typeof routeMetadata;

export function merchantRoutePermission(id: MerchantRouteId) {
  const descriptor: RouteDescriptor = routeMetadata[id];
  return { resource: descriptor.resource, permissionAction: descriptor.action };
}

export function merchantNavigationItem<Icon>(id: MerchantRouteId, icon: Icon) {
  const descriptor: RouteDescriptor = routeMetadata[id];
  return { to: descriptor.path, label: descriptor.label, icon, resource: descriptor.menuResource ?? descriptor.resource, action: descriptor.action };
}

// Preserve the existing title precedence and legacy display aliases.
const headerIds: MerchantRouteId[] = ["clients", "deals", "leads", "tasks", "calendar", "conversations", "services", "resources", "workingHours", "analytics", "timeline", "aiAgents", "integrations", "settings", "account", "support"];
const legacyHeaderAliases: Array<[string, MerchantRouteId]> = [["/app/services", "services"], ["/app/resources", "resources"], ["/app/working-hours", "workingHours"]];
export function getRouteTitle(pathname: string, t: (key: string) => string) {
  const match = headerIds.find(id => pathname === routeMetadata[id].path || pathname.startsWith(`${routeMetadata[id].path}/`));
  if (match) return t(routeMetadata[match].label);
  const alias = legacyHeaderAliases.find(([path]) => pathname === path || pathname.startsWith(`${path}/`));
  return t(routeMetadata[alias?.[1] ?? "dashboard"].label);
}
