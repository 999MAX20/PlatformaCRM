import { useEffect, useRef, useState } from "react";
import { AnnotationMode, getDocument, GlobalWorkerOptions, type PDFDocumentProxy, type RenderTask } from "pdfjs-dist";
import workerUrl from "pdfjs-dist/build/pdf.worker.min.mjs?url";
import { Button } from "../../../components/ui/Button";
import { Select } from "../../../components/ui/Select";
import { ErrorState, LoadingState } from "../../../components/ui/StateViews";
import { useI18n } from "../../../lib/i18n";

GlobalWorkerOptions.workerSrc = workerUrl;
const assets = import.meta.glob<string>("/node_modules/pdfjs-dist/{cmaps,standard_fonts,wasm}/*", { eager: true, query: "?url", import: "default" });
class LocalPdfAssets {
  async fetch({ kind, filename }: { kind: string; filename: string }) {
    const folder = { cMapUrl: "cmaps", standardFontDataUrl: "standard_fonts", wasmUrl: "wasm" }[kind];
    const url = folder && assets[`/node_modules/pdfjs-dist/${folder}/${filename}`];
    if (!url) throw new Error("PDF asset unavailable");
    const response = await fetch(url, { credentials: "omit" });
    if (!response.ok) throw new Error("PDF asset unavailable");
    return new Uint8Array(await response.arrayBuffer());
  }
}

export function loadMedicalPdf(data: Uint8Array) {
  return getDocument({ data, BinaryDataFactory: LocalPdfAssets,
    useWorkerFetch: false, enableXfa: false, stopAtErrors: true, verbosity: 0 });
}

export default function MedicalPdfPreview({ blob, name, onRetry }: { blob: Blob; name: string; onRetry: () => void }) {
  const { t } = useI18n();
  const [document, setDocument] = useState<PDFDocumentProxy | null>(null);
  const [page, setPage] = useState(1);
  const [zoom, setZoom] = useState(1);
  const [width, setWidth] = useState(0);
  const [rendering, setRendering] = useState(true);
  const [error, setError] = useState(false);
  const [text, setText] = useState("");
  const host = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    if (!host.current) return;
    const observer = new ResizeObserver(entries => setWidth(Math.floor(entries[0].contentRect.width)));
    observer.observe(host.current); return () => observer.disconnect();
  }, []);
  useEffect(() => {
    let active = true;
    let task: ReturnType<typeof getDocument> | undefined;
    setDocument(null); setPage(1); setText(""); setError(false); setRendering(true);
    void blob.arrayBuffer().then(data => {
      if (!active) return;
      task = loadMedicalPdf(new Uint8Array(data));
      return task.promise.then(value => { if (active) setDocument(value); });
    }).catch(() => { if (active) { setError(true); setRendering(false); } });
    return () => { active = false; void task?.destroy().catch(() => {}); };
  }, [blob]);
  useEffect(() => {
    if (!document || !width || !canvas.current) return;
    let active = true;
    let task: RenderTask | undefined;
    const target = canvas.current;
    setRendering(true); setError(false); setText("");
    void document.getPage(page).then(async sheet => {
      if (!active) return;
      const natural = sheet.getViewport({ scale: 1 });
      const scale = Math.min(width / natural.width, 2) * zoom;
      const viewport = sheet.getViewport({ scale });
      const ratio = Math.min(window.devicePixelRatio || 1, 2, Math.sqrt(16_000_000 / (viewport.width * viewport.height)));
      target.width = Math.max(1, Math.floor(viewport.width * ratio)); target.height = Math.max(1, Math.floor(viewport.height * ratio));
      target.style.width = `${viewport.width}px`; target.style.height = `${viewport.height}px`;
      task = sheet.render({ canvas: target, viewport, transform: [ratio, 0, 0, ratio, 0, 0], annotationMode: AnnotationMode.ENABLE });
      await task.promise;
      const content = await sheet.getTextContent();
      if (active) { setText(content.items.map(item => "str" in item ? item.str : "").join(" ")); setRendering(false); }
    }).catch(() => { if (active) { setError(true); setRendering(false); } });
    return () => { active = false; task?.cancel(); target.width = 0; target.height = 0; };
  }, [document, page, zoom, width]);
  return <section ref={host} className="min-w-0 space-y-3" data-testid="medical-pdf-preview" aria-busy={rendering}>
    {document ? <div className="flex flex-wrap items-center gap-2">
      <Button size="lg" variant="secondary" disabled={page <= 1} onClick={() => setPage(value => value - 1)}>{t("pagination.previous")}</Button>
      <span className="text-sm" aria-live="polite">{t("medical.files.pdfPage", { page, count: document.numPages })}</span>
      <Button size="lg" variant="secondary" disabled={page >= document.numPages} onClick={() => setPage(value => value + 1)}>{t("pagination.next")}</Button>
      <Select label={t("medical.files.pdfZoom")} value={zoom} onChange={event => setZoom(Number(event.target.value))}
        options={[1, 1.5, 2, 3].map(value => ({ value, label: `${value * 100}%` }))} />
    </div> : null}
    {rendering ? <LoadingState /> : null}
    {error ? <ErrorState message={t("medical.files.pdfError")} action={<Button size="lg" variant="secondary" onClick={onRetry}>{t("common.retry")}</Button>} /> : null}
    <div className="max-h-[65dvh] overflow-auto" hidden={!document || error} tabIndex={0} aria-label={name}>
      <canvas key={`${page}-${zoom}-${width}`} ref={canvas} role="img" aria-label={name} />
    </div>
    <p className="sr-only" data-testid="medical-pdf-text">{text}</p>
  </section>;
}
