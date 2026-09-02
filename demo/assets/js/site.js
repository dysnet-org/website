/* DysNet demo — behaviours ported from the HDS website:
   ⌘K site search, "On this page" contents, back-to-top. No trackers, no cookies. */
(function () {
  "use strict";

  /* ── Site search (HDS Search.astro pattern, simplified) ─────────── */
  var overlay = document.getElementById("search-overlay");
  var trigger = document.getElementById("search-btn");
  var index = null;

  function openSearch() {
    if (!overlay) return;
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
    var input = overlay.querySelector("input");
    input.value = "";
    render([]);
    input.focus();
    if (!index) {
      fetch("/search-index.json")
        .then(function (r) { return r.json(); })
        .then(function (d) { index = d; });
    }
  }
  function closeSearch() {
    if (!overlay) return;
    overlay.hidden = true;
    document.body.style.overflow = "";
    if (trigger) trigger.focus();
  }
  function render(hits) {
    var list = overlay.querySelector(".search-results");
    if (!hits.length) {
      list.innerHTML = '<li class="search-empty">Type to search the site — pages, registers, conditions.</li>';
      return;
    }
    list.innerHTML = hits.slice(0, 8).map(function (h) {
      return '<li><a href="' + h.url + '"><strong>' + h.title + "</strong><span>" + h.desc + "</span></a></li>";
    }).join("");
  }
  function search(q) {
    if (!index || !q.trim()) { render([]); return; }
    q = q.trim().toLowerCase();
    var hits = index.filter(function (p) {
      return (p.title + " " + p.desc + " " + (p.keywords || "")).toLowerCase().indexOf(q) !== -1;
    });
    var list = overlay.querySelector(".search-results");
    if (!hits.length) {
      list.innerHTML = '<li class="search-empty">No results for “' + q.replace(/[<>&]/g, "") + '”.</li>';
      return;
    }
    render(hits);
  }
  if (trigger && overlay) {
    trigger.addEventListener("click", openSearch);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) closeSearch(); });
    overlay.querySelector(".search-close").addEventListener("click", closeSearch);
    overlay.querySelector("input").addEventListener("input", function (e) { search(e.target.value); });
    document.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openSearch(); }
      if (e.key === "Escape" && !overlay.hidden) closeSearch();
    });
  }

  /* ── "On this page" contents (HDS TableOfContents pattern) ──────── */
  var main = document.getElementById("main");
  if (main) {
    var heads = Array.prototype.slice.call(main.querySelectorAll("h2"));
    if (heads.length >= 3) {
      var box = document.createElement("nav");
      box.className = "onpage";
      box.setAttribute("aria-label", "On this page");
      var items = heads.map(function (h, i) {
        if (!h.id) h.id = "s-" + (i + 1) + "-" + h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 40);
        return '<li><a href="#' + h.id + '">' + h.textContent + "</a></li>";
      }).join("");
      box.innerHTML = "<p>On this page</p><ul>" + items + "</ul>";
      heads[0].parentNode.insertBefore(box, heads[0].closest("div") === heads[0].parentNode ? heads[0].previousElementSibling || heads[0] : heads[0]);
    }
  }

  /* ── Back to top (HDS global.css pattern) ────────────────────────── */
  var btt = document.createElement("button");
  btt.className = "back-to-top";
  btt.setAttribute("aria-label", "Back to top");
  btt.innerHTML = "↑";
  btt.hidden = true;
  document.body.appendChild(btt);
  btt.addEventListener("click", function () { window.scrollTo({ top: 0, behavior: "smooth" }); });
  window.addEventListener("scroll", function () { btt.hidden = window.scrollY < 600; }, { passive: true });
})();

/* ── Donate widget (demo interactions) ─────────────────────────────── */
(function () {
  var box = document.getElementById("donate");
  if (!box) return;
  box.querySelectorAll(".freq button, .amounts button").forEach(function (b) {
    b.addEventListener("click", function () {
      var group = b.closest(".freq, .amounts");
      group.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
      b.setAttribute("aria-pressed", "true");
    });
  });
  var toggle = document.getElementById("bank-toggle");
  var details = document.getElementById("bank-details");
  toggle.addEventListener("click", function () {
    details.classList.toggle("open");
    toggle.textContent = details.classList.contains("open") ? "Bank details below ↓" : "Give by bank transfer";
  });
})();

/* ── Condition finder (Understanding dysmelia) ─────────────────────── */
(function () {
  var finder = document.getElementById("cond-finder");
  var grid = document.getElementById("cond-grid");
  if (!finder || !grid) return;
  var cards = Array.prototype.slice.call(grid.querySelectorAll(".card"));
  var state = { limbs: "", type: "", other: "", genetic: "" };

  function apply() {
    var n = 0;
    cards.forEach(function (c) {
      var ok = true;
      Object.keys(state).forEach(function (q) {
        var v = state[q];
        if (v && (c.getAttribute("data-" + q) || "").split(" ").indexOf(v) === -1) ok = false;
      });
      c.style.display = ok ? "" : "none";
      if (ok) n++;
    });
    document.getElementById("finder-n").textContent = n;
  }

  finder.querySelectorAll(".finder-chips").forEach(function (group) {
    var q = group.getAttribute("data-q");
    group.querySelectorAll("button").forEach(function (b) {
      b.addEventListener("click", function () {
        group.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
        b.setAttribute("aria-pressed", "true");
        state[q] = b.getAttribute("data-v");
        apply();
      });
    });
  });

  document.getElementById("finder-reset").addEventListener("click", function () {
    state = { limbs: "", type: "", other: "", genetic: "" };
    finder.querySelectorAll(".finder-chips").forEach(function (group) {
      group.querySelectorAll("button").forEach(function (x, i) { x.setAttribute("aria-pressed", i === 0 ? "true" : "false"); });
    });
    apply();
  });
})();

/* ── Click-to-play YouTube facade ──────────────────────────────────── */
(function () {
  document.querySelectorAll(".yt-embed").forEach(function (box) {
    function play() {
      var id = box.getAttribute("data-yt");
      var iframe = document.createElement("iframe");
      iframe.src = "https://www.youtube-nocookie.com/embed/" + id + "?autoplay=1&rel=0";
      iframe.title = box.getAttribute("data-title") || "Video";
      iframe.allow = "accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture";
      iframe.allowFullscreen = true;
      box.innerHTML = "";
      box.appendChild(iframe);
      box.style.cursor = "default";
    }
    box.querySelector("button").addEventListener("click", play);
    box.addEventListener("click", function (e) { if (e.target.tagName !== "IFRAME" && box.querySelector("button")) play(); });
  });
})();
