// Section paging for PageUp / PageDown only. The mouse wheel, trackpad, touch, arrow keys and space keep
// native scrolling (no scroll hijacking); CSS proximity snap gently aligns sections. Reduced motion jumps.
(() => {
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");

  function points() {
    const tops = [];
    document.querySelectorAll("main > section, footer.closing, body > footer").forEach((s) => {
      tops.push(Math.round(s.getBoundingClientRect().top + window.scrollY));
    });
    const max = document.documentElement.scrollHeight - window.innerHeight;
    return [...new Set(tops.map((t) => Math.min(t, max)))].sort((a, b) => a - b);
  }

  window.addEventListener("keydown", (e) => {
    if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
    if (e.key !== "PageDown" && e.key !== "PageUp") return;
    const el = document.activeElement;
    if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT|VIDEO)$/.test(el.tagName))) return;
    const y = window.scrollY;
    const list = points();
    const target = e.key === "PageDown" ? list.find((t) => t > y + 4) : [...list].reverse().find((t) => t < y - 4);
    if (target === undefined) return;
    e.preventDefault();
    window.scrollTo({ top: target, behavior: reduce.matches ? "auto" : "smooth" });
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
