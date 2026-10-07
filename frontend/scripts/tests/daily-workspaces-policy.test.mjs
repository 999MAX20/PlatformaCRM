import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const root = new URL("../../src/", import.meta.url);

async function source(path) {
  return readFile(new URL(path, root), "utf8");
}

test("capability-aware permissions hide disabled daily modules before role grants", async () => {
  const permissions = await source("lib/permissions.ts");
  assert.match(permissions, /if \(!isBusinessResourceEnabled\(user, businessId, resource\)\) return false;/);
  assert.match(permissions, /deals:\s*"deals"/);
  assert.match(permissions, /if \(role === "staff" \|\| role === "doctor"\) return "specialist";/);
});

test("command palette reuses permission and capability policy for commands and entity queries", async () => {
  const palette = await source("components/layout/CommandPalette.tsx");

  assert.match(palette, /hasPermission\(user, businessId, command\.resource, command\.action\)/);
  assert.match(palette, /id: "create-lead"[^\n]+resource: "leads", action: "create"/);
  assert.match(palette, /id: "open-settings"[^\n]+resource: "settings", action: "update"/);
  assert.match(palette, /id: "open-deals"[^\n]+resource: "deals"/);
  assert.match(palette, /id: "open-ai-agents"[^\n]+resource: "ai_automation"/);
  assert.match(palette, /clients: canViewClients/);
  assert.match(palette, /leads: canViewLeads/);
  assert.match(palette, /services: canViewServices/);
  assert.match(palette, /canViewLeads \? leads\.data \|\| \[\] : \[\]/);
  assert.match(palette, /canViewClients \? clients\.data \|\| \[\] : \[\]/);
  assert.match(palette, /canViewServices \? services\.data \|\| \[\] : \[\]/);
});

test("daily workspaces preserve recoverable and role-valid actions", async () => {
  const [tasks, calendar, appointmentAccess, conversations, conversationList] = await Promise.all([
    source("features/tasks/TasksPage.tsx"),
    source("features/calendar/CalendarPage.tsx"),
    source("features/calendar/appointmentAccess.ts"),
    source("features/conversations/ConversationsPage.tsx"),
    source("features/conversations/components/ConversationListPane.tsx"),
  ]);

  assert.match(tasks, /primaryAction:\s*canCreateTask/);
  assert.match(tasks, /includeTeamData:\s*canViewTeam/);
  assert.match(calendar, /data-testid="calendar-error-state"/);
  assert.match(calendar, /primaryAction:\s*canCreateAppointment/);
  assert.match(calendar, /canAccessAppointmentAction/);
  assert.match(appointmentAccess, /resource\?\.linked_user/);
  assert.match(appointmentAccess, /scope !== "own"/);
  assert.match(conversations, /data-testid="inbox-error-state"/);
  assert.match(conversations, /businessConnectorsApi\.list/);
  assert.match(conversations, /retry:\s*false/);
  assert.match(conversations, /connector\.capability === "communications"/);
  assert.match(conversations, /communicationConnectors\.isError/);
  assert.match(conversations, /communicationConnectors\.refetch\(\)/);
  assert.doesNotMatch(conversations, /!channel\.is_connected && channel\.total > 0/);
  assert.match(conversations, /!isIntegrationsAction\(action\.href\)/);
  assert.doesNotMatch(conversations, /onRetryLastMessage=/);
  assert.doesNotMatch(conversationList, /canRetryLastMessage\(conversation\)/);
  assert.match(conversationList, /data-testid="inbox-provider-status-unavailable"/);
  assert.match(conversationList, /data-testid="inbox-provider-status-retry"/);
  assert.match(conversationList, /t\("conversations\.channelStatusUnavailable"\)/);
});

test("owner dashboard fetches and renders capability-scoped daily modules", async () => {
  const [page, dashboard] = await Promise.all([
    source("features/dashboard/DashboardPage.tsx"),
    source("features/dashboard/OperationalDashboard.tsx"),
  ]);

  assert.match(page, /workQueuesApi\.get/);
  assert.doesNotMatch(page, /useCrmEntities|appointmentsApi\.list|tasksApi\.list/);
  for (const resource of ["leads", "deals", "appointments", "tasks", "conversations"]) {
    assert.ok(page.includes(`${resource}: permitted("${resource}")`));
  }
  assert.match(dashboard, /access\[resource\] && data\.available\[resource\]/);
  assert.match(dashboard, /metrics\.filter\(\(metric\) => canSee\(metric\.resource\)\)/);
  assert.match(dashboard, /data\.attention\.filter\(\(item\) => canSee\(resourceByType\[item\.type\]\)\)/);
});

test("shared owner and manager operations render only after loading and error guards", async () => {
  const dashboard = await source("features/dashboard/OperationalDashboard.tsx");
  const readyMarker = dashboard.indexOf('data-testid="dashboard-operations"');
  const loadingGuard = dashboard.indexOf("if (loading || !data) return <LoadingState />");
  const errorGuard = dashboard.indexOf("if (error)");
  assert.ok(errorGuard >= 0 && errorGuard < loadingGuard);
  assert.ok(loadingGuard >= 0 && loadingGuard < readyMarker);
  assert.doesNotMatch(dashboard, /summary\.[a-z_]+ \|\| 0/);
});

test("owner AI brief does not substitute unsourced local recommendations", async () => {
  const dashboard = await source("features/dashboard/OwnerDashboard.tsx");
  assert.match(dashboard, /ownerBrief\?\.recommendations/);
  assert.match(dashboard, /item\.source_ids\.some\(\(id\) => ownerBrief\?\.sources\.some/);
  assert.match(dashboard, /source\.id === id/);
  assert.match(dashboard, /recommendation\.labels\.join/);
  assert.doesNotMatch(dashboard, /if \(overdueTasks > 0\)|if \(newLeadsCount > 0\)/);
});
