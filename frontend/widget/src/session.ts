export type WidgetSession = {
  conversationId: string | null;
  messages: string[];
  fullName: string;
  phone: string;
  draft: string;
};

export function widgetSessionKey(apiUrl: string, publicToken: string, visitorId: string) {
  return `platforma:widget:${JSON.stringify([apiUrl.replace(/\/$/, ""), publicToken, visitorId])}`;
}

export function readWidgetSession(storage: Pick<Storage, "getItem">, key: string): WidgetSession | null {
  try {
    const value = JSON.parse(storage.getItem(key) || "null") as Partial<WidgetSession> | null;
    if (!value || (value.conversationId !== null && !/^[a-f0-9-]{36}$/i.test(value.conversationId || ""))) return null;
    if (!Array.isArray(value.messages) || !value.messages.every(message => typeof message === "string")) return null;
    return {
      conversationId: value.conversationId ?? null,
      messages: value.messages.slice(-100).map(message => message.slice(0, 20000)),
      fullName: typeof value.fullName === "string" ? value.fullName.slice(0, 255) : "",
      phone: typeof value.phone === "string" ? value.phone.slice(0, 32) : "",
      draft: typeof value.draft === "string" ? value.draft.slice(0, 20000) : "",
    };
  } catch {
    return null;
  }
}

export function saveWidgetSession(storage: Pick<Storage, "setItem">, key: string, session: WidgetSession) {
  try {
    storage.setItem(key, JSON.stringify({ ...session, messages: session.messages.slice(-100) }));
  } catch {
    // Storage denial must not prevent an in-memory conversation or retain a disabled form.
  }
}
