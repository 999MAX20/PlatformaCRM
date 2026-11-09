export const CONVERSATIONS_PRESET_STORAGE_KEY = "zani_conversations_filters_v1";

export const priorityOptions = [
  { value: "", labelKey: "conversations.anyPriority" },
  { value: "urgent", labelKey: "taskWorkspace.priority.urgent" },
  { value: "high", labelKey: "taskWorkspace.priority.high" },
  { value: "normal", labelKey: "taskWorkspace.priority.normal" },
  { value: "low", labelKey: "taskWorkspace.priority.low" },
];

export const channelOptions: Array<{ value: string; label: string } | { value: string; labelKey: string }> = [
  { value: "", labelKey: "conversations.allChannels" },
  { value: "website", label: "Website" },
  { value: "telegram", label: "Telegram" },
  { value: "whatsapp", label: "WhatsApp" },
  { value: "instagram", label: "Instagram" },
];
