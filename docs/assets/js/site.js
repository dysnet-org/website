/* DysNet demo — behaviours ported from the HDS website:
   ⌘K site search, "On this page" contents, back-to-top. No trackers, no cookies. */
(function () {
  "use strict";

  /* Path prefix when served from a GitHub Pages project URL; "" on www.dysnet.org. */
  var BASE = window.SITE_BASE || "";

  /* ── Arriving on an anchor: land on the entry, not where it was before the page settled ── */
  // The browser jumps to #cond-90025 as soon as the element exists, and the web fonts that load after it
  // change the height of everything above, so a long page leaves the reader far from the entry a search
  // result or a link promised. Once the fonts and the page have loaded, the jump is made again, unless
  // the reader has already scrolled on their own.
  if (location.hash.length > 1) {
    var landed = false, moved = false;
    window.addEventListener("wheel", function () { moved = true; }, { once: true, passive: true });
    window.addEventListener("touchmove", function () { moved = true; }, { once: true, passive: true });
    window.addEventListener("keydown", function () { moved = true; }, { once: true });
    var reland = function () {
      if (moved) return;
      var el = document.getElementById(decodeURIComponent(location.hash.slice(1)));
      if (el) { el.scrollIntoView({ block: "start" }); landed = true; }
    };
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(reland);
    window.addEventListener("load", reland);
  }

  /* ── Site search (HDS Search.astro pattern, simplified) ─────────── */
  var overlay = document.getElementById("search-overlay");
  var trigger = document.getElementById("search-btn");
  // ?q= opens the site-wide search, unless the page has a search box of its own that owns the
  // parameter: the bibliography, the teratogens register and the conditions page each filter
  // themselves on ?q=, and opening the overlay over them answered a question nobody asked.
  var qParam = new URLSearchParams(location.search).get("q");
  if (qParam && !document.querySelector("#bib-q, #tera-q, #cond-q")) setTimeout(function () { openSearch(qParam); }, 300);
  var index = null, loading = null, lastQ = "";
  // accents, case and punctuation around codes do not matter: "Pölydactyly", "orpha:2911", "Q71.3"
  function norm(s) { return String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase(); }
  function esc(s) { return String(s || "").replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function load() {
    if (index || loading) return loading;
    loading = fetch(BASE + "/search-index.json").then(function (r) { return r.json(); }).then(function (d) {
      index = d.entries.map(function (e) {
        var kind = d.kinds[e[0]];
        var url = e[1] || "/knowledge/teratogens/?q=" + encodeURIComponent(e[2]);
        return { kind: kind, url: url, title: e[2], desc: kind === "Substance" ? "Substance" + (e[3] ? " · " + e[3] : "") : e[3],
                 t: norm(e[2]), h: norm(e[2] + " " + e[3] + " " + e[4]) };
      });
      if (lastQ) search(lastQ);
    });
    return loading;
  }
  // the kinds a reader most often means come first when two results score alike
  var KIND_W = { Condition: 9, Form: 7, Page: 6, Registry: 5, "Care centre": 5, Association: 5, "Research team": 3, Substance: 2 };

  function openSearch(preset) {
    if (!overlay) return;
    overlay.hidden = false;
    document.body.style.overflow = "hidden";
    var input = overlay.querySelector("input");
    input.value = typeof preset === "string" ? preset : "";
    render([], "");
    input.focus();
    load();
    if (input.value) search(input.value);
  }
  function closeSearch() {
    if (!overlay) return;
    overlay.hidden = true;
    document.body.style.overflow = "";
    if (trigger) trigger.focus();
  }
  function more(q) {
    // the two registers too large to list here answer the query themselves
    var e = encodeURIComponent(q), h = esc(q);
    return '<li class="search-more"><a href="' + BASE + '/knowledge/bibliography/?q=' + e + '">Search the bibliography for “' + h + '”</a></li>' +
           '<li class="search-more"><a href="' + BASE + '/knowledge/teratogens/?q=' + e + '">Search the substances register for “' + h + '”</a></li>';
  }
  function render(hits, q) {
    var list = overlay.querySelector(".search-results");
    if (!q) {
      list.innerHTML = '<li class="search-empty">Type a condition, an ORPHAcode or ICD code, a registry, a care centre, an association or a substance.</li>';
      return;
    }
    if (!index) { list.innerHTML = '<li class="search-empty">Loading the index…</li>'; return; }
    var rows = hits.slice(0, 12).map(function (h) {
      return '<li><a href="' + BASE + h.url + '"><span class="search-kind">' + esc(h.kind) + "</span><strong>" + esc(h.title) +
             "</strong><span>" + esc(h.desc) + "</span></a></li>";
    }).join("");
    var none = hits.length ? "" : '<li class="search-empty">Nothing on the site matches “' + esc(q) + '”.</li>';
    list.innerHTML = rows + none + (q.length >= 3 ? more(q) : "");
  }
  function search(q) {
    lastQ = q;
    var qn = norm(q).trim();
    if (!index || qn.length < 2) { render([], qn.length < 2 ? "" : q.trim()); return; }
    var tokens = qn.split(/\s+/);
    var hits = index.filter(function (e) { return tokens.every(function (t) { return e.h.indexOf(t) !== -1; }); });
    hits.forEach(function (e) {
      var s = KIND_W[e.kind] || 0;
      if (e.t === qn) s += 100;
      else if (e.t.indexOf(qn) === 0) s += 60;
      else if (e.t.indexOf(qn) !== -1) s += 40;
      else if (tokens.every(function (t) { return e.t.indexOf(t) !== -1; })) s += 25;
      if ((" " + e.h + " ").indexOf(" " + qn + " ") !== -1) s += 10;   // a whole code or word, not a fragment
      e.s = s;
    });
    hits.sort(function (a, b) { return b.s - a.s || a.title.length - b.title.length; });
    render(hits, q.trim());
  }
  if (trigger && overlay) {
    trigger.addEventListener("click", openSearch);
    overlay.addEventListener("click", function (e) { if (e.target === overlay) closeSearch(); });
    overlay.querySelector(".search-close").addEventListener("click", closeSearch);
    overlay.querySelector("input").addEventListener("input", function (e) { search(e.target.value); });
    overlay.querySelector("input").addEventListener("keydown", function (e) {
      if (e.key === "Enter") { var a = overlay.querySelector(".search-results a"); if (a) { e.preventDefault(); a.click(); } }
    });
    // a result on the page already open only moves the view, so the overlay has to close itself
    overlay.querySelector(".search-results").addEventListener("click", function (e) { if (e.target.closest("a")) closeSearch(); });
    document.addEventListener("keydown", function (e) {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); openSearch(); }
      if (e.key === "Escape" && !overlay.hidden) closeSearch();
    });
  }

  /* ── "On this page" contents (HDS TableOfContents pattern) ──────── */
  var main = document.getElementById("main");
  if (main) {
    var heads = Array.prototype.slice.call(main.querySelectorAll("h2")).filter(function (h) { return !h.closest(".card, .aud-grid, .aud-panel, .hub-grid, .person, .start-here, .entry, .annex"); });
    if (heads.length >= 3) {
      var box = document.createElement("nav");
      box.className = "onpage";
      box.setAttribute("aria-label", "On this page");
      var items = heads.map(function (h, i) {
        if (!h.id) h.id = "s-" + (i + 1) + "-" + h.textContent.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/(^-|-$)/g, "").slice(0, 40);
        var label = h.getAttribute("data-toc") || h.textContent;
        return '<li><a href="#' + h.id + '">' + label + "</a></li>";
      }).join("");
      box.innerHTML = "<p>On this page</p><ul>" + items + "</ul>";
      // A page can name its own slot; otherwise the position is computed from the first heading.
      var slot = main.querySelector("#toc-here");
      if (slot) { slot.parentNode.insertBefore(box, slot); slot.remove(); return; }
      // Anchor the box at section level: climb to the child of the section container, then step back
      // over the opener marks (tick, eyebrow) so it sits between the intro and the first section.
      var anchor = heads[0];
      while (anchor.parentNode && anchor.parentNode !== main &&
             !(anchor.parentNode.classList && anchor.parentNode.classList.contains("container"))) anchor = anchor.parentNode;
      var prev = anchor.previousElementSibling;
      while (prev && prev.classList && (prev.classList.contains("tick") || prev.classList.contains("eyebrow"))) {
        anchor = prev; prev = anchor.previousElementSibling;
      }
      anchor.parentNode.insertBefore(box, anchor);
    }
  }

  /* ── Arriving on a demand: open it ──────────────────────────────────── */
// /voice/#demand-3 should show demand 3, not a closed row the reader has to find.
(function openDemandFromHash() {
  function open() {
    var m = /^#demand-\d+$/.test(location.hash) && document.querySelector(location.hash);
    if (!m) return;
    var d = m.querySelector("details");
    if (d) { d.open = true; m.scrollIntoView({ block: "start" }); }
  }
  open();
  window.addEventListener("hashchange", open);
})();

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
  var chosen = document.getElementById("bank-chosen"), ask = document.getElementById("bank-ask");
  function pressed(sel) { var b = box.querySelector(sel + ' button[aria-pressed="true"]'); return b ? b.childNodes[0].textContent.trim() : ""; }
  // a chosen amount must survive the click: it is restated in the panel and carried into the request
  function sync() {
    if (!chosen || !ask) return;
    var freq = pressed(".freq").toLowerCase(), amount = pressed(".amounts");
    var sum = amount === "Other" ? "an amount of my choosing" : amount.replace("€", "EUR ");
    chosen.innerHTML = "Your gift: <strong>" + freq + ", " + (amount === "Other" ? "amount of your choosing" : amount) + "</strong>.";
    var body = "Hello,\n\nI have made a " + freq + " gift of " + sum +
               " by bank transfer to the Handelsbanken account.\n\nThank you,\n";
    ask.setAttribute("href", "mailto:sal.giambruno@dysnet.org?cc=info@dysnet.org&subject=" +
      encodeURIComponent("Donation to DysNet: " + freq + ", " + (amount === "Other" ? "amount to agree" : amount)) +
      "&body=" + encodeURIComponent(body));
  }
  box.querySelectorAll(".freq button, .amounts button").forEach(function (b) {
    b.addEventListener("click", function () {
      var group = b.closest(".freq, .amounts");
      group.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
      b.setAttribute("aria-pressed", "true");
      sync();
    });
  });
  sync();
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
  // A reader who already knows what they are looking for should not have to answer three questions:
  // the box matches a name, a synonym, an ORPHAcode or an ICD code against each card's data-search.
  var qBox = document.getElementById("cond-q");

  function apply() {
    var text = qBox ? qBox.value.trim().toLowerCase() : "";
    var n = 0;
    cards.forEach(function (c) {
      var ok = true;
      Object.keys(state).forEach(function (q) {
        var v = state[q];
        if (v && (c.getAttribute("data-" + q) || "").split(" ").indexOf(v) === -1) ok = false;
      });
      if (ok && text && (c.getAttribute("data-search") || "").indexOf(text) === -1) ok = false;
      c.style.display = ok ? "" : "none";
      if (ok) n++;
    });
    document.getElementById("finder-n").textContent = n;
    if (typeof writeFilterParams === "function") writeFilterParams({ q: text });
  }
  if (qBox) {
    qBox.addEventListener("input", apply);
    // a searched view can be linked: /knowledge/understanding-dysmelia/?q=Q71.3
    var pre = typeof filterParams === "function" ? filterParams().get("q") : null;
    if (pre) { qBox.value = pre; }
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
    if (qBox) qBox.value = "";
    finder.querySelectorAll(".finder-chips").forEach(function (group) {
      group.querySelectorAll("button").forEach(function (x, i) { x.setAttribute("aria-pressed", i === 0 ? "true" : "false"); });
    });
    apply();
  });
  apply();   // a ?q= in the address has to take effect on load
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

    // colour countries + accessibility (the card's counts are written at build time, from the members list)
    Object.keys(data.countries).forEach(function (id) {
      var c = data.countries[id], el = svg.querySelector("#c" + id);
      if (!el) return;
      el.classList.add("st-" + c.status);
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "button");
      el.setAttribute("aria-label", c.name + ": " + data.labels[c.status] + ", " + c.orgs.map(orgName).join(", "));
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
      var RANK = { national: 0, regional: 1, departement: 2 };
      gj.features.slice().sort(function (a, b) {
        return (RANK[a.properties.scope] || 1) - (RANK[b.properties.scope] || 1);
      }).forEach(function (f) {
        var d = "";
        (f.geometry.type === "MultiPolygon" ? f.geometry.coordinates : [f.geometry.coordinates]).forEach(function (poly) {
          poly.forEach(function (ring) { d += "M" + ring.map(function (c) { var q = project(c[0], c[1]); return q[0].toFixed(2) + "," + q[1].toFixed(2); }).join("L") + "Z"; });
        });
        var path = document.createElementNS("http://www.w3.org/2000/svg", "path");
        path.setAttribute("d", d); path.setAttribute("class", "zone zone-" + f.properties.status);
        // painted most general first, so a département or regional outline ends up on top of a
        // national one and the pointer finds the registry that actually covers this ground
        path.setAttribute("data-scope", f.properties.scope || "regional");
        // the French zones carry a département name, the others the area they record; the status words
        // are the ones the legend and the WebGL map use (ZONE_LABELS in build-demo.py)
        var zl = ((data.zoneLabels || {})[f.properties.status] || {}).tip || f.properties.status;
        path.setAttribute("data-label", f.properties.label + " · " + (f.properties.area || f.properties.dep_name || f.properties.country) + " · " + zl);
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
      var clin = (data.clinical || {})[c.name];
      tip.innerHTML = "<strong>" + c.name + "</strong><span class=\"status\">" + data.labels[c.status] + "</span><ul>" +
        c.orgs.map(function (o) { var u = orgUrl(o); return "<li>" + (u ? "<a href=\"" + u + "\" target=\"_blank\" rel=\"noopener external\">" + orgName(o) + "</a>" : orgName(o)) + "</li>"; }).join("") + "</ul>" +
        (clin && clin.length ? '<p class="tip-clin">Clinical registry here: ' + clin.join(", ") + "</p>" : "");
      tip.style.display = "block";
      var r = host.getBoundingClientRect();
      var left = Math.min(x - r.left + 14, r.width - tip.offsetWidth - 12), top = Math.min(y - r.top + 14, r.height - tip.offsetHeight - 12);
      tip.style.left = Math.max(12, left) + "px"; tip.style.top = Math.max(12, top) + "px";
    }
    var hideTimer = null, pinned = null;
    // Placed once per country, then left where it is: a tooltip that follows the pointer
    // cannot be reached, and this one carries the member associations as links.
    var tipFor = null;
    function hideSoon() { if (pinned) return; clearTimeout(hideTimer); hideTimer = setTimeout(function () { tip.style.display = "none"; tipFor = null; }, 600); }
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
      if (zone) { clearTimeout(hideTimer); if (tipFor === zone && tip.style.display === "block") return; tipFor = zone; tip.innerHTML = "<strong>" + zone.getAttribute("data-label").split(" · ")[0] + "</strong><span class=\"status\">Registry coverage</span><p style=\"margin:0.3rem 0 0\">" + zone.getAttribute("data-label").split(" · ").slice(1).join(" · ") + "</p>"; tip.style.display = "block"; var rz = host.getBoundingClientRect(); tip.style.left = Math.max(12, Math.min(e.clientX - rz.left + 14, rz.width - tip.offsetWidth - 12)) + "px"; tip.style.top = Math.max(12, Math.min(e.clientY - rz.top + 14, rz.height - tip.offsetHeight - 12)) + "px"; return; }
      var el = e.target.closest ? e.target.closest("path[class*='st-']") : null;
      if (el) {
        clearTimeout(hideTimer);
        if (tipFor !== el || tip.style.display !== "block") { tipFor = el; showTip(el, e.clientX, e.clientY); }
      } else hideSoon();
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
    function choose(key) {
      chips.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-view") === key ? "true" : "false"); });
      setView(regionBox(REGIONS[key]));
      var g = document.querySelector(".map-guess");
      if (g) g.textContent = "Showing " + LABELS[key] + ".";
    }
    chips.forEach(function (b) { b.addEventListener("click", function () { choose(b.getAttribute("data-view")); }); });
    var first = guessRegion();
    svg.setAttribute("viewBox", full.join(" "));
    setTimeout(function () { choose(first); }, 350);
    window.addEventListener("resize", function () {
      var k = document.querySelector('.map-views button[aria-pressed="true"]');
      if (k) { current = regionBox(REGIONS[k.getAttribute("data-view")]); svg.setAttribute("viewBox", current.join(" ")); }
    });
  });
})();

/* ── Phone test, shared by the landing map blocks below ──────────────── */
function isPhone() { return window.matchMedia ? window.matchMedia("(max-width: 48rem)").matches : window.innerWidth <= 768; }

/* ── Landing map card: close after reading, reopen on demand ────────── */
(function () {
  var panel = document.getElementById("map-panel");
  var reopen = document.getElementById("map-panel-reopen");
  if (!panel || !reopen) return;
  var close = panel.querySelector(".map-panel-close");
  function setOpen(open, remember) {
    panel.classList.toggle("is-closed", !open); reopen.hidden = open;
    if (remember !== false) try { sessionStorage.setItem("dysnet-map-card", open ? "open" : "closed"); } catch (e) {}
  }
  close.addEventListener("click", function () { setOpen(false); reopen.focus(); });
  reopen.addEventListener("click", function () { setOpen(true); close.focus(); });
  // on a phone the map comes first and the card waits, collapsed to its title, until the reader asks for it
  var stored = null;
  try { stored = sessionStorage.getItem("dysnet-map-card"); } catch (e) {}
  if (stored === "closed" || (stored !== "open" && isPhone())) setOpen(false, false);
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
  // the legend sits under the map on a phone, collapsed to its button until the reader opens it
  set(false);
})();

/* ── Filter state in the address bar, so a filtered view can be linked ── */
function filterParams() { return new URLSearchParams(location.search); }
function writeFilterParams(obj) {
  if (!window.history || !history.replaceState) return;
  var u = new URL(location.href), p = u.searchParams;
  Object.keys(obj).forEach(function (k) {
    var v = obj[k];
    if (v == null || v === "" || (Array.isArray(v) && !v.length)) p.delete(k);
    else p.set(k, Array.isArray(v) ? v.join(",") : String(v));
  });
  var s = p.toString();
  history.replaceState(null, "", u.pathname + (s ? "?" + s : "") + u.hash);
}
function filterList(name) { var v = filterParams().get(name); return v ? v.split(",").filter(Boolean) : []; }

/* ── Registry: one answer per reader ─────────────────────────────────────── */
// Every panel is in the HTML, so a reader without JavaScript gets all four rather than
// none. Here we keep one and remember the choice in the URL, so a delegate can send an
// association straight to the panel written for it.
(function () {
  var box = document.getElementById("reg-aud");
  if (!box) return;
  var pills = Array.prototype.slice.call(box.querySelectorAll("button[data-aud]"));
  var panels = {};
  pills.forEach(function (b) {
    var k = b.getAttribute("data-aud");
    panels[k] = document.getElementById("aud-" + k);
  });
  function show(key, push) {
    if (!panels[key]) key = pills[0].getAttribute("data-aud");
    pills.forEach(function (b) {
      var on = b.getAttribute("data-aud") === key;
      b.setAttribute("aria-selected", on ? "true" : "false");
    });
    Object.keys(panels).forEach(function (k) { if (panels[k]) panels[k].hidden = k !== key; });
    if (push) writeFilterParams({ for: key === pills[0].getAttribute("data-aud") ? "" : key });
  }
  pills.forEach(function (b) {
    b.addEventListener("click", function () { show(b.getAttribute("data-aud"), true); });
  });
  // arrow keys move along the row, as a tablist should
  box.querySelector(".aud-pills").addEventListener("keydown", function (e) {
    var i = pills.indexOf(document.activeElement);
    if (i === -1) return;
    var j = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : -1;
    if (j < 0 || j >= pills.length) return;
    e.preventDefault();
    pills[j].focus();
    show(pills[j].getAttribute("data-aud"), true);
  });
  show(filterParams().get("for") || pills[0].getAttribute("data-aud"), false);
})();

/* ── Epidemiology: expected cases a year, by country and condition ──── */
(function () {
  var table = document.getElementById("inc-table"), sel = document.getElementById("inc-condition");
  if (!table || !sel) return;
  var dataEl = document.getElementById("inc-data"), DATA = null;
  try { DATA = JSON.parse(dataEl.textContent); } catch (e) { return; }
  var rows = Array.prototype.slice.call(table.tBodies[0].rows);
  var region = document.getElementById("inc-region"), q = document.getElementById("inc-q");
  var nEl = document.getElementById("inc-n"), totalEl = document.getElementById("inc-total");
  var labelEl = document.getElementById("inc-label"), headEl = document.getElementById("inc-head");
  var reset = document.getElementById("inc-reset"), more = document.getElementById("inc-more");
  var LIMIT = 25, expanded = false;

  // same rounding as the build: a country expecting less than one affected birth a year keeps a decimal
  function cases(births, rate) {
    var n = births * rate / 100000;
    return n >= 10 ? Math.round(n).toLocaleString("en") : (n >= 0.1 ? n.toFixed(1) : "<0.1");
  }
  function apply() {
    var r = DATA.rates[sel.value | 0], rate = r[1], basis = r[4] || "", note = r[5] || "";
    // A condition no one has measured keeps its row. Showing a dash and saying why is
    // information; dropping it from the list would hide the gap instead of reporting it.
    var estimable = rate !== null && rate !== undefined && rate !== "";
    var reg = region.value, needle = (q.value || "").trim().toLowerCase();
    writeFilterParams({ condition: r[3] === DATA.rates[0][3] ? "" : r[3], region: reg, country: q.value.trim() });
    var shown = 0, sum = 0;
    rows.forEach(function (tr) {
      var births = +tr.getAttribute("data-births");
      tr.cells[3].innerHTML = estimable ? cases(births, rate) : "&mdash;";
      var ok = (!reg || tr.getAttribute("data-region") === reg) &&
               (!needle || tr.getAttribute("data-name").indexOf(needle) !== -1);
      if (ok) { shown++; if (estimable) sum += births * rate / 100000; }
      // the count and the total cover every match; the table shows the first LIMIT until asked for more
      tr.hidden = !ok || (!expanded && shown > LIMIT);
    });
    more.hidden = shown <= LIMIT;
    more.textContent = expanded ? "Show the first " + LIMIT + " countries" : "Show all " + shown.toLocaleString("en") + " countries";
    nEl.textContent = shown.toLocaleString("en");
    totalEl.textContent = estimable ? (sum >= 10 ? Math.round(sum).toLocaleString("en") : sum.toFixed(1)) : "\u2014";
    var unit = estimable ? (rate >= 10 ? (rate / 10) + " per 10,000 births" : rate + " per 100,000 births") : "";
    labelEl.textContent = estimable
      ? r[0].toLowerCase() + " (" + unit + ", " + r[2] + ")"
      : r[0].toLowerCase() + ", for which no birth prevalence has been published, so no number can be estimated";
    headEl.textContent = "Expected a year: " + r[0];
    var basisEl = document.getElementById("inc-basis");
    if (basisEl) {
      var LABEL = DATA.basisLabels || {};   // written by the build, the same words as the prevalence table
      var lab = LABEL[basis] || "";
      var txt = note || (estimable ? "Source: " + r[2] + "." : "");
      basisEl.textContent = lab ? lab + ". " + txt : "";
      basisEl.hidden = !lab;
    }
  }
  // a link can arrive with a condition, a region or a country already chosen
  var pre = filterParams();
  if (pre.get("condition")) {
    DATA.rates.forEach(function (r, i) { if (r[3] === pre.get("condition")) sel.value = String(i); });
  }
  if (pre.get("region")) region.value = pre.get("region");
  if (pre.get("country")) q.value = pre.get("country");
  sel.addEventListener("change", apply);
  region.addEventListener("change", apply);
  q.addEventListener("input", apply);
  more.addEventListener("click", function () { expanded = !expanded; apply(); if (!expanded) more.scrollIntoView({ block: "center" }); });
  reset.addEventListener("click", function () { sel.value = "0"; region.value = ""; q.value = ""; expanded = false; apply(); });
  apply();
})();

/* ── Registries: country, condition and EUROCAT filters ─────────────── */
(function () {
  var table = document.getElementById("reg-table"), box = document.getElementById("reg-controls");
  if (!table || !box) return;
  var rows = Array.prototype.slice.call(table.tBodies[0].rows);
  var country = document.getElementById("reg-country"), cond = document.getElementById("reg-condition");
  var classif = document.getElementById("reg-classif"), eurocat = document.getElementById("reg-eurocat");
  var nEl = document.getElementById("reg-n"), hint = document.getElementById("reg-hint");
  function has(tr, attr, code) { return (" " + (tr.getAttribute(attr) || "") + " ").indexOf(" " + code + " ") !== -1; }
  // A condition is matched by the registries coded for it or for its specific forms; the ones that
  // list it only through a broader group are many, so they join the result only when asked for.
  function matches(tr, withClassif) {
    var c = cond.value;
    if (country.value && tr.getAttribute("data-country") !== country.value) return false;
    if (eurocat.value !== "" && tr.getAttribute("data-eurocat") !== eurocat.value) return false;
    if (!c) return true;
    return has(tr, "data-direct", c) || has(tr, "data-forms", c) || (withClassif && has(tr, "data-classif", c));
  }
  function apply() {
    classif.disabled = !cond.value;
    if (!cond.value) classif.checked = false;
    var shown = 0;
    rows.forEach(function (tr) { var ok = matches(tr, classif.checked); tr.hidden = !ok; if (ok) shown++; });
    nEl.textContent = shown;
    hint.innerHTML = "";
    if (!shown) {
      var more = cond.value && !classif.checked ? rows.filter(function (tr) { return matches(tr, true); }).length : 0;
      var name = cond.options[cond.selectedIndex].text;
      if (more) {
        hint.innerHTML = ". No registry here is coded for " + name + " itself; " + more + " list it through a broader group. " +
          '<button type="button" id="reg-show-classif">Show them</button>';
        document.getElementById("reg-show-classif").addEventListener("click", function () { classif.checked = true; apply(); });
      } else {
        hint.textContent = ". No registry matches these filters.";
      }
    }
    writeFilterParams({ country: country.value, condition: cond.value, classif: classif.checked ? "1" : "", eurocat: eurocat.value });
  }
  // a filtered view can be linked: /knowledge/registries/?country=France&condition=2911&eurocat=1
  var pre = filterParams();
  if (pre.get("country")) country.value = pre.get("country");
  if (pre.get("condition")) cond.value = pre.get("condition");
  if (pre.get("eurocat") !== null) eurocat.value = pre.get("eurocat");
  if (pre.get("classif") === "1") classif.checked = true;
  [country, cond, eurocat].forEach(function (el) { el.addEventListener("change", apply); });
  classif.addEventListener("change", apply);
  document.getElementById("reg-reset").addEventListener("click", function () {
    country.value = ""; cond.value = ""; eurocat.value = ""; classif.checked = false; apply();
  });
  apply();
})();

/* ── Bibliography: search + filters ────────────────────────────────── */
(function () {
  var list = document.getElementById("bib-list"), q = document.getElementById("bib-q"), sel = document.getElementById("bib-code"), chips = document.getElementById("bib-topics"), n = document.getElementById("bib-n");
  if (!list || !q) return;
  var topic = "", registry = "";   // registry: the register key a paper rests on, from ?registry=
  var LIMIT = 60, expanded = false, more = document.getElementById("bib-more"), focus = document.getElementById("bib-focus");
  var yFrom = document.getElementById("bib-from"), yTo = document.getElementById("bib-to"), exclude = "";
  // the page ships the first 60 entries as HTML; the full set travels as JSON and is rendered here on demand
  var dataEl = document.getElementById("bib-data"), DATA = null, LABELS = { codes: {}, topics: {} };
  try { var parsed = dataEl && dataEl.textContent.trim() ? JSON.parse(dataEl.textContent) : null; if (parsed) { DATA = parsed.items; LABELS = parsed; } } catch (e) { DATA = null; }
  function index(rows) { rows.forEach(function (r) { r.s = (r.t + " " + r.a + " " + r.j + " " + r.y + " " + (r.n || "")).toLowerCase().replace(/"/g, ""); }); }
  if (DATA) index(DATA);
  function esc(s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]; }); }
  function itemHtml(r) {
    // the old SICI DOIs carry < and >: percent-encoded in the address, escaped in the text
    var link = r.d ? '<a href="https://doi.org/' + esc(r.d.replace(/</g, "%3C").replace(/>/g, "%3E")) + '" target="_blank" rel="noopener external">doi:' + esc(r.d) + '</a>'
                   : '<a href="https://pubmed.ncbi.nlm.nih.gov/' + esc(r.m) + '/" target="_blank" rel="noopener external">PubMed ' + esc(r.m) + '</a>';
    var tags = r.c.map(function (c) { return '<span class="bib-tag">' + esc(LABELS.codes[c] || c) + '</span>'; }).join("") +
               r.k.map(function (k) { return '<span class="bib-tag bib-topic">' + esc(LABELS.topics[k] || k) + '</span>'; }).join("") +
               (r.w ? '<span class="bib-tag bib-via">' + (r.w === "PubMed search" ? "PubMed search" : "found on " + esc(r.w)) + '</span>' : "") +
               (r.r || []).map(function (g) { return '<span class="bib-tag bib-reg">rests on ' + esc(g) + '</span>'; }).join("");
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
                 (!exclude || r.c.indexOf(exclude) === -1) && (y >= from && y <= to) && (!registry || (r.r || []).indexOf(registry) !== -1);
        if (ok) { k++; if (expanded || k <= LIMIT) out.push(itemHtml(r)); }
      });
      list.innerHTML = out.join("");
    } else items.forEach(function (it) {
      var y = parseInt(it.getAttribute("data-year"), 10) || 0;
      var ok = (!text || it.getAttribute("data-text").indexOf(text) !== -1) &&
               (!code || it.getAttribute("data-codes").split(" ").indexOf(code) !== -1) &&
               (!topic || it.getAttribute("data-topics").split(" ").indexOf(topic) !== -1) &&
               (!exclude || it.getAttribute("data-codes").split(" ").indexOf(exclude) === -1) &&
               (y >= from && y <= to) && (!registry || (it.getAttribute("data-registries") || "").split(" ").indexOf(registry) !== -1);
      if (ok) k++;
      it.hidden = !ok || (!expanded && k > LIMIT);
    });
    n.textContent = k;
    writeFilterParams({ q: q.value.trim(), condition: code, topic: topic, exclude: exclude, registry: registry,
                        from: yFrom && yFrom.value, to: yTo && yTo.value });
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
  // a link can arrive with a condition, a theme, a search or a year range already chosen
  var pre = filterParams();
  if (pre.get("q")) q.value = pre.get("q");
  if (pre.get("condition")) sel.value = pre.get("condition");
  if (pre.get("topic")) topic = pre.get("topic");
  if (pre.get("exclude")) exclude = pre.get("exclude");
  if (pre.get("registry")) registry = pre.get("registry");
  if (pre.get("from") && yFrom) yFrom.value = pre.get("from");
  if (pre.get("to") && yTo) yTo.value = pre.get("to");
  chips.querySelectorAll("button").forEach(function (b) {
    if (topic && b.getAttribute("data-topic") === topic) b.setAttribute("aria-pressed", "true");
    b.addEventListener("click", function () {
      var on = b.getAttribute("aria-pressed") === "true";
      chips.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); });
      topic = on ? "" : b.getAttribute("data-topic"); if (!on) b.setAttribute("aria-pressed", "true"); expanded = false; apply();
    });
  });
  document.getElementById("bib-reset").addEventListener("click", function () { q.value = ""; sel.value = ""; topic = ""; exclude = ""; registry = ""; expanded = false; if (yFrom) yFrom.value = ""; if (yTo) yTo.value = ""; chips.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", "false"); }); apply(); });
  apply();
  // the full set travels as a file: until it lands, the 60 entries in the HTML are filtered in place
  var bibSrc = dataEl && dataEl.getAttribute("data-src");
  if (!DATA && bibSrc) fetch(bibSrc).then(function (r) { return r.json(); }).then(function (d) {
    LABELS = d; DATA = d.items; index(DATA); items = null; apply();
  }).catch(function () {});
})();

/* ── Teratogens register: search + filters, rendered from embedded data ── */
(function () {
  var list = document.getElementById("tera-list"), q = document.getElementById("tera-q"), n = document.getElementById("tera-n"), dataEl = document.getElementById("tera-data");
  if (!list || !q || !dataEl) return;
  var DATA = null;
  try { if (dataEl.textContent.trim()) DATA = JSON.parse(dataEl.textContent); } catch (e) { DATA = null; }
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"]/g, function (ch) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[ch]; }); };
  var LABEL = { clp: "EU harmonised classification (CLP Annex VI)", nite: "Japan: GHS classification by the government (NITE)", p65: "California Proposition 65 (developmental toxicant)", ema: "EMA: pregnancy prevention programme or contraindication for teratogenicity", who: "WHO fact sheet on congenital disorders", efsa: "EFSA health-based guidance value", bib: "DysNet bibliography (peer-reviewed meta-analysis)" };
  var LEVEL = { known: "Known", presumed: "Presumed", suspected: "Suspected" }, KIND = { chemical: "Chemical", medicine: "Medicine", product: "Consumer product" };
  var USE = { food: "Food and drink", construction: "Building and construction", goods: "Manufactured goods", cosmetics: "Cosmetics and personal care", cleaning: "Cleaning and household", agriculture: "Agriculture and pest control", fuel: "Fuel and vehicles" };
  var EU_ALL = "Mandatory hazard classification and labelling of the substance and of mixtures containing it (CLP Annex VI, harmonised).";
  var EU_1 = " Not to be supplied to the general public as a substance or in mixtures above the concentration limit (REACH Annex XVII, entry 30, where listed in Appendix 5 or 6). Cannot be approved as a pesticide active substance unless human exposure is negligible (Regulation 1107/2009, Annex II 3.6.4). Prohibited in cosmetic products (Regulation 1223/2009, Article 15). Reprotoxic substance under Directive 2004/37/EC as amended by Directive 2022/431: substitution, exposure limits and health surveillance at work.";
  var EU_2 = " Labelling required; no general ban on supply to the public for category 2. Prohibited in cosmetics unless evaluated as safe by the SCCS (Regulation 1223/2009, Article 15(1)).";
  var CA = "A clear and reasonable warning is required before knowingly exposing anyone in California (Health and Safety Code 25249.6); listing does not ban the substance. Attorney General, district attorneys and private enforcers; civil penalties up to USD 2,500 per violation per day.";
  var SRC_SHORT = { clp: "EU CLP", nite: "Japan NITE", p65: "California Prop 65", ema: "EMA", efsa: "EFSA", who: "WHO", bib: "DysNet bibliography" };
  var DEC_SRC = {
    "eu-ppp": ["European Commission", "https://ec.europa.eu/food/plant/pesticides/eu-pesticides-database/start/screen/active-substances"],
    "reach-xvii": ["European Commission", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02006R1907-20260622"],
    "reach-xiv": ["European Commission", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02006R1907-20260622"],
    "cosmetics": ["European Commission", "https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:02009R1223-20260518"],
    "stockholm": ["Stockholm Convention", "https://www.pops.int/TheConvention/ThePOPs/ListingofPOPs/tabid/2509/Default.aspx"],
    "rotterdam": ["national authorities, notified to the Rotterdam Convention", "https://www.pic.int/Procedures/NotificationsofFinalRegulatoryActions/Database/tabid/1368/language/en-US/Default.aspx"]
  };
  var DEC_CLS = { approved: "st-warn", pending: "st-warn", refused: "st-ban", public_supply_banned: "st-ban",
                  cosmetics_banned: "st-ban", cosmetics_restricted: "st-warn",
                  authorisation_required: "st-ban", eliminated: "st-ban", restricted: "st-ban",
                  unintentional: "st-label", banned_somewhere: "st-ban" };
  // Every chip carries a count of what is in the current selection, so that narrowing to
  // "Known" shows at once how many of those an authority acted on, and where.
  function recount(rows) {
    var n = { source: {}, level: {}, kind: {}, use: {}, dec: {}, paper: {} };
    rows.forEach(function (r) {
      (r.s || []).forEach(function (c) { n.source[c] = (n.source[c] || 0) + 1; });
      n.level[r.l] = (n.level[r.l] || 0) + 1;
      n.kind[r.k] = (n.kind[r.k] || 0) + 1;
      if (r.med) n.kind.medicine = (n.kind.medicine || 0) + 1;
      (r.u || []).forEach(function (u) { n.use[u] = (n.use[u] || 0) + 1; });
      var seen = {};
      (r.dec || []).forEach(function (d) { if (!seen[d.v]) { seen[d.v] = 1; n.dec[d.v] = (n.dec[d.v] || 0) + 1; } });
      if (r.pc) n.paper.paper = (n.paper.paper || 0) + 1;
      if (r.pcoch) n.paper.cochrane = (n.paper.cochrane || 0) + 1;
    });
    [["data-source", n.source], ["data-level", n.level], ["data-kind", n.kind],
     ["data-use", n.use], ["data-dec", n.dec], ["data-paper", n.paper]].forEach(function (pair) {
      document.querySelectorAll("#tera-controls button[" + pair[0] + "]").forEach(function (b) {
        var c = pair[1][b.getAttribute(pair[0])] || 0, small = b.querySelector("small");
        if (!small) { small = document.createElement("small"); b.appendChild(document.createTextNode(" ")); b.appendChild(small); }
        small.textContent = c;
        b.classList.toggle("is-empty", c === 0 && b.getAttribute("aria-pressed") !== "true");
      });
    });
  }

  function paperChip(r) {
    if (!r.pc) return "";
    var lab = "Peer-reviewed: " + r.pc + " paper" + (r.pc === 1 ? "" : "s");
    if (r.pcn) lab += ", incl. " + r.pcn + " Cochrane";
    return '<span class="st dec st-doi">' + lab + "</span>";
  }
  function paperLines(r) {
    var out = (r.pp || []).map(function (x) {
      var cite = esc(x.t) + (x.j ? ' <span class="fine">' + esc(x.j) + ", " + esc(x.y) + "</span>" : "");
      var link = x.d ? ' <a href="https://doi.org/' + esc(x.d) + '" target="_blank" rel="noopener external">doi:' + esc(x.d) + ' \u2197</a>'
               : (x.m ? ' <a href="https://pubmed.ncbi.nlm.nih.gov/' + esc(x.m) + '/" target="_blank" rel="noopener external">PubMed \u2197</a>' : "");
      return "<li>" + (x.c ? "<strong>Cochrane review:</strong> " : "") + cite + link + "</li>";
    });
    var more = r.pc - Math.min(3, (r.pp || []).length);
    if (more > 0 && r.pq) out.push('<li><a href="' + esc(r.pq) + '" target="_blank" rel="noopener external">all ' + r.pc + ' on PubMed \u2197</a></li>');
    return out;
  }
  function decChips(r) {
    return (r.dec || []).map(function (d) {
      return '<span class="st dec ' + (DEC_CLS[d.v] || "st-label") + '">' + esc(d.w) + ": " + esc(d.t) + "</span>";
    }).join("");
  }
  function decLines(r) {
    return (r.dec || []).map(function (d) {
      var meta = DEC_SRC[d.c] || ["", ""], u = d.u || meta[1];
      var line = "<strong>" + esc(d.t) + "</strong> \u2014 " + esc(meta[0]) + (d.d ? ", " + esc(d.d) : "");
      return "<li>" + line + (u ? ' <a href="' + esc(u) + '" target="_blank" rel="noopener external">source \u2197</a>' : "") + "</li>";
    });
  }
  function shortJur(place, text) {
    var s = /programme/.test(text) ? "authorised with a pregnancy prevention programme" : /ontraindicated/.test(text) ? "contraindicated in pregnancy" : /REMS/.test(text) ? "REMS programme" : /boxed warning/.test(text) ? "boxed warning" : /mandatory/.test(text) ? "pregnancy warning mandatory" : /no EU-wide/.test(text) ? "legal, no pregnancy warning" : /pack/.test(text) ? "legal, pack warnings" : text.split(";")[0].slice(0, 50);
    var cls = /contraindicated/.test(s) ? "st-ban" : /(warning|REMS|programme)/.test(s) ? "st-warn" : "st-ok";
    return '<span class="st ' + cls + '">' + esc(place.replace(" / EEA", "").replace(" (USA)", "")) + ": " + esc(s) + '</span>';
  }
  function itemHtml(r) {
    var clp = r.src.filter(function (s) { return s.c === "clp"; })[0];
    var srcs = r.src.map(function (s) {
      var det = s.c === "clp" ? "Repr. " + s.cat + " · " + s.st.join(", ") : s.c === "nite" ? s.st.join(", ") + (s.fy ? " · classified " + s.fy : "") : s.c === "p65" ? s.tox + (s.on ? " · listed " + s.on.slice(0, 4) : "") : s.c === "ema" ? "pregnancy prevention programme or contraindication" : s.c === "who" ? "fact sheet on congenital disorders" : s.c === "efsa" ? "health-based guidance value" : "peer-reviewed evidence";
      return '<span class="tera-src src-' + s.c + '">' + SRC_SHORT[s.c] + '<small> · ' + esc(det) + '</small></span>';
    }).join("");
    var chips = [];
    if (clp) { chips.push('<span class="st st-label">EU: hazard label required</span>'); if (clp.cat === "2") chips.push('<span class="st st-ok">EU: sale to the public allowed</span><span class="st st-warn">EU: cosmetics case by case</span>'); else chips.push('<span class="st st-ban">EU: not supplied to the public above limits</span><span class="st st-ban">EU: prohibited in cosmetics</span><span class="st st-ban">EU: not approvable as a pesticide</span><span class="st st-work">EU: workplace controls</span>'); }
    if (r.s.indexOf("p65") !== -1) chips.push(r.del ? '<span class="st st-ok">California: delisted ' + esc(r.del) + ', no warning required</span>' : '<span class="st st-warn">California: warning required</span>');
    if (clp && clp.cat !== "2") chips.push('<span class="st st-ban">ChemFORWARD: band F by list screening</span>');
    if (r.efsa && r.efsa.value) chips.push('<span class="st st-label">EFSA: ' + esc(r.efsa.value.split(";")[0].toLowerCase()) + '</span>');
    Object.keys(r.jur || {}).forEach(function (k) { chips.push(shortJur(k, r.jur[k])); });
    if (r.dec && r.dec.length) chips.unshift(decChips(r));
    if (r.pc) chips.push(paperChip(r));
    var details = r.src.map(function (s) {
      var line = LABEL[s.c] + ": " + (s.c === "clp" ? "Repr. " + s.cat + ", " + s.st.join(", ") + (s.from ? ", applies from " + s.from : "") : s.c === "nite" ? s.st.join(", ") + (s.fy ? ", classified in the " + s.fy + " fiscal year" : "") : s.c === "p65" ? s.tox + (s.on ? ", listed " + s.on : "") + (s.via ? ", via " + s.via : "") : (s.note || ""));
      var u = s.u || (s.c === "p65" ? "https://oehha.ca.gov/proposition-65/proposition-65-list" : "");
      return "<li>" + esc(line) + (u ? ' <a href="' + esc(u) + '"' + (/^http/.test(u) ? ' target="_blank" rel="noopener external"' : '') + '>source ↗</a>' : '') + "</li>";
    });
    details = decLines(r).concat(paperLines(r)).concat(details);
    if (clp) details.push("<li><strong>EU / EEA:</strong> " + EU_ALL + (clp.cat === "2" ? EU_2 : EU_1) + "</li>");
    if (r.s.indexOf("p65") !== -1) details.push("<li><strong>California (USA):</strong> " + (r.del ? "Listed as a developmental toxicant and delisted on " + esc(r.del) + "; no warning is required today. " : "") + CA + "</li>");
    Object.keys(r.jur || {}).forEach(function (k) { details.push("<li><strong>" + esc(k) + ":</strong> " + esc(r.jur[k]) + "</li>"); });
    if (clp && clp.cat !== "2") details.push("<li><strong>ChemFORWARD:</strong> meets the list-screening criterion for the F hazard band (Annex VI Repr. 1), per Chemical Hazard Rating Guidance v2.2, May 2024.</li>");
    if (r.med && r.atc && r.atc.length) details.push('<li><strong>Medicine:</strong> ' + (r.mev ? '\u201c' + esc(r.mev) + '\u201d ' : "") + 'ATC ' + esc(r.atc.join(", ")) + ', the WHO classification of medicines.</li>');
    Object.keys(r.ue || {}).sort().forEach(function (u) { details.push('<li><strong>' + (USE[u] || u) + ':</strong> \u201c' + esc(r.ue[u]) + '\u201d' + (r.w ? ' <a href="' + esc(r.w) + '" target="_blank" rel="noopener external">Wikipedia \u2197</a>' : "") + '</li>'); });
    if (r.cas) details.push('<li><strong>GreenScreen:</strong> check the <a href="https://registry.greenscreenchemicals.org/" target="_blank" rel="noopener external">assessment registry</a> for CAS ' + esc(r.cas) + '.</li>');
    var ids = [r.cas ? "CAS " + r.cas : "", /^\d{3}-\d{3}-\d$/.test(r.ec || "") ? "EC " + r.ec : "", (r.atc && r.atc.length ? "ATC " + r.atc.join(", ") : "")].filter(Boolean).join(" · ");
    return '<li class="tera-item"><div class="tera-head"><span class="tera-level tera-' + r.l + '">' + LEVEL[r.l] + '</span><h3 class="tera-name">' + (r.w ? '<a href="' + esc(r.w) + '" target="_blank" rel="noopener external" title="Wikipedia">' + esc(r.n) + '</a>' : esc(r.n)) + '</h3><span class="badge">' + (KIND[r.k] || r.k) + '</span>' + (r.med && r.k !== 'medicine' ? '<span class="badge badge-med">Medicine</span>' : '') + (ids ? '<span class="tera-ids">' + ids + '</span>' : '') + '</div>' +
           '<div class="tera-srcs">' + srcs + '</div>' + ((r.u && r.u.length) ? '<div class="tera-uses">' + r.u.map(function (u) { return '<span class="use use-' + u + '">' + (USE[u] || u) + '</span>'; }).join("") + '</div>' : "") + '<div class="tera-status">' + chips.join("") + '</div>' + (r.reg ? '<p class="tera-registry">A pregnancy registry is recruiting for ' + esc(r.reg.m) + ': <a href="' + esc(r.reg.u) + '" target="_blank" rel="noopener external">' + esc(r.reg.n) + '</a>' + (r.reg.p ? ' \u00b7 ' + esc(r.reg.p) : '') + ' <span class="fine">listed by the FDA, which does not endorse it</span></p>' : '') +
           '<details class="tera-details"><summary>Details and legal basis</summary><ul>' + details.join("") + '</ul></details></li>';
  }
  function prime(rows) { rows.forEach(function (r) { r.t = (r.f + " " + r.cas + " " + r.ec).toLowerCase(); }); }
  if (DATA) prime(DATA);
  var ORDER = { known: 0, presumed: 1, suspected: 2 };
  function order(rows) { rows.sort(function (a, b) { return (ORDER[a.l] - ORDER[b.l]) || a.n.toLowerCase().replace(/^[^a-z]+/, "").localeCompare(b.n.toLowerCase().replace(/^[^a-z]+/, "")); }); }
  if (DATA) order(DATA);
  var LIMIT = 40, expanded = false, more = document.getElementById("tera-more");
  var state = { sources: [], levels: [], kinds: [], uses: [], decs: [], papers: [] };
  function apply() {
    if (!DATA) return;                      // the entries rendered into the page stay until the data lands
    var text = q.value.trim().toLowerCase(), k = 0, out = [], kept = [];
    DATA.forEach(function (r) {
      var ok = (!text || r.t.indexOf(text) !== -1) &&
               (!state.sources.length || state.sources.some(function (s) { return r.s.indexOf(s) !== -1; })) &&
               (!state.levels.length || state.levels.indexOf(r.l) !== -1) &&
               (!state.kinds.length || state.kinds.indexOf(r.k) !== -1 || (r.med && state.kinds.indexOf('medicine') !== -1)) &&
               (!state.uses.length || (r.u || []).some(function (u) { return state.uses.indexOf(u) !== -1; })) &&
               (!state.decs.length || (r.dec || []).some(function (d) { return state.decs.indexOf(d.v) !== -1; })) &&
               (!state.papers.length || state.papers.every(function (p) { return p === "cochrane" ? r.pcoch : r.pc; }));
      if (ok) { k++; kept.push(r); if (expanded || k <= LIMIT) out.push(itemHtml(r)); }
    });
    list.innerHTML = out.join("");
    n.textContent = k;
    recount(kept);
    writeFilterParams({ q: q.value.trim(), source: state.sources, level: state.levels, kind: state.kinds, use: state.uses, decision: state.decs, paper: state.papers });
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
  bind("tera-uses", "data-use", "uses"); bind("tera-decisions", "data-dec", "decs"); bind("tera-decisions", "data-paper", "papers");
  q.addEventListener("input", function () { expanded = false; apply(); });
  more.addEventListener("click", function () { expanded = true; apply(); });
  document.getElementById("tera-reset").addEventListener("click", function () {
    q.value = ""; state = { sources: [], levels: [], kinds: [], uses: [], decs: [], papers: [] }; expanded = false;
    document.querySelectorAll("#tera-controls button[aria-pressed]").forEach(function (b) { b.setAttribute("aria-pressed", "false"); }); apply();
  });
  // a link can arrive with a search, a source, a level, a kind or a use already chosen
  var pre = filterParams();
  if (pre.get("q")) q.value = pre.get("q");
  state.sources = filterList("source"); state.levels = filterList("level");
  state.kinds = filterList("kind"); state.uses = filterList("use"); state.decs = filterList("decision"); state.papers = filterList("paper");
  [["data-source", state.sources], ["data-level", state.levels], ["data-kind", state.kinds], ["data-use", state.uses], ["data-dec", state.decs], ["data-paper", state.papers]].forEach(function (pair) {
    document.querySelectorAll("#tera-controls button[" + pair[0] + "]").forEach(function (b) {
      if (pair[1].indexOf(b.getAttribute(pair[0])) !== -1) b.setAttribute("aria-pressed", "true");
    });
  });
  apply();
  var teraSrc = dataEl.getAttribute("data-src");
  if (!DATA && teraSrc) fetch(teraSrc).then(function (r) { return r.json(); }).then(function (d) { DATA = d; prime(DATA); order(DATA); apply(); }).catch(function () {});
})();
