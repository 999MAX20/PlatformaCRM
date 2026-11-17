export function channelConnectionState(channel?: { status: string }) {
  if (!channel) return { key: "aiAgents.status.notConnected", tone: "neutral" } as const;
  switch (channel.status) {
    case "active": return { key: "aiAgents.status.connected", tone: "success" } as const;
    case "paused": return { key: "aiAgents.channel.paused", tone: "neutral" } as const;
    case "error": return { key: "aiAgents.status.error", tone: "warning" } as const;
    default: return { key: "aiAgents.status.setup", tone: "progress" } as const;
  }
}
