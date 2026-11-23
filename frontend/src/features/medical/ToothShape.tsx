export function ToothShape({ tooth }: { tooth: number }) {
  const position = tooth % 10;
  const quadrant = Math.floor(tooth / 10);
  const primary = quadrant > 4;
  const lower = [3, 4, 7, 8].includes(quadrant);
  const molar = position >= (primary ? 4 : 6);
  const premolar = !primary && position >= 4 && position <= 5;
  const canine = position === 3;
  const crown = molar
    ? "M9 39 C5 34 5 23 10 19 C14 15 19 19 24 17 C29 15 36 15 39 21 C43 28 41 35 38 39 C30 43 17 43 9 39Z"
    : premolar
      ? "M14 39 C9 34 10 23 15 19 C19 16 22 19 25 17 C30 15 35 21 35 29 C36 35 32 39 29 41Z"
      : canine
        ? "M15 40 C11 35 12 27 16 22 L24 16 L32 23 C36 29 34 36 31 40Z"
        : "M14 40 C11 34 12 24 14 19 Q24 16 34 19 C36 25 36 34 32 40Z";
  const roots = molar
    ? "M10 39 C11 48 8 61 12 68 C16 73 18 52 23 48 C28 51 29 72 34 69 C39 63 36 49 38 39"
    : premolar
      ? "M14 39 C16 49 13 65 19 70 C23 71 24 52 26 49 C29 55 27 66 31 66 C35 62 31 47 31 40"
      : "M15 39 C16 52 19 68 24 73 C29 68 32 53 32 39";
  return <svg viewBox="0 0 48 88" width="48" height="88" aria-hidden="true" focusable="false" className="h-24 w-10 shrink-0">
    <g transform={lower ? undefined : "translate(0 88) scale(1 -1)"} stroke="currentColor" strokeWidth="1.5" strokeLinejoin="round" strokeLinecap="round">
      <path d={roots} className="fill-surface-card" />
      <path d={crown} className="fill-surface-card" />
      <path d={molar ? "M13 26 Q20 29 24 23 Q26 29 36 27 M24 23 L23 36 M16 35 Q22 32 31 36" : premolar ? "M16 26 Q24 31 30 25 M24 29 L24 36" : "M18 23 Q24 21 30 23"} fill="none" opacity="0.55" />
    </g>
  </svg>;
}
