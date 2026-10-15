import axios from "axios";

export const SERVICE_AVAILABLE_EVENT = "platforma:service-available";

// Public readiness must not depend on access-token refresh or session identity.
const connectivityClient = axios.create({ baseURL: import.meta.env.VITE_API_URL || "", timeout: 5_000 });

export async function checkServiceConnection(signal: AbortSignal) {
  const response = await connectivityClient.get<{ status: string }>("/ready/", { signal });
  if (response.data.status !== "ok") throw new Error("Unexpected health response");
}
