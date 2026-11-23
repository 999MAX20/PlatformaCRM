export function openDocumentPrintWindow(title: string, loading: string) {
  const target = window.open("", "_blank", "popup,width=900,height=800");
  if (!target) return null;
  target.opener = null;
  const page = target.document;
  page.title = title;
  const status = page.createElement("p");
  status.textContent = loading; status.setAttribute("role", "status");
  page.body.append(status);
  const urls: string[] = [];
  function cleanup() { for (const url of urls.splice(0)) URL.revokeObjectURL(url); }
  target.addEventListener("pagehide", cleanup, { once: true });
  return {
    close: () => { cleanup(); if (!target.closed) target.close(); },
    render: async (blob: Blob, signal: AbortSignal, printLabel: string) => {
      if (signal.aborted || target.closed) return;
      const { loadMedicalPdf } = await import("../files/MedicalPdfPreview");
      if (signal.aborted || target.closed) return;
      const task = loadMedicalPdf(new Uint8Array(await blob.arrayBuffer()));
      const abort = () => { void task.destroy().catch(() => {}); cleanup(); if (!target.closed) target.close(); };
      signal.addEventListener("abort", abort, { once: true });
      try {
        const pdf = await task.promise;
        if (pdf.numPages > 100) throw new Error("Document page limit exceeded");
        const style = page.createElement("style");
        style.textContent = "@page{size:A4;margin:0}body{margin:0;background:#fff}img{display:block;width:210mm;height:297mm;break-after:page}img:last-child{break-after:auto}button{margin:12px;padding:12px;font:16px sans-serif}@media screen{img{max-width:100%;height:auto}}@media print{button,[role=status]{display:none}}";
        page.head.append(style);
        const print = page.createElement("button");
        print.textContent = printLabel; print.disabled = true; print.onclick = () => target.print();
        page.body.append(print);
        for (let index = 1; index <= pdf.numPages; index++) {
          if (signal.aborted || target.closed) return;
          const sheet = await pdf.getPage(index);
          const viewport = sheet.getViewport({ scale: 1.5 });
          if (viewport.width * viewport.height > 8_000_000) throw new Error("Document page size exceeded");
          // PDF.js registers embedded fonts in this document, not in the print window.
          const canvas = document.createElement("canvas");
          canvas.width = Math.ceil(viewport.width); canvas.height = Math.ceil(viewport.height);
          await sheet.render({ canvas, viewport }).promise;
          const png = await new Promise<Blob>((resolve, reject) => canvas.toBlob(value => value ? resolve(value) : reject(new Error("Page unavailable")), "image/png"));
          canvas.width = canvas.height = 0;
          const url = URL.createObjectURL(png); urls.push(url);
          const image = page.createElement("img");
          image.alt = `${title} · ${index}`; image.src = url;
          page.body.append(image); await image.decode(); sheet.cleanup();
        }
        if (!signal.aborted && !target.closed) { status.remove(); print.disabled = false; target.focus(); target.print(); }
      } finally { signal.removeEventListener("abort", abort); await task.destroy(); }
    },
  };
}
