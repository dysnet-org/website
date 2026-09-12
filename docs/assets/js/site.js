/* DysNet demo — behaviours ported from the HDS website:
   ⌘K site search, "On this page" contents, back-to-top. No trackers, no cookies. */
(function () {
  "use strict";

  /* Path prefix when served from a GitHub Pages project URL; "" on www.dysnet.org. */
  var BASE = window.SITE_BASE || "";

  /* ── Site search (HDS Search.astro pattern, simplified) ─────────── */
  var overlay = document.getElementById("search-overlay");
  var trigger = document.getElementById("search-btn");
  var qParam = new URLSearchParams(location.search).get("q");
  if (qParam) setTimeout(function () { openSearch(qParam); }, 300);
  var index = null;

  function openSearch(preset) {
    if (!overlay) return;
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
    var input = overlay.querySelector("input");
    input.value = preset || "";
    render([]);
    input.focus();
    if (preset) setTimeout(function () { input.dispatchEvent(new Event("input", { bubbles: true })); }, 50);
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
  if (!host || !data || window.DYSNET_GL_ACTIVE) return;  // WebGL map took over (map-gl.js)
  // SVG fallback is in use: the estimated-people dots need WebGL, so explain instead of showing an empty legend entry
  var dotLegend = document.querySelector(".map-legend .l-dot");
  if (dotLegend) dotLegend.innerHTML = "Grey dots (estimated people living with a limb difference) need WebGL, which this browser has turned off.";
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

    // registry coverage zones (register 2): drawn from the same GeoJSON as the WebGL map, behind the markers
    var gz = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gz.setAttribute("class", "zones");
    svg.appendChild(gz);
    fetch(base + data.zonesUrl).then(function (r) { return r.json(); }).then(function (gj) {
      gj.features.forEach(function (f) {
        var d = "";
        (f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [f.geometry.coordinates]).forEach(function (poly) {
          poly.forEach(function (ring) { d += "M" + ring.map(function (c) { var q = project(c[0], c[1]); return q[0].toFixed(2) + "," + q[1].toFixed(2); }).join("L") + "Z"; });
        });
        var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d); path.setAttribute("class", "zone zone-" + f.properties.status);
        path.setAttribute("data-label", f.properties.label + " · " + f.properties.dep_name + (f.properties.status === "in_progress" ? " · starting to cover" : " · covered"));
        gz.appendChild(path);
      });
    }).catch(function () {});

    // care centres (register 4): orange markers linking to the centre's website
    var gc = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gc.setAttribute("class", "centre");
    (data.centres || []).forEach(function (c) {
      if (!c.lat || !c.lon) return;
      var pt = project(c.lon, c.lat);
      var a = document.createElementNS("http://www.w3.org/2000/svg", "a");
      if (c.url) { a.setAttribute("href", c.url); a.setAttribute("target", "_blank"); a.setAttribute("rel", "noopener external"); }
      var ci = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      ci.setAttribute("cx", pt[0]); ci.setAttribute("cy", pt[1]); ci.setAttribute("r", "2.6");
      var ti = document.createElementNS("http://www.w3.org/2000/svg", "title");
      ti.textContent = c.name + " · " + c.city + ", " + c.country + " · " + c.type;
      a.appendChild(ti); a.appendChild(ci); gc.appendChild(a);
    });
    svg.appendChild(gc);

    // research teams (register 3): blue markers, title tooltip, link to the register
    var gt = document.createElementNS("http://www.w3.org/2000/svg", "g");
    gt.setAttribute("class", "team");
    (data.teams || []).forEach(function (tm) {
      if (!tm.lat || !tm.lon) return;
      var pt = project(tm.lon, tm.lat);
      var a = document.createElementNS("http://www.w3.org/2000/svg", "a");
      a.setAttribute("href", (window.SITE_BASE || "") + "/knowledge/researchers/");
      var ci = document.createElementNS("http://www.w3.org/2000/svg", "circle");
      ci.setAttribute("cx", pt[0]); ci.setAttribute("cy", pt[1]); ci.setAttribute("r", String(2 + Math.min(2, tm.papers / 4)));
      var ti = document.createElementNS("http://www.w3.org/2000/svg", "title");
      ti.textContent = tm.name + " · " + tm.country + " · " + tm.papers + " publications";
      a.appendChild(ti); a.appendChild(ci); gt.appendChild(a);
    });
    svg.appendChild(gt);

    // layer filter (SVG edition): countries, centres, teams, offices; dots and city names need WebGL
    document.querySelectorAll("#map-layers button").forEach(function (b) {
      var key = b.getAttribute("data-layer");
      if (key === "people" || key === "cities") { b.disabled = true; b.title = "Needs WebGL"; return; }
      b.addEventListener("click", function () {
        var on = b.getAttribute("aria-pressed") !== "true";
        b.setAttribute("aria-pressed", on ? "true" : "false");
        if (key === "members") host.classList.toggle("nofill", !on);
        else { var grp = svg.querySelector("g." + { centres: "centre", teams: "team", offices: "office", zones: "zones" }[key]); if (grp) grp.style.display = on ? "" : "none"; }
        document.querySelectorAll('.map-legend [data-layer="' + key + '"]').forEach(function (el) { el.classList.toggle("off", !on); });
      });
    });

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
    var hideTimer = null, pinned = null;
    function hideSoon() { if (pinned) return; clearTimeout(hideTimer); hideTimer = setTimeout(function () { tip.style.display = "none"; }, 350); }
    // markers (care centres, research teams): hover shows the card, click pins it
    function markerTip(a, x, y) {
      var title = a.querySelector("title") ? a.querySelector("title").textContent : "";
      var parts = title.split(" · "), href = a.getAttribute("href");
      tip.innerHTML = "<strong>" + parts[0] + "</strong><span class=\"status\">" + (a.parentNode.classList.contains("team") ? "Research team" : "Care centre") + "</span><p style=\"margin:0.3rem 0 0\">" + parts.slice(1).join(" · ") + "</p>" +
        (href ? "<p style=\"margin:0.3rem 0 0\"><a href=\"" + href + "\"" + (/^https?:/.test(href) ? " target=\"_blank\" rel=\"noopener external\"" : "") + ">" + (a.parentNode.classList.contains("team") ? "Researchers register" : "Website ↗") + "</a></p>" : "");
      tip.style.display = "block";
      var r = host.getBoundingClientRect();
      var left = Math.min(x - r.left + 14, r.width - tip.offsetWidth - 12), top = Math.min(y - r.top + 14, r.height - tip.offsetHeight - 12);
      tip.style.left = Math.max(12, left) + "px"; tip.style.top = Math.max(12, top) + "px";
    }
    svg.addEventListener("mousemove", function (e) {
      if (pinned) return;
      var a = e.target.closest ? e.target.closest("g.centre a, g.team a") : null;
      if (a) { clearTimeout(hideTimer); markerTip(a, e.clientX, e.clientY); return; }
      var zone = e.target.closest ? e.target.closest("path.zone") : null;
      if (zone) { clearTimeout(hideTimer); tip.innerHTML = "<strong>" + zone.getAttribute("data-label").split(" · ")[0] + "</strong><span class=\"status\">Registry coverage</span><p style=\"margin:0.3rem 0 0\">" + zone.getAttribute("data-label").split(" · ").slice(1).join(" · ") + "</p>"; tip.style.display = "block"; var rz = host.getBoundingClientRect(); tip.style.left = Math.max(12, Math.min(e.clientX - rz.left + 14, rz.width - tip.offsetWidth - 12)) + "px"; tip.style.top = Math.max(12, Math.min(e.clientY - rz.top + 14, rz.height - tip.offsetHeight - 12)) + "px"; return; }
      var el = e.target.closest ? e.target.closest("path[class*='st-']") : null;
      if (el) { clearTimeout(hideTimer); showTip(el, e.clientX, e.clientY); } else hideSoon();
    });
    svg.addEventListener("click", function (e) {
      var a = e.target.closest ? e.target.closest("g.centre a, g.team a") : null;
      if (a) { e.preventDefault(); clearTimeout(hideTimer); pinned = a; markerTip(a, e.clientX, e.clientY); return; }
      if (pinned) { pinned = null; tip.style.display = "none"; }
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

/* ── Landing map card: close after reading, reopen on demand ────────── */
(function () {
  var panel = document.getElementById("map-panel");
  var reopen = document.getElementById("map-panel-reopen");
  if (!panel || !reopen) return;
  var close = panel.querySelector(".map-panel-close");
  function setOpen(open) {
    panel.hidden = !open; reopen.hidden = open;
    try { sessionStorage.setItem("dysnet-map-card", open ? "open" : "closed"); } catch (e) {}
  }
  close.addEventListener("click", function () { setOpen(false); reopen.focus(); });
  reopen.addEventListener("click", function () { setOpen(true); close.focus(); });
  try { if (sessionStorage.getItem("dysnet-map-card") === "closed") setOpen(false); } catch (e) {}
})();

/* ── Phone menu and map options ────────────────────────────────────── */
(function () {
  var tog = document.getElementById("nav-toggle"), header = document.querySelector("header.site");
  if (tog && header) tog.addEventListener("click", function () {
    var open = !header.classList.contains("nav-open");
    header.classList.toggle("nav-open", open); tog.setAttribute("aria-expanded", open ? "true" : "false"); tog.textContent = open ? "Close" : "Menu";
  });
  var mo = document.getElementById("map-options-toggle"), side = document.getElementById("map-side");
  if (mo && side) mo.addEventListener("click", function () {
    var open = !side.classList.contains("open");
    side.classList.toggle("open", open); mo.setAttribute("aria-expanded", open ? "true" : "false"); mo.textContent = open ? "Hide map options" : "Map options";
  });
})();

/* ── Landing map legend: collapsed to a button on wide screens ─────── */
(function () {
  var legend = document.getElementById("map-legend"), btn = document.getElementById("map-legend-toggle");
  if (!legend || !btn) return;
  function set(open) { legend.classList.toggle("open", open); btn.setAttribute("aria-expanded", open ? "true" : "false"); btn.textContent = open ? "Hide legend" : "Legend"; }
  btn.addEventListener("click", function () { set(!legend.classList.contains("open")); });
  set(false);
})();

/* ── Bibliography: search + filters ────────────────────────────────── */
(function () {
  var list = document.getElementById("bib-list"), q = document.getElementById("bib-q"), sel = document.getElementById("bib-code"), chips = document.getElementById("bib-topics"), n = document.getElementById("bib-n");
  if (!list || !q) return;
  var topic = "";
  var LIMIT = 60, expanded = false, more = document.getElementById("bib-more"), focus = document.getElementById("bib-focus");
  var yFrom = document.getElementById("bib-from"), yTo = document.getElementById("bib-to"), exclude = "";
  // the page ships the first 60 entries as HTML; the full set travels as JSON and is rendered here on demand
  var dataEl = document.getElementById("bib-data"), DATA = null, LABELS = { codes: {}, topics: {} };
  try { var parsed = dataEl ? JSON.parse(dataEl.textContent) : null; if (parsed) { DATA = parsed.items; LABELS = parsed; } } catch (e) { DATA = null; }
  if (DATA) DATA.forEach(function (r) { r.s = (r.t + " " + r.a + " " + r.j + " " + r.y + " " + (r.n || "")).toLowerCase().replace(/"/g, ""); });
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]; }); }
  function itemHtml(r) {
    var link = r.d ? '<a href="https://doi.org/' + esc(r.d) + '" target="_blank" rel="noopener external">doi:' + esc(r.d) + '</a>'
                   : '<a href="https://pubmed.ncbi.nlm.nih.gov/' + esc(r.m) + '/" target="_blank" rel="noopener external">PubMed ' + esc(r.m) + '</a>';
    var tags = r.c.map(function (c) { return '<span class="bib-tag">' + esc(LABELS.codes[c] || c) + '</span>'; }).join("") +
               r.k.map(function (k) { return '<span class="bib-tag bib-topic">' + esc(LABELS.topics[k] || k) + '</span>'; }).join("") +
               (r.w ? '<span class="bib-tag bib-via">' + (r.w === "PubMed search" ? "PubMed search" : "found on " + esc(r.w)) + '</span>' : "");
    return '<li class="bib-item"><p class="bib-title">' + esc(r.t) + '</p><p class="bib-meta">' + esc(r.a) + ' · <em>' + esc(r.j) + '</em> · ' + esc(r.y) +
           (r.v ? ' · ' + esc(r.v) : '') + (r.p ? ':' + esc(r.p) : '') + ' · ' + link + '</p><p class="bib-tags">' + tags + '</p></li>';
  }
  var items = DATA ? null : Array.prototype.slice.call(list.querySelectorAll(".bib-item"));
  function apply() {
    var text = q.value.trim().toLowerCase(), code = sel.value, k = 0;
    var from = yFrom && parseInt(yFrom.value, 10) || 0, to = yTo && parseInt(yTo.value, 10) || 9999;
    if (DATA) {
      var out = [];
      DATA.forEach(function (r) {
        var y = parseInt(r.y, 10) || 0;
        var ok = (!text || r.s.indexOf(text) !== -1) && (!code || r.c.indexOf(code) !== -1) && (!topic || r.k.indexOf(topic) !== -1) &&
                 (!exclude || r.c.indexOf(exclude) === -1) && (y >= from && y <= to);
        if (ok) { k++; if (expanded || k <= LIMIT) out.push(itemHtml(r)); }
      });
      list.innerHTML = out.join("");
    } else items.forEach(function (it) {
      var y = parseInt(it.getAttribute("data-year"), 10) || 0;
      var ok = (!text || it.getAttribute("data-text").indexOf(text) !== -1) &&
               (!code || it.getAttribute("data-codes").split(" ").indexOf(code) !== -1) &&
               (!topic || it.getAttribute("data-topics").split(" ").indexOf(topic) !== -1) &&
               (!exclude || it.getAttribute("data-codes").split(" ").indexOf(exclude) === -1) &&
               (y >= from && y <= to);
      if (ok) k++;
      it.hidden = !ok || (!expanded && k > LIMIT);
    });
    n.textContent = k;
    if (more) { more.hidden = expanded || k <= LIMIT; more.textContent = "Show all " + k + " matching references"; }
    if (focus) focus.querySelectorAll("button").forEach(function (b) {
      var on = b.hasAttribute("data-exclude") ? b.getAttribute("data-exclude") === exclude : b.getAttribute("data-code") === code;
      b.setAttribute("aria-pressed", on ? "true" : "false");
    });
  }
  if (more) more.addEventListener("click", function () { expanded = true; apply(); });
  if (focus) focus.querySelectorAll("button").forEach(function (b) {
    b.addEventListener("click", function () {
      if (b.hasAttribute("data-exclude")) { exclude = exclude === b.getAttribute("data-exclude") ? "" : b.getAttribute("data-exclude"); if (exclude && sel.value === exclude) sel.value = ""; }
      else { sel.value = sel.value === b.getAttribute("data-code") ? "" : b.getAttribute("data-code"); if (sel.value && exclude === sel.value) exclude = ""; }
      expanded = false; apply();
    });
  });
  q.addEventListener("input", function () { expanded = false; apply(); }); sel.addEventListener("change", function () { expanded = false; apply(); });
  [yFrom, yTo].forEach(function (el) { if (el) el.addEventListener("input", function () { expanded = false; apply(); }); });
  apply();
  chips.querySelectorAll("button").forEach(function (b) {
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") === "true";
      chips.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
      topic = on ? "" : b.getAttribute("data-topic"); if (!on) b.setAttribute("aria-pressed", "true"); expanded = false; apply();
    });
  });
  document.getElementById("bib-reset").addEventListener("click", function () { q.value = ""; sel.value = ""; topic = ""; exclude = ""; expanded = false; if (yFrom) yFrom.value = ""; if (yTo) yTo.value = ""; chips.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); }); apply(); });
})();

/* ── Teratogens register: search + filters, rendered from embedded data ── */
(function () {
  var list = document.getElementById("tera-list"), q = document.getElementById("tera-q"), n = document.getElementById("tera-n"), dataEl = document.getElementById("tera-data");
  if (!list || !q || !dataEl) return;
  var DATA; try { DATA = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]; }); };
  var LABEL = { clp: "EU harmonised classification (CLP Annex VI)", p65: "California Proposition 65 (developmental toxicant)", ema: "EMA: pregnancy prevention programme or contraindication for teratogenicity", who: "WHO fact sheet on congenital disorders", bib: "DysNet bibliography (peer-reviewed meta-analysis)" };
  var LEVEL = { known: "Known", presumed: "Presumed", suspected: "Suspected" }, KIND = { chemical: "Chemical", medicine: "Medicine", product: "Consumer product" };
  var EU_ALL = "Mandatory hazard classification and labelling of the substance and of mixtures containing it (CLP Annex VI, harmonised).";
  var EU_1 = " Not to be supplied to the general public as a substance or in mixtures above the concentration limit (REACH Annex XVII, entry 30, where listed in Appendix 5 or 6). Cannot be approved as a pesticide active substance unless human exposure is negligible (Regulation 1107/2009, Annex II 3.6.4). Prohibited in cosmetic products (Regulation 1223/2009, Article 15). Reprotoxic substance under Directive 2004/37/EC as amended by Directive 2022/431: substitution, exposure limits and health surveillance at work.";
  var EU_2 = " Labelling required; no general ban on supply to the public for category 2. Prohibited in cosmetics unless evaluated as safe by the SCCS (Regulation 1223/2009, Article 15(1)).";
  var CA = "A clear and reasonable warning is required before knowingly exposing anyone in California (Health and Safety Code 25249.6); listing does not ban the substance. Attorney General, district attorneys and private enforcers; civil penalties up to USD 2,500 per violation per day.";
  var SRC_SHORT = { clp: "EU CLP", p65: "California Prop 65", ema: "EMA", who: "WHO", bib: "DysNet bibliography" };
  function shortJur(place, text) {
    var s = /programme/.test(text) ? "authorised with a pregnancy prevention programme" : /ontraindicated/.test(text) ? "contraindicated in pregnancy" : /REMS/.test(text) ? "REMS programme" : /boxed warning/.test(text) ? "boxed warning" : /mandatory/.test(text) ? "pregnancy warning mandatory" : /no EU-wide/.test(text) ? "legal, no pregnancy warning" : /pack/.test(text) ? "legal, pack warnings" : text.split(";")[0].slice(0, 50);
    var cls = /contraindicated/.test(s) ? "st-ban" : /(warning|REMS|programme)/.test(s) ? "st-warn" : "st-ok";
    return '<span class="st ' + cls + '">' + esc(place.replace(" / EEA", "").replace(" (USA)", "")) + ": " + esc(s) + '</span>';
  }
  function itemHtml(r) {
    var clp = r.src.filter(function (s) { return s.c === "clp"; })[0];
    var srcs = r.src.map(function (s) {
      var det = s.c === "clp" ? "Repr. " + s.cat + " · " + s.st.join(", ") : s.c === "p65" ? s.tox + (s.on ? " · listed " + s.on.slice(0, 4) : "") : s.c === "ema" ? "pregnancy prevention programme or contraindication" : s.c === "who" ? "fact sheet on congenital disorders" : "peer-reviewed evidence";
      return '<span class="tera-src src-' + s.c + '">' + SRC_SHORT[s.c] + '<small> · ' + esc(det) + '</small></span>';
    }).join("");
    var chips = [];
    if (clp) { chips.push('<span class="st st-label">EU: hazard label required</span>'); if (clp.cat === "2") chips.push('<span class="st st-ok">EU: sale to the public allowed</span><span class="st st-warn">EU: cosmetics case by case</span>'); else chips.push('<span class="st st-ban">EU: no sale to the public</span><span class="st st-ban">EU: banned in cosmetics</span><span class="st st-ban">EU: no pesticide approval</span><span class="st st-work">EU: workplace limits</span>'); }
    if (r.s.indexOf("p65") !== -1) chips.push('<span class="st st-warn">California: warning required</span>');
    if (clp && clp.cat !== "2") chips.push('<span class="st st-ban">ChemFORWARD: band F by list screening</span>');
    Object.keys(r.jur || {}).forEach(function (k) { chips.push(shortJur(k, r.jur[k])); });
    var details = r.src.map(function (s) {
      var line = LABEL[s.c] + ": " + (s.c === "clp" ? "Repr. " + s.cat + ", " + s.st.join(", ") + (s.from ? ", applies from " + s.from : "") : s.c === "p65" ? s.tox + (s.on ? ", listed " + s.on : "") + (s.via ? ", via " + s.via : "") : (s.note || ""));
      var u = s.u || (s.c === "p65" ? "https://oehha.ca.gov/proposition-65/proposition-65-list" : "");
      return "<li>" + esc(line) + (u ? ' <a href="' + esc(u) + '"' + (/^http/.test(u) ? ' target="_blank" rel="noopener external"' : '') + '>source ↗</a>' : '') + "</li>";
    });
    if (clp) details.push("<li><strong>EU / EEA:</strong> " + EU_ALL + (clp.cat === "2" ? EU_2 : EU_1) + "</li>");
    if (r.s.indexOf("p65") !== -1) details.push("<li><strong>California (USA):</strong> " + CA + "</li>");
    Object.keys(r.jur || {}).forEach(function (k) { details.push("<li><strong>" + esc(k) + ":</strong> " + esc(r.jur[k]) + "</li>"); });
    if (clp && clp.cat !== "2") details.push("<li><strong>ChemFORWARD:</strong> meets the list-screening criterion for the F hazard band (Annex VI Repr. 1), per Chemical Hazard Rating Guidance v2.2, May 2024.</li>");
    if (r.cas) details.push('<li><strong>GreenScreen:</strong> check the <a href="https://registry.greenscreenchemicals.org/" target="_blank" rel="noopener external">assessment registry</a> for CAS ' + esc(r.cas) + '.</li>');
    var ids = [r.cas ? "CAS " + r.cas : "", r.ec ? "EC " + r.ec : ""].filter(Boolean).join(" · ");
    return '<li class="tera-item"><div class="tera-head"><span class="tera-level tera-' + r.l + '">' + LEVEL[r.l] + '</span><h3 class="tera-name">' + (r.w ? '<a href="' + esc(r.w) + '" target="_blank" rel="noopener external" title="Wikipedia">' + esc(r.n) + '</a>' : esc(r.n)) + '</h3><span class="badge">' + (KIND[r.k] || r.k) + '</span>' + (ids ? '<span class="tera-ids">' + ids + '</span>' : '') + '</div>' +
           '<div class="tera-srcs">' + srcs + '</div><div class="tera-status">' + chips.join("") + '</div>' +
           '<details class="tera-details"><summary>Details and legal basis</summary><ul>' + details.join("") + '</ul></details></li>';
  }
  DATA.forEach(function (r) { r.t = (r.f + " " + r.cas + " " + r.ec).toLowerCase(); });
  var ORDER = { known: 0, presumed: 1, suspected: 2 };
  DATA.sort(function (a, b) { return (ORDER[a.l] - ORDER[b.l]) || a.n.toLowerCase().replace(/^[^a-z]+/, "").localeCompare(b.n.toLowerCase().replace(/^[^a-z]+/, "")); });
  var LIMIT = 40, expanded = false, more = document.getElementById("tera-more");
  var state = { sources: [], levels: [], kinds: [] };
  function apply() {
    var text = q.value.trim().toLowerCase(), k = 0, out = [];
    DATA.forEach(function (r) {
      var ok = (!text || r.t.indexOf(text) !== -1) &&
               (!state.sources.length || state.sources.some(function (s) { return r.s.indexOf(s) !== -1; })) &&
               (!state.levels.length || state.levels.indexOf(r.l) !== -1) &&
               (!state.kinds.length || state.kinds.indexOf(r.k) !== -1);
      if (ok) { k++; if (expanded || k <= LIMIT) out.push(itemHtml(r)); }
    });
    list.innerHTML = out.join("");
    n.textContent = k;
    more.hidden = expanded || k <= LIMIT; more.textContent = "Show all " + k + " matching entries";
  }
  function bind(groupId, attr, key) {
    document.querySelectorAll("#" + groupId + " button[" + attr + "]").forEach(function (b) {
      b.addEventListener("click", function () {
        var v = b.getAttribute(attr), i = state[key].indexOf(v);
        if (i === -1) state[key].push(v); else state[key].splice(i, 1);
        b.setAttribute("aria-pressed", i === -1 ? "true" : "false"); expanded = false; apply();
      });
    });
  }
  bind("tera-sources", "data-source", "sources"); bind("tera-levels", "data-level", "levels"); bind("tera-levels", "data-kind", "kinds");
  q.addEventListener("input", function () { expanded = false; apply(); });
  more.addEventListener("click", function () { expanded = true; apply(); });
  document.getElementById("tera-reset").addEventListener("click", function () {
    q.value = ""; state = { sources: [], levels: [], kinds: [] }; expanded = false;
    document.querySelectorAll("#tera-controls button[aria-pressed]").forEach(function (b) { b.setAttribute("aria-pressed", "false"); }); apply();
  });
  var pre = new URLSearchParams(location.search).get("q"); if (pre) { q.value = pre; }
  apply();
})();
