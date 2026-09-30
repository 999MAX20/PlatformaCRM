import { useQuery } from "@tanstack/react-query";
import { getAccountAvatar } from "../../api/auth";
import { cn } from "../../lib/cn";
import type { CurrentUser } from "../../types";

export const accountAvatarKey = (userId?: string | number) => ["account-avatar", userId];

export function useAccountAvatar(user: CurrentUser | null) {
  return useQuery({ queryKey: accountAvatarKey(user?.id), queryFn: getAccountAvatar, enabled: Boolean(user), staleTime: 60_000, retry: false });
}

export function UserAvatar({ user, className }: { user: CurrentUser | null; className?: string }) {
  const avatar = useAccountAvatar(user);
  const name = user?.full_name?.trim() || user?.email || "";
  const parts = name.split(/\s+/).filter(Boolean);
  const initials = parts.length > 1 ? `${parts[0][0]}${parts[parts.length - 1][0]}` : name.slice(0, 2);
  return <span className={cn("grid shrink-0 place-items-center overflow-hidden rounded-full bg-brand-100 font-semibold text-brand-800 ring-1 ring-brand-200/70", className)}>
    {avatar.data?.image ? <img src={avatar.data.image} alt="" className="h-full w-full object-cover" /> : <span aria-hidden="true">{initials.toUpperCase()}</span>}
  </span>;
}
