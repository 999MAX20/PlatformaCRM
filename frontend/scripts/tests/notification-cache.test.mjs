import assert from "node:assert/strict";
import test from "node:test";
import { QueryClient, QueryObserver } from "@tanstack/react-query";
import { invalidateNotificationReceipts } from "../../src/lib/notificationCache.ts";

test("receipt changes refresh mounted monitoring and stale cached monitoring without polling", async () => {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  let receipts = 0;
  const keys = [
    ["notifications", "page", 1, 2, 1],
    ["notifications-summary", "bell", 1, 2],
    ["notification-detail", 1, 2, 3],
    ["announcements", 1, 2, 1],
    ["announcements", "recipients", 1, 2, 3, 1],
  ];
  const observers = [];
  const unsubscribes = [];
  try {
    for (const queryKey of keys) {
      await client.fetchQuery({ queryKey, queryFn: async () => receipts });
      const observer = new QueryObserver(client, { queryKey, queryFn: async () => receipts });
      observers.push(observer);
      unsubscribes.push(observer.subscribe(() => {}));
    }
    const inactiveKey = ["announcements", "recipients", 1, 2, 4, 1];
    await client.fetchQuery({ queryKey: inactiveKey, queryFn: async () => receipts });
    client.setQueryData(["clients"], "unrelated");
    for (const count of [1, 0, 2]) {
      receipts = count;
      await invalidateNotificationReceipts(client);
      for (const key of keys) assert.equal(client.getQueryData(key), count);
      assert.equal(client.getQueryState(inactiveKey).isInvalidated, true);
      assert.equal(client.getQueryState(["clients"]).isInvalidated, false);
    }
    assert.equal(await client.fetchQuery({ queryKey: inactiveKey, queryFn: async () => receipts }), 2);
  } finally {
    unsubscribes.forEach(unsubscribe => unsubscribe());
    observers.forEach(observer => observer.destroy());
    client.clear();
  }
});

test("receipt mutation completion waits for the active monitoring response", async () => {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  const queryKey = ["announcements", "recipients", 1, 2, 3, 1];
  client.setQueryData(queryKey, 0);
  let release;
  const response = new Promise(resolve => { release = resolve; });
  const observer = new QueryObserver(client, { queryKey, queryFn: () => response });
  const unsubscribe = observer.subscribe(() => {});
  try {
    let complete = false;
    const refresh = invalidateNotificationReceipts(client).then(() => { complete = true; });
    await Promise.resolve();
    assert.equal(complete, false);
    release(1);
    await refresh;
    assert.equal(client.getQueryData(queryKey), 1);
    assert.equal(complete, true);
  } finally {
    unsubscribe(); observer.destroy(); client.clear();
  }
});
