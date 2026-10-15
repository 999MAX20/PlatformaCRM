import { createContext, useContext, useLayoutEffect, type ReactNode } from "react";
import { useLocation } from "react-router";

export type PlatformHeading = { path: string; title: string };
export const PlatformHeadingContext = createContext<((value: PlatformHeading | null) => void) | null>(null);

/** Mount only with accessible entity data; unmount on loading/denial clears metadata. */
export function PlatformPageHeading({ title, actions, subject }: { title: string; actions?: ReactNode; subject?: string }) {
  const setHeading = useContext(PlatformHeadingContext);
  const { pathname } = useLocation();
  useLayoutEffect(() => {
    setHeading?.({ path: pathname, title });
    return () => setHeading?.(null);
  }, [pathname, title, setHeading]);
  if (!actions && !subject) return null;
  return <div className="flex flex-wrap items-center justify-between gap-3">
    {subject && <h2 className="min-w-0 break-words text-lg font-semibold">{subject}</h2>}
    {actions && <div className="ml-auto flex flex-wrap items-center gap-2">{actions}</div>}
  </div>;
}
