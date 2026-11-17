import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router";
import { I18nProvider } from "../../src/lib/i18n";
import { NotificationHost } from "../../src/components/notifications/NotificationHost";
import { NotificationProvider } from "../../src/components/notifications/NotificationProvider";
import { TelegramInlineSetup } from "../../src/features/integrations/components/setup/TelegramSetup";
import { Dialog } from "../../src/components/ui/Overlay";
import type { BotChannel } from "../../src/types";
import "@fontsource-variable/manrope";
import "../../src/styles.css";

const channel = { id: 2, bot: 9, channel: "telegram", status: "error", config_json: {} } as BotChannel;
createRoot(document.getElementById("root")!).render(<I18nProvider><MemoryRouter><QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
  <NotificationHost><NotificationProvider><Dialog title="Telegram" open onClose={() => undefined}>
    <TelegramInlineSetup channel={channel} canManage={!location.search.includes("readonly")} />
  </Dialog></NotificationProvider></NotificationHost>
</QueryClientProvider></MemoryRouter></I18nProvider>);
