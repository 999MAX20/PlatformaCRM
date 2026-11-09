import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { I18nProvider } from "../src/lib/i18n";
import { YCloudSetup } from "../src/features/integrations/components/setup/YCloudSetup";
import type { BotChannel } from "../src/types";
import "../src/lib/focusModality";
import "@fontsource-variable/manrope";
import "@fontsource-variable/noto-sans";
import "../src/styles.css";

const params = new URLSearchParams(location.search);
localStorage.setItem("ai_smb_language", params.get("lang") || "ru");
document.documentElement.lang = params.get("lang") || "ru";
const client = new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } });
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={client}><MemoryRouter><I18nProvider>
    <main className="mx-auto max-w-3xl p-4"><YCloudSetup channel={{ id: 42 } as BotChannel} canManage={params.get("readonly") !== "1"} /></main>
  </I18nProvider></MemoryRouter></QueryClientProvider>,
);
