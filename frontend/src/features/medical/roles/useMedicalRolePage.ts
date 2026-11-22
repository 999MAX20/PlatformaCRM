import axios from "axios";
import { useEffect, useState } from "react";
import type { MedicalRolePage } from "../../../api/medicalRoles";

export function medicalRoleDenied(error: unknown) {
  return axios.isAxiosError(error) && [401, 403, 404].includes(error.response?.status ?? 0);
}

export function useMedicalRolePage<T extends { id: number }>(
  read: (after: number | undefined, signal: AbortSignal) => Promise<MedicalRolePage<T>>,
  onDenied: (error: unknown) => void,
) {
  const [rows, setRows] = useState<T[]>([]);
  const [after, setAfter] = useState<number>();
  const [next, setNext] = useState<number | null>(null);
  const [attempt, setAttempt] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<unknown>(null);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true); setError(null);
    void read(after, controller.signal).then(page => {
      if (controller.signal.aborted) return;
      setRows(previous => after === undefined ? page.results : [...previous, ...page.results.filter(row => !previous.some(old => old.id === row.id))]);
      setNext(page.next_after_id);
    }).catch(cause => {
      if (controller.signal.aborted) return;
      if (medicalRoleDenied(cause)) { setRows([]); setNext(null); onDenied(cause); }
      else setError(cause);
    }).finally(() => { if (!controller.signal.aborted) setLoading(false); });
    return () => controller.abort();
  }, [read, after, attempt, onDenied]);
  return { rows, next, loading, error, retry: () => setAttempt(value => value + 1),
    more: () => { if (next !== null && !loading && !error) setAfter(next); } };
}
