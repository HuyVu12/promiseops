// One screen per scroll step on desktop (a product requirement): a wheel notch, PageUp/PageDown,
// arrows or space move to the next or previous stop. Stops are each section's top, every further
// screen of a tall section, and the bottom of a section taller than the viewport, so nothing is
// skipped. Touch devices keep native scrolling with CSS proximity snap. Reduced motion jumps.
(() => {
  const desktop = window.matchMedia("(min-width: 1024px) and (min-height: 640px) and (pointer: fine)");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  let busy = false;

  function points() {
    const vh = window.innerHeight;
    const stops = [];
    document.querySelectorAll("main > section, footer.closing, body > footer").forEach((s) => {
      const top = Math.round(s.getBoundingClientRect().top + window.scrollY);
      const lastScreen = top + s.offsetHeight - vh;
      stops.push(top);
      for (let y = top + vh; y < lastScreen - 4; y += vh) stops.push(y);
      if (lastScreen > top + 4) stops.push(lastScreen);
    });
    const max = document.documentElement.scrollHeight - vh;
    return [...new Set(stops.map((t) => Math.min(Math.round(t), max)))].sort((a, b) => a - b);
  }

  function go(dir) {
    const y = window.scrollY;
    const list = points();
    const target = dir > 0 ? list.find((t) => t > y + 4) : [...list].reverse().find((t) => t < y - 4);
    if (target === undefined) return false;
    busy = true;
    window.scrollTo({ top: target, behavior: reduce.matches ? "auto" : "smooth" });
    window.setTimeout(() => { busy = false; }, reduce.matches ? 120 : 750);
    return true;
  }

  window.addEventListener("wheel", (e) => {
    if (!desktop.matches || e.ctrlKey || Math.abs(e.deltaY) < 4) return;
    e.preventDefault();
    if (!busy) go(e.deltaY > 0 ? 1 : -1);
  }, { passive: false });

  window.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey) return;
    const el = document.activeElement;
    if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT|VIDEO|BUTTON)$/.test(el.tagName))) return;
    const page = e.key === "PageDown" || e.key === "PageUp";
    if (!page && !desktop.matches) return;
    const down = e.key === "PageDown" || ((e.key === "ArrowDown" || e.key === " ") && !e.shiftKey);
    const up = e.key === "PageUp" || e.key === "ArrowUp" || (e.key === " " && e.shiftKey);
    if (!down && !up) return;
    e.preventDefault();
    if (!busy) go(down ? 1 : -1);
  });

  // The queue preview on the landing page: tabs filter the list, a case row opens the live demo.
  document.querySelectorAll("[data-preview]").forEach((frame) => {
    const tabs = frame.querySelectorAll(".pt-tab[data-view]");
    const rows = frame.querySelectorAll(".pt-list > li");
    tabs.forEach((tab) => tab.addEventListener("click", () => {
      tabs.forEach((t) => { const on = t === tab; t.classList.toggle("is-on", on); t.setAttribute("aria-selected", String(on)); });
      const mine = tab.dataset.view === "mine";
      rows.forEach((li) => { li.hidden = mine && li.dataset.owner !== "me"; });
    }));
    frame.querySelectorAll(".pt-click").forEach((li) => {
      const open = () => { window.location.href = "/app"; };
      li.addEventListener("click", open);
      li.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); open(); } });
    });
  });
})();
