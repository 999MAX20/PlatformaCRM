import { Navigate } from "react-router";

import { PageLoader, BusinessRouteRedirect } from "./routeGuards";
import { AccountPage, LeadsPage, DealsPage, ClientsPage, TasksPage, CalendarPage, ConversationsPage, TimelinePage, BotsPage, IntegrationsPage, AIAgentsPage, AutomationsPage, AnalyticsPage, SettingsPage } from "./routeLoaders";
export const legacyMerchantRoutes = [
  {
    path: "/leads",
    resource: "leads",
    element: (
      <PageLoader>
        <LeadsPage />
      </PageLoader>
    ),
  },
  {
    path: "/account",
    element: (
      <PageLoader>
        <AccountPage />
      </PageLoader>
    ),
  },
  {
    path: "/deals",
    resource: "deals",
    element: (
      <PageLoader>
        <DealsPage />
      </PageLoader>
    ),
  },
  {
    path: "/clients",
    resource: "clients",
    element: (
      <PageLoader>
        <ClientsPage />
      </PageLoader>
    ),
  },
  {
    path: "/tasks",
    resource: "tasks",
    element: (
      <PageLoader>
        <TasksPage />
      </PageLoader>
    ),
  },
  {
    path: "/calendar",
    resource: "appointments",
    element: (
      <PageLoader>
        <CalendarPage />
      </PageLoader>
    ),
  },
  {
    path: "/conversations",
    resource: "conversations",
    element: (
      <PageLoader>
        <ConversationsPage />
      </PageLoader>
    ),
  },
  {
    path: "/timeline",
    resource: "analytics",
    element: (
      <PageLoader>
        <TimelinePage />
      </PageLoader>
    ),
  },
  {
    path: "/crm-bots",
    resource: "integrations",
    element: (
      <PageLoader>
        <BotsPage />
      </PageLoader>
    ),
  },
  {
    path: "/integrations",
    resource: "integrations",
    element: (
      <PageLoader>
        <IntegrationsPage />
      </PageLoader>
    ),
  },
  {
    path: "/ai-assistant",
    element: (
      <PageLoader>
        <Navigate to="/app/ai-agents" replace />
      </PageLoader>
    ),
  },
  {
    path: "/ai",
    element: <Navigate to="/app/ai-agents" replace />,
  },
  {
    path: "/assistant",
    element: (
      <PageLoader>
        <Navigate to="/app/ai-agents" replace />
      </PageLoader>
    ),
  },
  {
    path: "/inbox",
    resource: "conversations",
    element: (
      <PageLoader>
        <ConversationsPage />
      </PageLoader>
    ),
  },
  {
    path: "/ai-agents",
    element: (
      <PageLoader>
        <AIAgentsPage />
      </PageLoader>
    ),
  },
  {
    path: "/automations",
    resource: "automations",
    element: (
      <PageLoader>
        <AutomationsPage />
      </PageLoader>
    ),
  },
  {
    path: "/services",
    resource: "settings",
    element: <BusinessRouteRedirect section="services" />,
  },
  {
    path: "/resources",
    resource: "settings",
    element: <BusinessRouteRedirect section="resources" />,
  },
  {
    path: "/working-hours",
    resource: "settings",
    element: <BusinessRouteRedirect section="working-hours" />,
  },
  {
    path: "/analytics",
    resource: "analytics",
    element: (
      <PageLoader>
        <AnalyticsPage />
      </PageLoader>
    ),
  },
  {
    path: "/settings",
    resource: "settings",
    permissionAction: "update",
    element: (
      <PageLoader>
        <SettingsPage />
      </PageLoader>
    ),
  },
  {
    path: "/billing",
    resource: "settings",
    permissionAction: "update",
    element: <Navigate to="/app/settings#billing" replace />,
  },
];
