import { useEffect, useMemo, useState } from "react";

import type { AppError } from "../../api/appError";

// Error identity changes for a new failed request, not for the countdown ticks.
export function useRecoveryDelay(error?: AppError) {
  const deadline = useMemo(() => Date.now() + (error?.retryAfterSeconds || 0) * 1000, [error]);
  const [now, setNow] = useState(Date.now);
  useEffect(() => {
    setNow(Date.now());
    if (deadline <= Date.now()) return;
    const timer = window.setInterval(() => {
      setNow(Date.now());
      if (Date.now() >= deadline) window.clearInterval(timer);
    }, 250);
    return () => window.clearInterval(timer);
  }, [deadline]);
  return Math.max(0, Math.ceil((deadline - Math.max(now, Date.now())) / 1000));
}
