export function deliveryNotice(status: string) {
  if (status === "sent") return { key: "conversations.replySent", tone: "success" } as const;
  if (status === "failed") return { key: "conversations.deliveryStatusFailed", tone: "warning" } as const;
  if (status === "delivery_unknown") return { key: "conversations.deliveryYCloudUnknown", tone: "warning" } as const;
  if (status === "accepted") return { key: "conversations.deliveryYCloudAccepted", tone: "info" } as const;
  return { key: "conversations.deliveryStatusQueued", tone: "info" } as const;
}
