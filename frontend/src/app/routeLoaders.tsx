import { lazy } from "react";
export const AppLayout = lazy(() =>
  import("../components/layout/AppLayout").then((module) => ({
    default: module.AppLayout,
  })),
);
export const PlatformLayout = lazy(() =>
  import("../components/layout/PlatformLayout").then((module) => ({
    default: module.PlatformLayout,
  })),
);
export const InviteAcceptPage = lazy(() =>
  import("../features/auth/InviteAcceptPage").then((module) => ({
    default: module.InviteAcceptPage,
  })),
);
export const SignupPage = lazy(() =>
  import("../features/auth/SignupPage").then((module) => ({
    default: module.SignupPage,
  })),
);
export const DocumentsPage = lazy(() => import("../features/documents/DocumentsPage").then(module => ({ default: module.DocumentsPage })));
export const ForgotPasswordPage = lazy(() =>
  import("../features/auth/ForgotPasswordPage").then((module) => ({
    default: module.ForgotPasswordPage,
  })),
);
export const ResetPasswordPage = lazy(() =>
  import("../features/auth/ResetPasswordPage").then((module) => ({
    default: module.ResetPasswordPage,
  })),
);
export const AccountRecoveryPage = lazy(() => import("../features/auth/AccountRecoveryPage").then(module => ({ default: module.AccountRecoveryPage })));
export const MfaPage = lazy(() =>
  import("../features/auth/MfaPage").then((module) => ({
    default: module.MfaPage,
  })),
);
export const DashboardPage = lazy(() =>
  import("../features/dashboard/DashboardPage").then((module) => ({
    default: module.DashboardPage,
  })),
);
export const AccountPage = lazy(() =>
  import("../features/account/AccountPage").then((module) => ({
    default: module.AccountPage,
  })),
);
export const LeadsPage = lazy(() =>
  import("../features/leads/LeadsPage").then((module) => ({
    default: module.LeadsPage,
  })),
);
export const LeadWorkspacePage = lazy(() =>
  import("../features/leads/LeadWorkspacePage").then((module) => ({
    default: module.LeadWorkspacePage,
  })),
);
export const DealsPage = lazy(() =>
  import("../features/deals/DealsPage").then((module) => ({
    default: module.DealsPage,
  })),
);
export const DealWorkspacePage = lazy(() =>
  import("../features/deals/DealWorkspacePage").then((module) => ({
    default: module.DealWorkspacePage,
  })),
);
export const ClientsPage = lazy(() =>
  import("../features/clients/ClientsPage").then((module) => ({
    default: module.ClientsPage,
  })),
);
export const ClientWorkspacePage = lazy(() =>
  import("../features/clients/ClientWorkspacePage").then((module) => ({
    default: module.ClientWorkspacePage,
  })),
);
export const TasksPage = lazy(() =>
  import("../features/tasks/TasksPage").then((module) => ({
    default: module.TasksPage,
  })),
);
export const TaskWorkspacePage = lazy(() =>
  import("../features/tasks/TaskWorkspacePage").then((module) => ({
    default: module.TaskWorkspacePage,
  })),
);
export const CalendarPage = lazy(() =>
  import("../features/calendar/CalendarPage").then((module) => ({
    default: module.CalendarPage,
  })),
);
export const AppointmentWorkspacePage = lazy(() =>
  import("../features/calendar/AppointmentWorkspacePage").then((module) => ({
    default: module.AppointmentWorkspacePage,
  })),
);
export const ConversationsPage = lazy(() =>
  import("../features/conversations/ConversationsPage").then((module) => ({
    default: module.ConversationsPage,
  })),
);
export const TimelinePage = lazy(() =>
  import("../features/timeline/TimelinePage").then((module) => ({
    default: module.TimelinePage,
  })),
);
export const BotsPage = lazy(() =>
  import("../features/bots/BotsPage").then((module) => ({
    default: module.BotsPage,
  })),
);
export const BotDetailPage = lazy(() =>
  import("../features/bots/BotDetailPage").then((module) => ({
    default: module.BotDetailPage,
  })),
);
export const IntegrationsPage = lazy(() =>
  import("../features/integrations/IntegrationsPage").then((module) => ({
    default: module.IntegrationsPage,
  })),
);
export const PricingPage = lazy(() =>
  import("../features/pricing/PricingPage").then((module) => ({
    default: module.PricingPage,
  })),
);
export const AIAgentsPage = lazy(() =>
  import("../features/assistant/AIAgentsPage").then((module) => ({
    default: module.AIAgentsPage,
  })),
);
export const AutomationsPage = lazy(() =>
  import("../features/automations/AutomationsPage").then((module) => ({
    default: module.AutomationsPage,
  })),
);
export const ResourcesPage = lazy(() =>
  import("../features/resources/ResourcesPage").then((module) => ({
    default: module.ResourcesPage,
  })),
);
export const ServicesPage = lazy(() =>
  import("../features/services/ServicesPage").then((module) => ({
    default: module.ServicesPage,
  })),
);
export const BranchesPage = lazy(() => import("../features/business/BranchesPage").then((module) => ({ default: module.BranchesPage })));
export const AnalyticsPage = lazy(() =>
  import("../features/analytics/AnalyticsPage").then((module) => ({
    default: module.AnalyticsPage,
  })),
);
export const SettingsPage = lazy(() =>
  import("../features/settings/SettingsPage").then((module) => ({
    default: module.SettingsPage,
  })),
);
export const WorkingHoursPage = lazy(() =>
  import("../features/settings/WorkingHoursPage").then((module) => ({
    default: module.WorkingHoursPage,
  })),
);
export const PlatformOverviewPage = lazy(() =>
  import("../features/platform/PlatformOverviewPage").then((module) => ({
    default: module.PlatformOverviewPage,
  })),
);
export const PlatformOperationsPage = lazy(() =>
  import("../features/platform/PlatformOperationsPage").then((module) => ({
    default: module.PlatformOperationsPage,
  })),
);
export const PlatformMerchantsPage = lazy(() =>
  import("../features/platform/PlatformMerchantsPage").then((module) => ({
    default: module.PlatformMerchantsPage,
  })),
);
export const PlatformMerchantDetailPage = lazy(() =>
  import("../features/platform/PlatformMerchantDetailPage").then((module) => ({
    default: module.PlatformMerchantDetailPage,
  })),
);
export const SupportListPage = lazy(() => import("../features/support/SupportListPage").then(module => ({ default: module.SupportListPage })));
export const SupportDetailPage = lazy(() => import("../features/support/SupportDetailPage").then(module => ({ default: module.SupportDetailPage })));
export const SupportIncidentPage = lazy(() => import("../features/support/SupportIncidentPage").then(module => ({ default: module.SupportIncidentPage })));
