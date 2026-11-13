export function createPageLoadingState() {
  const pending = new Set<symbol>();
  const listeners = new Set<() => void>();
  let version = 0;
  let ready = false;
  function publish() {
    version += 1;
    listeners.forEach(listener => listener());
  }
  return {
    subscribe(listener: () => void) {
      listeners.add(listener);
      return () => { listeners.delete(listener); };
    },
    snapshot: () => version,
    isReady: () => ready,
    setPending(id: symbol, loading: boolean) {
      // Once revealed, polling and later interactions belong to their local surface.
      if (ready || pending.has(id) === loading) return;
      if (loading) pending.add(id);
      else pending.delete(id);
      publish();
    },
    revealIfReady() {
      if (ready || pending.size) return;
      ready = true;
      publish();
    },
  };
}
