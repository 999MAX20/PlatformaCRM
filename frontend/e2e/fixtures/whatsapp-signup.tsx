import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router";
import { I18nProvider } from "../../src/lib/i18n";
import { NotificationProvider } from "../../src/components/notifications/NotificationProvider";
import { WhatsAppInlineSetup } from "../../src/features/integrations/components/setup/WhatsAppSetup";
import { MessengerSetupDialog } from "../../src/features/integrations/components/setup/IntegrationSetupUi";
import type { BotChannel } from "../../src/types";
import "../../src/lib/focusModality";
import "@fontsource-variable/manrope";
import "@fontsource-variable/noto-sans";
import "../../src/styles.css";

const channel = { id: 17, bot: 9, channel: "whatsapp", status: "draft", external_id: "", config_json: {} } as BotChannel;
function Fixture() {
  const [open, setOpen] = useState(false);
  const setup = <WhatsAppInlineSetup businessId={7} channel={channel} canManage={!location.search.includes("readonly")} />;
  if (!location.search.includes("dialog")) return setup;
  return <>
    <button id="open-whatsapp" onClick={() => setOpen(true)}>Open WhatsApp</button>
    <MessengerSetupDialog title="WhatsApp" logo="/integrations_logos/whatsapp.png" open={open}
      onClose={() => setOpen(false)} focusReturnId="open-whatsapp">{setup}</MessengerSetupDialog>
  </>;
}
createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
    <BrowserRouter><I18nProvider><NotificationProvider>
      <div className="mx-auto max-w-3xl p-4"><Fixture /></div>
    </NotificationProvider></I18nProvider></BrowserRouter>
  </QueryClientProvider>,
);
