import type { APIRequestContext } from "@playwright/test";

/** Exercise the real browser-auth contract, including cookie + CSRF bootstrap. */
export async function authPost(request: APIRequestContext, url: string, options: Parameters<APIRequestContext["post"]>[1] = {}) {
  const csrf = await request.get(url.replace(/\/api\/auth\/.*$/, "/api/auth/csrf/"));
  if (!csrf.ok()) throw new Error(`Authentication bootstrap failed (${csrf.status()})`);
  const { csrf_token: token } = await csrf.json();
  if (!token) throw new Error("Authentication bootstrap did not return a CSRF token");
  return request.post(url, { ...options, headers: {
    ...options.headers, Origin: new URL(csrf.url()).origin, "X-CSRFToken": token,
  } });
}
