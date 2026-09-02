/* DysNet demo — behaviours ported from the HDS website:
   ⌘K site search, "On this page" contents, back-to-top. No trackers, no cookies. */
(function () {
  "use strict";

  /* Path prefix when served from a GitHub Pages project URL; "" on www.dysnet.org. */
  var BASE = window.SITE_BASE || "";

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
      fetch(BASE + "/search-index.json")
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
      return '<li><a href="' + BASE + h.url + '"><strong>' + h.title + "</strong><span>" + h.desc + "</span></a></li>";
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

/* ── Landing map: registry participants, region-aware views ─────────
   Self-hosted SVG (Natural Earth data). Region is guessed from the device
   time zone only; nothing is sent anywhere. */
(function () {
  var host = document.getElementById("worldmap");
  var data = window.DYSNET_MAP;
  if (!host || !data) return;
  var base = window.SITE_BASE || "";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var REGIONS = {
    world: null,
    europe: [-25, 34, 45, 72],
    americas: [-170, -57, -30, 75],
    asiapacific: [60, -50, 180, 55],
    africa: [-20, -37, 62, 42]
  };
  function orgName(o) { return Array.isArray(o) ? o[0] : o; }
  function orgUrl(o) { return Array.isArray(o) && o[1] ? o[1] : null; }
  var LABELS = { world: "World", europe: "Europe", americas: "Americas", asiapacific: "Asia-Pacific", africa: "Africa & Middle East" };

  function guessRegion() {
    var tz = "";
    try { tz = Intl.DateTimeFormat().resolvedOptions().timeZone || ""; } catch (e) {}
    if (/^(Europe|Atlantic)\//.test(tz)) return "europe";
    if (/^America\//.test(tz)) return "americas";
    if (/^(Australia|Pacific)\//.test(tz)) return "asiapacific";
    if (/^Africa\//.test(tz) || /^Asia\/(Riyadh|Dubai|Tehran|Jerusalem|Beirut|Amman|Baghdad|Kuwait|Qatar|Bahrain|Muscat|Damascus)$/.test(tz)) return "africa";
    if (/^Asia\//.test(tz)) return "asiapacific";
    return "world";
  }

  fetch(base + "/assets/map/world.svg").then(function (r) { return r.text(); }).then(function (svgText) {
    host.innerHTML = svgText;
    var svg = host.querySelector("svg");
    var proj = JSON.parse(svg.getAttribute("data-proj"));
    var full = [0, 0, proj.width, proj.height];

    function project(lon, lat) {
      var l = lon * Math.PI / 180, p = lat * Math.PI / 180, p2 = p * p, p4 = p2 * p2;
      var x = l * (0.8707 - 0.131979 * p2 + p4 * (-0.013791 + p4 * (0.003971 * p2 - 0.001529 * p4)));
      var y = -(p * (1.007226 + p2 * (0.015085 + p4 * (-0.044475 + 0.028874 * p2 - 0.005916 * p4))));
      return [(x - proj.minx) * proj.scale, (y - proj.miny) * proj.scale];
    }
    function regionBox(b) {
      if (!b) return full;
      var xs = [], ys = [];
      for (var i = 0; i <= 8; i++) {
        var lon = b[0] + (b[2] - b[0]) * i / 8, lat = b[1] + (b[3] - b[1]) * i / 8;
        [project(lon, b[1]), project(lon, b[3]), project(b[0], lat), project(b[2], lat)].forEach(function (pt) { xs.push(pt[0]); ys.push(pt[1]); });
      }
      var minx = Math.min.apply(null, xs), maxx = Math.max.apply(null, xs), miny = Math.min.apply(null, ys), maxy = Math.max.apply(null, ys);
      var pad = 0.04 * (maxx - minx);
      // keep the hero's aspect ratio so the region fills the frame
      var w = maxx - minx + 2 * pad, h = maxy - miny + 2 * pad;
      var ar = host.clientWidth / Math.max(host.clientHeight, 1);
      if (w / h < ar) { var nw = h * ar; minx -= (nw - w) / 2; w = nw; } else { var nh = w / ar; miny -= (nh - h) / 2; h = nh; }
      return [minx - pad, miny - pad, w, h];
    }

    // colour countries + accessibility
    var counts = { member: 0, candidate: 0, contact: 0, orgs: 0 };
    Object.keys(data.countries).forEach(function (id) {
      var c = data.countries[id], el = svg.querySelector("#c" + id);
      if (!el) return;
      el.classList.add("st-" + c.status);
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "button");
      el.setAttribute("aria-label", c.name + ": " + data.labels[c.status] + ", " + c.orgs.map(orgName).join(", "));
      counts[c.status]++; counts.orgs += c.orgs.length;
    });
    document.querySelectorAll("[data-count]").forEach(function (el) {
      var k = el.getAttribute("data-count");
      el.textContent = k === "countries" ? counts.member + counts.candidate : counts[k];
    });

    // office markers
    var g = document.createElementNS("http://www.w3.org/2000/svg", "g");
    g.setAttribute("class", "office");
    data.offices.forEach(function (o) {
      var pt = project(o.lon, o.lat);
      var c = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      c.setAttribute("cx", pt[0]); c.setAttribute("cy", pt[1]); c.setAttribute("r", "2.2");
      var t = document.createElementNS("http://www.w3.org/2000/svg", "text");
      t.setAttribute("x", pt[0] + 3.5); t.setAttribute("y", pt[1] + 1.8); t.textContent = o.name;
      g.appendChild(c); g.appendChild(t);
    });
    svg.appendChild(g);

    // tooltip
    var tip = document.querySelector(".map-tip");
    function showTip(el, x, y) {
      var id = el.id.slice(1), c = data.countries[id];
      if (!c) return;
      tip.innerHTML = "<strong>" + c.name + "</strong><span class=\"status\">" + data.labels[c.status] + "</span><ul>" +
        c.orgs.map(function (o) { var u = orgUrl(o); return "<li>" + (u ? "<a href=\"" + u + "\" target=\"_blank\" rel=\"noopener external\">" + orgName(o) + "</a>" : orgName(o)) + "</li>"; }).join("") + "</ul>";
      tip.style.display = "block";
      var r = host.getBoundingClientRect();
      var left = Math.min(x - r.left + 14, r.width - tip.offsetWidth - 12), top = Math.min(y - r.top + 14, r.height - tip.offsetHeight - 12);
      tip.style.left = Math.max(12, left) + "px"; tip.style.top = Math.max(12, top) + "px";
    }
    var hideTimer = null;
    function hideSoon() { clearTimeout(hideTimer); hideTimer = setTimeout(function () { tip.style.display = "none"; }, 350); }
    svg.addEventListener("mousemove", function (e) {
      var el = e.target.closest ? e.target.closest("path[class*='st-']") : null;
      if (el) { clearTimeout(hideTimer); showTip(el, e.clientX, e.clientY); } else hideSoon();
    });
    svg.addEventListener("mouseleave", hideSoon);
    tip.addEventListener("mouseenter", function () { clearTimeout(hideTimer); });
    tip.addEventListener("mouseleave", hideSoon);
    svg.addEventListener("focusin", function (e) {
      var el = e.target; if (!el.classList || !/st-/.test(el.className.baseVal || "")) return;
      var b = el.getBoundingClientRect(); showTip(el, b.left + b.width / 2, b.top + b.height / 2);
    });
    svg.addEventListener("focusout", function () { tip.style.display = "none"; });

    // region views
    var current = full.slice();
    function setView(box) {
      if (reduce) { svg.setAttribute("viewBox", box.join(" ")); current = box; return; }
      var from = current.slice(), start = null;
      function step(ts) {
        if (!start) start = ts;
        var t = Math.min(1, (ts - start) / 650); t = 1 - Math.pow(1 - t, 3);
        var v = from.map(function (a, i) { return a + (box[i] - a) * t; });
        svg.setAttribute("viewBox", v.join(" "));
        if (t < 1) requestAnimationFrame(step); else current = box;
      }
      requestAnimationFrame(step);
    }
    var chips = document.querySelectorAll(".map-views button");
    function choose(key, guessed) {
      chips.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-view") === key ? "true" : "false"); });
      setView(regionBox(REGIONS[key]));
      var g = document.querySelector(".map-guess");
      if (g) g.textContent = guessed ? "Showing " + LABELS[key] + ", guessed from your device’s time zone. Nothing is sent." : "Showing " + LABELS[key] + ".";
    }
    chips.forEach(function (b) { b.addEventListener("click", function () { choose(b.getAttribute("data-view"), false); }); });
    var first = guessRegion();
    svg.setAttribute("viewBox", full.join(" "));
    setTimeout(function () { choose(first, first !== "world"); }, 350);
    window.addEventListener("resize", function () {
      var k = document.querySelector('.map-views button[aria-pressed="true"]');
      if (k) { current = regionBox(REGIONS[k.getAttribute("data-view")]); svg.setAttribute("viewBox", current.join(" ")); }
    });
  });
})();
