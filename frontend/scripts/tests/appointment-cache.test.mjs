import assert from "node:assert/strict";
import test from "node:test";
import { QueryClient, QueryObserver } from "@tanstack/react-query";
import { refreshAppointmentQueries } from "../../src/lib/appointmentCache.ts";

test("one appointment mutation refreshes mounted surfaces and invalidates cached client/Inbox state", async () => {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  const mounted = [["appointments", "calendar", 1], ["crm-card", "appointment", 7], ["available-slots", 1]];
  const cached = [["appointments", "client-workspace", 3], ["crm-card", "client", 3], ["inbox-context", 1, 1, 4]];
  const cleanup = [];
  let state = "created";
  try {
    for (const queryKey of [...mounted, ...cached]) {
      await client.fetchQuery({ queryKey, queryFn: async () => state });
      if (mounted.includes(queryKey)) {
        const observer = new QueryObserver(client, { queryKey, queryFn: async () => state });
        const unsubscribe = observer.subscribe(() => {});
        cleanup.push(() => { unsubscribe(); observer.destroy(); });
      }
    }
    client.setQueryData(["services", 1], "unchanged");
    for (const next of ["confirmed", "rescheduled", "cancelled"]) {
      state = next;
      await refreshAppointmentQueries(client, { id: 7, status: state });
      for (const queryKey of mounted) assert.equal(client.getQueryData(queryKey), state);
      for (const queryKey of cached) assert.equal(client.getQueryState(queryKey).isInvalidated, true);
      assert.equal(client.getQueryData(["appointments", 7]).status, state);
      assert.equal(client.getQueryState(["services", 1]).isInvalidated, false);
    }
    assert.equal(await client.fetchQuery({ queryKey: cached[2], queryFn: async () => state }), "cancelled");
  } finally {
    cleanup.forEach(fn => fn()); client.clear();
  }
});
