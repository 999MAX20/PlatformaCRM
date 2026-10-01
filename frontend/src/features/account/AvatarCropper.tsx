import { useRef } from "react";
import { useI18n } from "../../lib/i18n";

type Position = { x: number; y: number };
export const AVATAR_CROP_FRACTION = 0.8;

export function AvatarCropper({ src, dimensions, zoom, position, disabled, onPosition, onLoad, onError }: {
  src: string;
  dimensions: { width: number; height: number };
  zoom: number;
  position: Position;
  disabled: boolean;
  onPosition: (position: Position) => void;
  onLoad: (image: HTMLImageElement) => void;
  onError: () => void;
}) {
  const { t } = useI18n();
  const drag = useRef<{ pointer: number; x: number; y: number; position: Position } | null>(null);
  const { width, height } = dimensions;
  const ready = width > 0 && height > 0;
  const minimum = Math.min(width, height);
  const side = AVATAR_CROP_FRACTION * minimum / zoom;
  const clamp = (value: number) => Math.max(-1, Math.min(1, value));
  const move = (dx: number, dy: number, bounds: DOMRect, start: Position) => {
    const scale = bounds.width / width * zoom;
    onPosition({
      x: clamp(start.x - 2 * dx / ((width - side) * scale)),
      y: clamp(start.y - 2 * dy / ((height - side) * scale)),
    });
  };
  return <div
    role="group" aria-label={t("account.avatarDrag")} tabIndex={disabled ? -1 : 0}
    className="platforma-focus-ring relative mx-auto touch-none select-none overflow-hidden rounded-lg bg-platforma-ink cursor-grab active:cursor-grabbing"
    data-testid="avatar-crop-preview"
    style={ready ? { aspectRatio: `${width} / ${height}`, width: `min(100%, ${320 * width / height}px)` } : { height: 240 }}
    onPointerDown={event => {
      if (disabled || !ready || (event.pointerType === "mouse" && event.button !== 0)) return;
      event.preventDefault(); event.currentTarget.focus();
      event.currentTarget.setPointerCapture(event.pointerId);
      drag.current = { pointer: event.pointerId, x: event.clientX, y: event.clientY, position };
    }}
    onPointerMove={event => {
      const start = drag.current;
      if (!start || disabled || event.pointerId !== start.pointer) return;
      move(event.clientX - start.x, event.clientY - start.y, event.currentTarget.getBoundingClientRect(), start.position);
    }}
    onPointerUp={() => { drag.current = null; }}
    onPointerCancel={() => { drag.current = null; }}
    onLostPointerCapture={() => { drag.current = null; }}
    onKeyDown={event => {
      if (disabled || !ready) return;
      const step = event.shiftKey ? 30 : 10;
      const movement: Record<string, [number, number]> = { ArrowLeft: [-step, 0], ArrowRight: [step, 0], ArrowUp: [0, -step], ArrowDown: [0, step] };
      if (!movement[event.key]) return;
      event.preventDefault();
      move(...movement[event.key], event.currentTarget.getBoundingClientRect(), position);
    }}
  >
    <img src={src} alt={t("account.avatarPreview")} draggable={false}
      onLoad={event => onLoad(event.currentTarget)} onError={onError}
      className="pointer-events-none absolute max-w-none"
      style={ready ? {
        width: `${zoom * 100}%`, height: `${zoom * 100}%`,
        left: `${50 - zoom * 50 - position.x * (width - side) / width * zoom * 50}%`,
        top: `${50 - zoom * 50 - position.y * (height - side) / height * zoom * 50}%`,
      } : { visibility: "hidden" }} />
    {ready ? <div aria-hidden="true" className="pointer-events-none absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-white"
      style={{ width: `${80 * minimum / width}%`, height: `${80 * minimum / height}%`, boxShadow: "0 0 0 100vmax rgb(0 0 0 / 55%)" }} /> : null}
  </div>;
}
