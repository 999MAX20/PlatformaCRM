import { apiClient } from "./client";

export async function checkServiceConnection(signal: AbortSignal) {
  const response = await apiClient.get<{ status: string }>("/health/", { signal, timeout: 5_000 });
  if (response.data.status !== "ok") throw new Error("Unexpected health response");
}
