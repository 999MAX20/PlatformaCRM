export const refreshCookieName = process.env.AUTH_REFRESH_COOKIE_NAME || "zani_refresh";

if (process.env.ZANI_QUALITY_GATE === "1" && !refreshCookieName.startsWith("zani_test_refresh_")) {
  throw new Error("Isolated browser tests require the runtime refresh cookie namespace");
}
