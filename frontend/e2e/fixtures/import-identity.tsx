import { useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { I18nProvider, useI18n } from "../../src/lib/i18n";
import { ImportJobReview } from "../../src/features/integrations/components/ImportJobReview";
import { importExportApi } from "../../src/api/importExport";
import type { ImportJob } from "../../src/types";
import "../../src/styles.css";

const message = "Phone or email matches multiple clients. Resolve the conflicting contacts before importing.";
const initial = {
  id: 1, business: 1, status: "previewed", entity_type: "clients", total_rows: 1,
  mapping_json: { full_name: "Name", phone: "Mobile", email: "Email" },
  mapping_fields: ["full_name", "phone", "email"],
  preview_json: { headers: ["Name", "Mobile", "Email"], rows: [{ Name: "Synthetic Client", Mobile: "8 (701) 111-22-33", Email: "second@example.test" }], import_summary: { ready: false, errors: 1 } },
  errors_json: { rows: [{ row: 1, field: "identity", message }] }, updated_at: "2026-11-23T00:00:00Z",
} as unknown as ImportJob;
let current = initial;
importExportApi.errors = async () => ({ count: current.errors_json?.rows?.length || 0, next: null, previous: null, results: current.errors_json?.rows || [] });
importExportApi.preview = async (_id, mapping) => {
  const errors = mapping.email ? [{ row: 1, field: "identity", message }] : [];
  current = { ...current, mapping_json: mapping, errors_json: { rows: errors }, updated_at: new Date().toISOString(),
    preview_json: { ...current.preview_json, import_summary: { ...current.preview_json?.import_summary, errors: errors.length, ready: errors.length === 0 } } } as ImportJob;
  return current;
};
importExportApi.confirm = async () => { current = { ...current, status: "imported" }; return current; };
function Fixture() {
  const [job, setJob] = useState(initial);
  const { setLanguage } = useI18n();
  return <main className="mx-auto max-w-3xl p-4"><h1>Google Sheets · synthetic import</h1>
    <nav aria-label="Fixture language">{(["ru", "kk", "en"] as const).map(language => <button key={language} className="m-2 p-2" onClick={() => setLanguage(language)}>{language}</button>)}</nav>
    <ImportJobReview job={job} userId={1} canCreate onChange={setJob} onImported={setJob} />
    <output data-testid="fixture-status">{job.status}</output></main>;
}
createRoot(document.getElementById("root")!).render(<I18nProvider><QueryClientProvider client={new QueryClient()}><Fixture /></QueryClientProvider></I18nProvider>);
