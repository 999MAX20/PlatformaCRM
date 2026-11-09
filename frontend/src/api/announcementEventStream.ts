type StreamResult = "ended" | "reauthenticate" | "forbidden";

/** Bounded parser for our payload-free SSE invalidation protocol. */
export function eventFrames(onEvent: (event: string) => void) {
  let pending = "";
  return (chunk: string) => {
    pending += chunk;
    if (pending.length > 65_536) throw new Error("Invalid event stream frame");
    let boundary: number;
    while ((boundary = pending.indexOf("\n\n")) >= 0) {
      const frame = pending.slice(0, boundary);
      pending = pending.slice(boundary + 2);
      const event = frame.split("\n").find(line => line.startsWith("event:"))?.slice(6).trim();
      if (event) onEvent(event);
    }
  };
}

export function waitForReconnect(delay: number, signal: AbortSignal) {
  return new Promise<void>(resolve => {
    const done = () => { clearTimeout(timer); signal.removeEventListener("abort", done); resolve(); };
    const timer = setTimeout(done, delay);
    signal.addEventListener("abort", done, { once: true });
    if (signal.aborted) done();
  });
}

type StreamOptions = {
  signal: AbortSignal;
  connect: (signal: AbortSignal) => Promise<Response>;
  reauthenticate: () => Promise<void>;
  invalidate: () => Promise<unknown>;
  forbidden: () => Promise<unknown>;
  wait?: (delay: number, signal: AbortSignal) => Promise<void>;
  idleTimeout?: number;
};

export async function runAnnouncementEvents({ signal, connect, reauthenticate, invalidate, forbidden,
  wait = waitForReconnect, idleTimeout = 40_000 }: StreamOptions) {
  let delay = 500;
  let authAttempts = 0;
  while (!signal.aborted) {
    const attempt = new AbortController();
    const abort = () => attempt.abort();
    signal.addEventListener("abort", abort, { once: true });
    if (signal.aborted) abort();
    let idleTimer = setTimeout(abort, idleTimeout);
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
    let result: StreamResult = "ended";
    try {
      const response = await connect(attempt.signal);
      if (response.status === 401) result = "reauthenticate";
      else if (response.status === 403) result = "forbidden";
      else if (response.status === 400 || response.status === 404) return;
      else if (!response.ok || !response.headers.get("content-type")?.startsWith("text/event-stream") || !response.body) {
        throw new Error("Event stream unavailable");
      } else {
        reader = response.body.getReader();
        const cancel = () => { void reader?.cancel().catch(() => undefined); };
        attempt.signal.addEventListener("abort", cancel, { once: true });
        const decoder = new TextDecoder();
        let dirty = false;
        const parse = eventFrames(event => {
          if (event === "ready") { dirty = true; delay = 500; authAttempts = 0; }
          else if (event === "changed") dirty = true;
          else if (event === "reauthenticate" || event === "forbidden") result = event;
        });
        try {
          while (!attempt.signal.aborted && result === "ended") {
            const chunk = await reader.read();
            if (chunk.done) break;
            clearTimeout(idleTimer);
            idleTimer = setTimeout(abort, idleTimeout);
            parse(decoder.decode(chunk.value, { stream: true }));
            if (dirty && !signal.aborted) { dirty = false; await invalidate(); }
          }
        } finally { attempt.signal.removeEventListener("abort", cancel); }
      }
    } catch {
      // Ordinary polling keeps working; only transport recovery backs off.
    } finally {
      clearTimeout(idleTimer);
      signal.removeEventListener("abort", abort);
      attempt.abort();
      await reader?.cancel().catch(() => undefined);
      reader?.releaseLock();
    }
    if (signal.aborted) return;
    if (result === "forbidden") { await forbidden(); return; }
    if (result === "reauthenticate") {
      if (authAttempts++ > 0) return;
      try { await reauthenticate(); } catch { return; }
      continue;
    }
    await wait(delay, signal);
    delay = Math.min(delay * 2, 30_000);
  }
}
