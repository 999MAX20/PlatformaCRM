import { useEffect } from "react";
import { useLocation } from "react-router";

import { LoadingState } from "../components/ui/StateViews";

export function LandingHome() {
  const { search, hash } = useLocation();
  useEffect(() => {
    // Client-side navigation must leave the SPA to load the landing's own document.
    window.location.replace(`/landing/index.html${search}${hash}`);
  }, [search, hash]);
  return <LoadingState scope="page" />;
}
