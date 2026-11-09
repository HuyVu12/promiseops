// One screen per scroll step on desktop: a wheel gesture or paging key moves to the next or
// previous section top (and the second half of two-screen sections). Touch devices keep native
// scrolling with CSS proximity snap. Reduced motion jumps instantly.
(() => {
  const desktop = window.matchMedia("(min-width: 1024px) and (min-height: 640px) and (pointer: fine)");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  let busy = false;

  function points() {
    const tops = [];
    document.querySelectorAll("main > section, footer.closing, body > footer").forEach((s) => {
      const top = Math.round(s.getBoundingClientRect().top + window.scrollY);
      tops.push(top);
      const screens = Math.round(s.offsetHeight / window.innerHeight);
      for (let i = 1; i < screens; i++) tops.push(top + i * window.innerHeight);
    });
    const max = document.documentElement.scrollHeight - window.innerHeight;
    return [...new Set(tops.map((t) => Math.min(t, max)))].sort((a, b) => a - b);
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
    if (!desktop.matches || e.altKey || e.ctrlKey || e.metaKey) return;
    const el = document.activeElement;
    if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT|VIDEO)$/.test(el.tagName))) return;
    const down = ["PageDown", "ArrowDown", " "].includes(e.key) && !e.shiftKey;
    const up = ["PageUp", "ArrowUp"].includes(e.key) || (e.key === " " && e.shiftKey);
    if (!down && !up) return;
    e.preventDefault();
    if (!busy) go(down ? 1 : -1);
  });
})();
