/** Shared by the app, component catalog and embedded widget. No focus is moved. */
const root = document.documentElement;
const navigationKeys = new Set(["Tab", "ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight", "Home", "End", "PageUp", "PageDown", "Escape"]);

// Absent attribute keeps native focus-visible behavior, including initial AT focus.
// The guard also avoids duplicate listeners when the widget shares the app document.
if (!root.hasAttribute("data-platforma-focus")) {
  root.setAttribute("data-platforma-focus", "keyboard");
  document.addEventListener("pointerdown", () => {
    root.setAttribute("data-platforma-focus", "pointer");
  }, true);
  document.addEventListener("keydown", event => {
    if (event.isComposing || event.metaKey || event.ctrlKey || event.altKey) return;
    const target = event.target;
    const editing = target instanceof HTMLElement &&
      (target.matches("input, textarea") || target.isContentEditable);
    // Typing/caret movement in a clicked field is not keyboard navigation.
    const compositeNavigation = target instanceof HTMLElement && target.getAttribute("role") === "combobox" && navigationKeys.has(event.key);
    if (event.key === "Tab" || event.key === "Escape" || compositeNavigation || (!editing && (navigationKeys.has(event.key) || event.key === "Enter" || event.key === " "))) {
      root.setAttribute("data-platforma-focus", "keyboard");
    }
  }, true);
}

export {};
