import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Pencil } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { uploadAccountAvatar, removeAccountAvatar } from "../../api/auth";
import { getApiErrorMessage } from "../../api/client";
import { Button } from "../../components/ui/Button";
import { Modal } from "../../components/ui/Modal";
import { useI18n } from "../../lib/i18n";
import type { CurrentUser } from "../../types";
import { AvatarCropper, AVATAR_CROP_FRACTION } from "./AvatarCropper";
import { accountAvatarKey, useAccountAvatar, UserAvatar } from "./UserAvatar";

export function AvatarEditor({ user }: { user: CurrentUser | null }) {
  const { t } = useI18n();
  const input = useRef<HTMLInputElement>(null);
  const client = useQueryClient();
  const avatar = useAccountAvatar(user);
  const [open, setOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState("");
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });
  const [zoom, setZoom] = useState(1);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const [fileError, setFileError] = useState(false);
  useEffect(() => {
    if (!file) { setPreview(""); return; }
    const url = URL.createObjectURL(file);
    setPreview(url);
    return () => URL.revokeObjectURL(url);
  }, [file]);
  const side = AVATAR_CROP_FRACTION * Math.min(dimensions.width, dimensions.height) / zoom;
  const close = () => { if (!mutation.isPending) { setOpen(false); setFile(null); setFileError(false); } };
  const mutation = useMutation({
    mutationFn: (remove: boolean) => remove ? removeAccountAvatar() : uploadAccountAvatar(file!, {
      x: (dimensions.width - side) * (position.x + 1) / 2 / dimensions.width,
      y: (dimensions.height - side) * (position.y + 1) / 2 / dimensions.height,
      size: AVATAR_CROP_FRACTION / zoom,
    }),
    onSuccess: data => { client.setQueryData(accountAvatarKey(user?.id), data); setOpen(false); setFile(null); },
  });
  return <div className="flex items-center justify-center self-stretch">
    <button type="button" className="platforma-focus-ring relative rounded-full" aria-label={t("account.avatarChange")} onClick={() => { mutation.reset(); setFileError(false); setOpen(true); }}>
      <UserAvatar user={user} className="h-24 w-24 text-3xl" />
      <span className="absolute bottom-0 right-0 grid h-7 w-7 place-items-center rounded-full border-2 border-white bg-brand-500 text-white"><Pencil size={14} aria-hidden="true" /></span>
    </button>
    <Modal title={t("account.avatarChange")} open={open} onClose={close} size="sm">
      <div className="space-y-4">
        <input ref={input} type="file" accept="image/jpeg,image/png,image/webp" className="hidden" aria-label={t("account.avatarUpload")} disabled={mutation.isPending} onChange={event => {
          const selected = event.target.files?.[0]; event.target.value = "";
          if (!selected) return;
          if (selected.size > 5 * 1024 * 1024 || !["image/jpeg", "image/png", "image/webp"].includes(selected.type)) { setFileError(true); return; }
          setFileError(false); mutation.reset(); setDimensions({ width: 0, height: 0 }); setZoom(1); setPosition({ x: 0, y: 0 }); setFile(selected);
        }} />
        {preview ? <AvatarCropper src={preview} dimensions={dimensions} zoom={zoom} position={position} disabled={mutation.isPending}
          onPosition={setPosition} onLoad={image => {
            if (image.naturalWidth * image.naturalHeight > 16_000_000) { setFileError(true); setFile(null); return; }
            setDimensions({ width: image.naturalWidth, height: image.naturalHeight });
          }} onError={() => { setFileError(true); setFile(null); }} /> : <UserAvatar user={user} className="mx-auto h-32 w-32 text-4xl" />}
        {file && dimensions.width > 0 ? <label className="block text-sm">{t("account.avatarZoom")}<input disabled={mutation.isPending} className="block w-full accent-orange-500" type="range" min="1" max="3" step="0.01" value={zoom} onChange={event => setZoom(Number(event.target.value))} /></label> : null}
        {fileError ? <p role="alert" className="text-sm text-platforma-danger">{t("account.avatarInvalid")}</p> : null}
        {mutation.error || avatar.error ? <p role="alert" className="text-sm text-platforma-danger">{getApiErrorMessage(mutation.error || avatar.error)}</p> : null}
        <div className="flex flex-wrap justify-center gap-2">
          <Button size="sm" variant="secondary" disabled={mutation.isPending} onClick={() => input.current?.click()}>{t("account.avatarChoose")}</Button>
          {avatar.data?.image ? <Button size="sm" variant="ghost" disabled={mutation.isPending} onClick={() => mutation.mutate(true)}>{t("account.avatarRemove")}</Button> : null}
        </div>
        <div className="flex justify-end gap-2 border-t border-platforma-border pt-3">
          <Button variant="secondary" disabled={mutation.isPending} onClick={close}>{t("common.cancel")}</Button>
          <Button disabled={!file || dimensions.width === 0 || fileError} isLoading={mutation.isPending} onClick={() => mutation.mutate(false)}>{t("common.save")}</Button>
        </div>
      </div>
    </Modal>
  </div>;
}
