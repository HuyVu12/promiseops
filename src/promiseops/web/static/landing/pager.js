// Section paging on desktop: one wheel gesture glides to the next (or previous) screen with an eased
// animation, the trackpad's inertia tail is ignored so one flick never skips two sections, and the page is
// never pulled backwards (no CSS snap). Tall sections get one stop per screen. Touch devices, small
// windows and reduced motion keep native scrolling. PageUp/PageDown/Space use the same stops.
(() => {
  const desktop = window.matchMedia("(min-width: 1024px) and (min-height: 640px) and (pointer: fine)");
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)");
  const DURATION = 700;      // ms per section glide
  const QUIET = 180;         // ms without wheel events that ends a gesture (trackpad inertia included)
  const THRESHOLD = 24;      // accumulated deltaY that counts as an intent to move
  let animating = false, gestureOpen = false, quietTimer = 0, acc = 0;

  function points() {
    const tops = [];
    const vh = window.innerHeight;
    document.querySelectorAll("main > section, footer.closing, body > footer").forEach((s) => {
      const top = Math.round(s.getBoundingClientRect().top + window.scrollY);
      const bottomStop = top + s.offsetHeight - vh;   // a section taller than the screen also stops at its foot
      tops.push(top);
      for (let y = top + vh; y < bottomStop; y += vh) tops.push(y);
      if (bottomStop > top + 40) tops.push(bottomStop);
    });
    const max = document.documentElement.scrollHeight - vh;
    return [...new Set(tops.map((t) => Math.min(Math.max(t, 0), max)))].sort((a, b) => a - b);
  }

  const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);

  function glide(target) {
    const from = window.scrollY, dist = target - from;
    if (Math.abs(dist) < 2) return;
    if (reduce.matches) { window.scrollTo({ top: target, behavior: "instant" }); return; }
    animating = true;
    const html = document.documentElement, prev = html.style.scrollBehavior;
    html.style.scrollBehavior = "auto";          // per-frame scrollTo must not be smoothed again by CSS
    const t0 = performance.now();
    const step = (now) => {
      const k = Math.min(1, (now - t0) / DURATION);
      window.scrollTo(0, from + dist * ease(k));
      if (k < 1) requestAnimationFrame(step);
      else { html.style.scrollBehavior = prev; animating = false; }
    };
    requestAnimationFrame(step);
  }

  function go(dir) {
    const y = window.scrollY, list = points();
    const target = dir > 0 ? list.find((t) => t > y + 4) : [...list].reverse().find((t) => t < y - 4);
    if (target !== undefined) glide(target);
  }

  function inScrollable(el) {
    for (; el && el !== document.body; el = el.parentElement) {
      const o = getComputedStyle(el).overflowY;
      if ((o === "auto" || o === "scroll") && el.scrollHeight > el.clientHeight + 1) return true;
    }
    return false;
  }

  window.addEventListener("wheel", (e) => {
    if (!desktop.matches || reduce.matches || e.ctrlKey || Math.abs(e.deltaX) > Math.abs(e.deltaY)) return;
    if (inScrollable(e.target)) return;
    e.preventDefault();
    clearTimeout(quietTimer);
    quietTimer = setTimeout(() => { gestureOpen = false; acc = 0; }, QUIET);
    if (animating || gestureOpen) return;       // one move per gesture; the inertia tail is swallowed
    acc += e.deltaY;
    if (Math.abs(acc) >= THRESHOLD) { gestureOpen = true; go(acc > 0 ? 1 : -1); acc = 0; }
  }, { passive: false });

  window.addEventListener("keydown", (e) => {
    if (!desktop.matches || e.altKey || e.ctrlKey || e.metaKey) return;
    const el = document.activeElement;
    if (el && (el.isContentEditable || /^(INPUT|TEXTAREA|SELECT|VIDEO|BUTTON)$/.test(el.tagName))) return;
    const down = e.key === "PageDown" || (e.key === " " && !e.shiftKey);
    const up = e.key === "PageUp" || (e.key === " " && e.shiftKey);
    if (!down && !up) return;
    e.preventDefault();
    if (!animating) go(down ? 1 : -1);
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
