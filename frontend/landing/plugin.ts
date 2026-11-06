import type { Connect, Plugin } from "vite";

const landingHome: Connect.NextHandleFunction = (request, _response, next) => {
  const [pathname, ...query] = (request.url ?? "").split("?");
  if (pathname === "/" || pathname === "/index.html") {
    request.url = `/landing/index.html${query.length ? `?${query.join("?")}` : ""}`;
  }
  next();
};

/** Keep the public HTML outside the authenticated React application's CSS and providers. */
export function crmLanding(): Plugin {
  return {
    name: "crm-public-landing",
    configureServer(server) {
      server.middlewares.use(landingHome);
    },
    configurePreviewServer(server) {
      server.middlewares.use(landingHome);
    },
  };
}
