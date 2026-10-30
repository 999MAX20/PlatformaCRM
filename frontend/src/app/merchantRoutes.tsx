import { routeMetadata, merchantRoutePermission } from "./routeMetadata";
import { Navigate } from "react-router";

import { PageLoader, UserStartRedirect, BusinessRouteRedirect } from "./routeGuards";
import { DashboardPage, AccountPage, LeadsPage, LeadWorkspacePage, DealsPage, DealWorkspacePage, ClientsPage, ClientWorkspacePage, TasksPage, TaskWorkspacePage, CalendarPage, AppointmentWorkspacePage, ConversationsPage, TimelinePage, BotsPage, BotDetailPage, IntegrationsPage, PricingPage, AIAgentsPage, AutomationsPage, ResourcesPage, ServicesPage, BranchesPage, AnalyticsPage, SettingsPage, WorkingHoursPage, SupportListPage, SupportDetailPage } from "./routeLoaders";
export const merchantFeatureRoutes = [
{ path: routeMetadata.support.segment, ...merchantRoutePermission("support"), element: <PageLoader><SupportListPage /></PageLoader> },
{ path: "support/:id", element: <PageLoader><SupportDetailPage /></PageLoader> },
{
    index: true,
    element: <UserStartRedirect />,
  },
{ path: routeMetadata.dashboard.segment, ...merchantRoutePermission("dashboard"), element: (
      <PageLoader>
        <DashboardPage />
      </PageLoader>
    ) },
{ path: routeMetadata.account.segment, ...merchantRoutePermission("account"), element: (
      <PageLoader>
        <AccountPage />
      </PageLoader>
    ) },
{ path: routeMetadata.leads.segment, ...merchantRoutePermission("leads"), element: (
      <PageLoader>
        <LeadsPage />
      </PageLoader>
    ) },
{
    path: "leads/:id",
    resource: "leads",
    element: (
      <PageLoader>
        <LeadWorkspacePage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.deals.segment, ...merchantRoutePermission("deals"), element: (
      <PageLoader>
        <DealsPage />
      </PageLoader>
    ) },
{
    path: "deals/:id",
    resource: "deals",
    element: (
      <PageLoader>
        <DealWorkspacePage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.clients.segment, ...merchantRoutePermission("clients"), element: (
      <PageLoader>
        <ClientsPage />
      </PageLoader>
    ) },
{
    path: "clients/:id",
    resource: "clients",
    element: (
      <PageLoader>
        <ClientWorkspacePage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.tasks.segment, ...merchantRoutePermission("tasks"), element: (
      <PageLoader>
        <TasksPage />
      </PageLoader>
    ) },
{
    path: "tasks/:id",
    resource: "tasks",
    element: (
      <PageLoader>
        <TaskWorkspacePage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.calendar.segment, ...merchantRoutePermission("calendar"), element: (
      <PageLoader>
        <CalendarPage />
      </PageLoader>
    ) },
{
    path: "calendar/:id",
    resource: "appointments",
    element: (
      <PageLoader>
        <AppointmentWorkspacePage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.conversations.segment, ...merchantRoutePermission("conversations"), element: (
      <PageLoader>
        <ConversationsPage />
      </PageLoader>
    ) },
{
    path: "conversations/:id",
    resource: "conversations",
    element: (
      <PageLoader>
        <ConversationsPage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.timeline.segment, ...merchantRoutePermission("timeline"), element: (
      <PageLoader>
        <TimelinePage />
      </PageLoader>
    ) },
{
    path: "bots",
    resource: "integrations",
    element: (
      <PageLoader>
        <BotsPage />
      </PageLoader>
    ),
  },
{
    path: "bots/:id",
    resource: "integrations",
    element: (
      <PageLoader>
        <BotDetailPage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.integrations.segment, ...merchantRoutePermission("integrations"), element: (
      <PageLoader>
        <IntegrationsPage />
      </PageLoader>
    ) },
{
    path: "pricing",
    resource: "integrations",
    element: (
      <PageLoader>
        <PricingPage />
      </PageLoader>
    ),
  },
{
    path: "ai-assistant",
    element: (
      <PageLoader>
        <Navigate to="/app/ai-agents" replace />
      </PageLoader>
    ),
  },
{
    path: "ai",
    element: <Navigate to="/app/ai-agents" replace />,
  },
{
    path: "assistant",
    element: (
      <PageLoader>
        <Navigate to="/app/ai-agents" replace />
      </PageLoader>
    ),
  },
{
    path: "inbox",
    resource: "conversations",
    element: (
      <PageLoader>
        <ConversationsPage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.aiAgents.segment, ...merchantRoutePermission("aiAgents"), element: (
      <PageLoader>
        <AIAgentsPage />
      </PageLoader>
    ) },
{
    path: "ai-agents/:id",
    element: (
      <PageLoader>
        <AIAgentsPage />
      </PageLoader>
    ),
  },
{
    path: "ai-agents/:id/:section",
    element: (
      <PageLoader>
        <AIAgentsPage />
      </PageLoader>
    ),
  },
{
    path: "automations",
    resource: "automations",
    element: (
      <PageLoader>
        <AutomationsPage />
      </PageLoader>
    ),
  },
{ path: routeMetadata.business.segment, ...merchantRoutePermission("business"), element: <Navigate to="/app/business/services" replace /> },
{ path: routeMetadata.services.segment, ...merchantRoutePermission("services"), element: (
      <PageLoader>
        <ServicesPage />
      </PageLoader>
    ) },
{
    path: "business/branches",
    resource: "settings",
    element: <PageLoader><BranchesPage /></PageLoader>,
  },
{ path: routeMetadata.resources.segment, ...merchantRoutePermission("resources"), element: (
      <PageLoader>
        <ResourcesPage />
      </PageLoader>
    ) },
{ path: routeMetadata.workingHours.segment, ...merchantRoutePermission("workingHours"), element: (
      <PageLoader>
        <WorkingHoursPage />
      </PageLoader>
    ) },
{
    path: "services",
    resource: "settings",
    element: <BusinessRouteRedirect section="services" />,
  },
{
    path: "resources",
    resource: "settings",
    element: <BusinessRouteRedirect section="resources" />,
  },
{
    path: "working-hours",
    resource: "settings",
    element: <BusinessRouteRedirect section="working-hours" />,
  },
{ path: routeMetadata.analytics.segment, ...merchantRoutePermission("analytics"), element: (
      <PageLoader>
        <AnalyticsPage />
      </PageLoader>
    ) },
{ path: routeMetadata.settings.segment, ...merchantRoutePermission("settings"), element: (
      <PageLoader>
        <SettingsPage />
      </PageLoader>
    ) },
{
    path: "billing",
    resource: "settings",
    permissionAction: "update",
    element: <Navigate to="/app/settings#billing" replace />,
  }
];
