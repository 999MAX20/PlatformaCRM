import { routeMetadata, merchantRoutePermission } from "./routeMetadata";
import { Navigate } from "react-router";
import { lazy } from "react";
const VoiceSettingsPage = lazy(() => import("../features/voice/VoiceSettingsPage"));
const VoiceHistoryPage = lazy(() => import("../features/voice/VoiceHistoryPage"));
import { RecordsPage, LegacyRecordsPage, ImportWorkspacePage } from "./routeLoaders";

import { PageLoader, UserStartRedirect, BusinessRouteRedirect, SettingsAccessRoute, IntegrationsSettingsRedirect } from "./routeGuards";
import { DashboardPage, AccountPage, ClientsPage, ClientWorkspacePage, TasksPage, TaskWorkspacePage, CalendarPage, AppointmentWorkspacePage, ConversationsPage, TimelinePage, BotsPage, BotDetailPage, PricingPage, AIAgentsPage, AutomationsPage, ResourcesPage, ServicesPage, BranchesPage, CompanyPage, AnalyticsPage, SettingsPage, WorkingHoursPage, SupportListPage, SupportDetailPage } from "./routeLoaders";
export const merchantFeatureRoutes = [
  { path: "voice/history", resource: "ai_assistant", permissionAction: "suggest", element: <PageLoader><VoiceHistoryPage /></PageLoader> },
  { path: "settings/voice", resource: "ai_assistant", permissionAction: "suggest", element: <PageLoader><VoiceSettingsPage /></PageLoader> },
{ path: "integrations/import", resource: "integrations", action: "manage", element: <PageLoader><ImportWorkspacePage /></PageLoader> },
{ path: routeMetadata.appointments.segment, ...merchantRoutePermission("appointments"), element: <PageLoader><RecordsPage /></PageLoader> },
{ path: "appointments/:id", resource: "appointments", element: <PageLoader><AppointmentWorkspacePage /></PageLoader> },
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
        <LegacyRecordsPage kind="lead" />
      </PageLoader>
    ) },
{
    path: "leads/:id",
    resource: "leads",
    element: (
      <PageLoader>
        <LegacyRecordsPage kind="lead" />
      </PageLoader>
    ),
  },
{ path: routeMetadata.deals.segment, ...merchantRoutePermission("deals"), element: (
      <PageLoader>
        <LegacyRecordsPage kind="deal" />
      </PageLoader>
    ) },
{
    path: "deals/:id",
    resource: "deals",
    element: (
      <PageLoader>
        <LegacyRecordsPage kind="deal" />
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
        <IntegrationsSettingsRedirect />
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
{ path: routeMetadata.business.segment, ...merchantRoutePermission("business"), element: <Navigate to="/app/business/company" replace /> },
{ path: "business/company", resource: "settings", element: <PageLoader><CompanyPage /></PageLoader> },
{ path: "business/staff", resource: "settings", element: <PageLoader><ResourcesPage key="staff" mode="staff" /></PageLoader> },
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
        <ResourcesPage key="physical" mode="physical" />
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
{ path: routeMetadata.settings.segment, element: (
      <PageLoader>
        <SettingsAccessRoute><SettingsPage /></SettingsAccessRoute>
      </PageLoader>
    ) },
{
    path: "billing",
    resource: "settings",
    permissionAction: "update",
    element: <Navigate to="/app/settings#billing" replace />,
  }
];
