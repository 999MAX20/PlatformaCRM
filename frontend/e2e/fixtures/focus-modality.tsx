import React, { useState } from "react";
import { createRoot } from "react-dom/client";
import "../../src/lib/focusModality";
import "../../src/styles.css";
import "../../widget/src/index";
import { I18nProvider } from "../../src/lib/i18n";
import { Button } from "../../src/components/ui/Button";
import { Input } from "../../src/components/ui/Input";
import { Modal } from "../../src/components/ui/Modal";
import { SearchableSelect } from "../../src/components/ui/SearchableSelect";
import { LanguageSelector } from "../../src/components/layout/LanguageSelector";

function Fixture() {
  const [open, setOpen] = useState(false);
  const [value, setValue] = useState("");
  return <main className="p-8">
    <Button id="open-dialog" onClick={() => setOpen(true)}>Open dialog</Button>
    <Modal title="Focus dialog" open={open} onClose={() => setOpen(false)} focusReturnId="open-dialog">
      <Input label="Dialog field" /><Button onClick={() => setOpen(false)}>Done</Button>
    </Modal>
    <SearchableSelect label="Search choice" value={value} onChange={setValue} options={[{ value: "a", label: "Alpha" }]} />
    <LanguageSelector />
  </main>;
}
createRoot(document.getElementById("root")!).render(<I18nProvider><Fixture /></I18nProvider>);
window.PlatformaCRMWidget?.init({ publicToken: "focus-fixture", apiUrl: "/api/widget-test" });
