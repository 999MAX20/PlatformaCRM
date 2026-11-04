const sensitiveRoute = /[\/\\](reset-password|invite|api[\/\\]team[\/\\]invitations[\/\\]preview)(?=[\/\\?#]|$)/i;

export function redactTelemetryUrls(value: string): string {
  return value.replace(/[^\s"'<>]+/g, part => {
    // Split before decoding so encoded whitespace inside a bearer cannot expose its suffix.
    let decoded = part.replace(/\\\//g, "/");
    for (let i = 0; i < 8 && /%[0-9a-f]{2}/i.test(decoded); i++) {
      decoded = decoded.replace(/%([0-9a-f]{2})/gi, (_, hex: string) => String.fromCharCode(Number.parseInt(hex, 16)));
    }
    if (/%[0-9a-f]{2}/i.test(decoded)) return "[Encoded telemetry value omitted]";
    const match = sensitiveRoute.exec(decoded);
    if (!match) return part;
    const route = match[1].replace(/\\/g, "/").toLowerCase();
    const template = route === "reset-password" ? "/reset-password/:uid/:token" : `/${route}/:token`;
    return decoded.slice(0, match.index) + template;
  });
}

export function sanitizeTelemetry<T>(value: T): T {
  const ancestors = new WeakSet<object>();
  function clean(item: unknown, depth: number): unknown {
    if (typeof item === "string") return redactTelemetryUrls(item);
    if (item === null || typeof item !== "object" || item instanceof Date) return item;
    if (depth > 32) return "[Truncated]";
    if (ancestors.has(item)) return "[Circular]";
    const output: unknown[] | Record<string, unknown> = Array.isArray(item) ? [] : {};
    ancestors.add(item);
    for (const [key, child] of Object.entries(item)) {
      Object.defineProperty(output, redactTelemetryUrls(key), { value: clean(child, depth + 1), enumerable: true, writable: true, configurable: true });
    }
    ancestors.delete(item);
    return output;
  }
  return clean(value, 0) as T;
}
