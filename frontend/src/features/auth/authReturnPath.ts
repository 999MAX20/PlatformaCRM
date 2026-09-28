import { isSafeInternalReturnPath } from "../../api/client";

type ReturnLocation = { pathname?: string; search?: string; hash?: string };

export function getAuthReturnPathFromState(state: unknown) {
  const candidate = (state as { from?: ReturnLocation & { from?: ReturnLocation } } | null)?.from;
  // Older MFA navigation wrapped the original state in a second `from` object.
  const from = candidate?.pathname ? candidate : candidate?.from;
  return from?.pathname ? `${from.pathname}${from.search ?? ""}${from.hash ?? ""}` : undefined;
}

export function getPostAuthReturnPath(isPlatformUser: boolean, intendedPath?: string) {
  const fallback = isPlatformUser ? "/platform" : "/app";
  if (!intendedPath) return fallback;
  if (intendedPath.startsWith("/invite/")) return intendedPath;
  if (!isSafeInternalReturnPath(intendedPath)) return fallback;
  if (isPlatformUser && !intendedPath.startsWith("/platform")) return fallback;
  if (!isPlatformUser && !intendedPath.startsWith("/app")) return fallback;
  return intendedPath;
}
