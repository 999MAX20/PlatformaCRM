import axios, { AxiosError } from "axios";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import { AuthProvider } from "../../src/features/auth/AuthProvider";
import { GoogleSheetsCard } from "../../src/features/integrations/components/GoogleSheetsCard";
import { GoogleCalendarCard } from "../../src/features/integrations/components/GoogleCalendarCard";
import { googleIntegrationsApi } from "../../src/api/googleIntegrations";
import { googleCalendarApi } from "../../src/api/googleCalendar";
import { apiClient } from "../../src/api/client";
import "../../src/styles.css";

// Synthetic fixture only: no auth, provider or application request leaves the page.
axios.defaults.adapter = async config => {
  throw new AxiosError("Synthetic signed-out session", "ERR_BAD_REQUEST", config, undefined,
    { data: {}, status: 401, statusText: "Unauthorized", headers: {}, config });
};
apiClient.defaults.adapter = axios.defaults.adapter;
const connected = new Set([1, 2]);
googleIntegrationsApi.status = async (_business, provider) => {
  const id = provider === "google_calendar" ? 2 : 1;
  return { id, status: connected.has(id) ? "connected" : "disconnected", email: "synthetic@example.test",
    enabled: true, retention_enabled: !location.search.includes("disabled") };
};
googleIntegrationsApi.disconnect = async id => {
  connected.delete(Number(id));
  return { id: Number(id), status: "disconnected", email: "", google_revoked: true };
};
googleIntegrationsApi.exports = async () => [];
googleCalendarApi.bindings = async () => ({ enabled: true, specialists: [], bindings: [{
  id: "synthetic-binding", resource_id: 1, resource_name: "Synthetic specialist", calendar_name: "",
  enabled: false, last_sync_at: null, error_code: "", stale: false, pending: false,
  coverage_start: null, coverage_end: null, next_sync_at: null,
}] });
function Fixture() {
  const { setLanguage } = useI18n();
  return <main className="mx-auto max-w-3xl space-y-4 p-4">
    <h1>Google retention · synthetic verification</h1>
    <nav aria-label="Fixture language">{(["ru", "kk", "en"] as const).map(language =>
      <button key={language} className="m-2 p-2" onClick={() => setLanguage(language)}>{language}</button>)}</nav>
    <GoogleSheetsCard businessId={1} /><GoogleCalendarCard businessId={1} />
  </main>;
}
createRoot(document.getElementById("root")!).render(<I18nProvider>
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <AuthProvider><Fixture /></AuthProvider>
  </QueryClientProvider>
</I18nProvider>);
