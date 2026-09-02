/* DysNet landing map, WebGL edition.
   MapLibre GL JS (BSD) + PMTiles: one self-hosted Natural Earth 10m tileset
   (public domain), zoom 0–9 (country → city, no streets). No tile provider,
   no API key, no request leaves our domain. Falls back to the SVG map in
   site.js when WebGL is unavailable. */
(function () {
  "use strict";
  var host = document.getElementById("glmap");
  var data = window.DYSNET_MAP;
  if (!host || !data || !window.maplibregl || !window.pmtiles) return;

  // WebGL check (MapLibre 4 dropped maplibregl.supported())
  try {
    var probe = document.createElement("canvas");
    if (!(probe.getContext("webgl2") || probe.getContext("webgl"))) return;
  } catch (e) { return; }

  window.DYSNET_GL_ACTIVE = true;
  document.querySelector(".map-hero").classList.add("gl");

  var base = window.SITE_BASE || "";
  var reduce = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // ── data lookups ───────────────────────────────────────────────────
  var byA3 = {};
  var counts = { member: 0, candidate: 0, contact: 0, orgs: 0 };
  Object.keys(data.countries).forEach(function (id) {
    var c = data.countries[id];
    if (c.a3) byA3[c.a3] = c;
    counts[c.status]++; counts.orgs += c.orgs.length;
  });
  document.querySelectorAll("[data-count]").forEach(function (el) {
    var k = el.getAttribute("data-count");
    el.textContent = k === "countries" ? counts.member + counts.candidate : counts[k];
  });
  function orgName(o) { return Array.isArray(o) ? o[0] : o; }
  function orgUrl(o) { return Array.isArray(o) && o[1] ? o[1] : null; }

  var COLOURS = { member: "#c084fc", candidate: "#4cc42c", contact: "#fbbf24" };
  var fillMatch = ["match", ["get", "ADM0_A3"]];
  Object.keys(byA3).forEach(function (a3) { fillMatch.push(a3, COLOURS[byA3[a3].status]); });
  fillMatch.push("#5a2f86");

  // ── style ──────────────────────────────────────────────────────────
  var protocol = new pmtiles.Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  var style = {
    version: 8,
    glyphs: base + "/assets/fonts/{fontstack}/{range}.pbf",
    sources: {
      ne: { type: "vector", url: "pmtiles://" + base + "/assets/map/ne10m.pmtiles?v=2", attribution: "Natural Earth" },
      offices: { type: "geojson", data: { type: "FeatureCollection", features: data.offices.map(function (o) {
        return { type: "Feature", geometry: { type: "Point", coordinates: [o.lon, o.lat] }, properties: { name: o.name } };
      }) } }
    },
    layers: [
      { id: "bg", type: "background", paint: { "background-color": "#24093f" } },
      { id: "countries", type: "fill", source: "ne", "source-layer": "countries",
        paint: { "fill-color": fillMatch, "fill-opacity": 1 } },
      { id: "hover", type: "fill", source: "ne", "source-layer": "countries", filter: ["==", ["get", "ADM0_A3"], ""],
        paint: { "fill-color": "#ffffff", "fill-opacity": 0.22 } },
      { id: "lakes", type: "fill", source: "ne", "source-layer": "lakes", minzoom: 3, paint: { "fill-color": "#24093f" } },
      { id: "rivers", type: "line", source: "ne", "source-layer": "rivers", minzoom: 5,
        paint: { "line-color": "#3b1463", "line-width": ["interpolate", ["linear"], ["zoom"], 5, 0.4, 9, 1.4] } },
      { id: "admin1", type: "line", source: "ne", "source-layer": "admin1", minzoom: 4,
        paint: { "line-color": "rgba(255,255,255,0.12)", "line-width": 0.6 } },
      { id: "borders", type: "line", source: "ne", "source-layer": "countries",
        paint: { "line-color": "rgba(255,255,255,0.16)", "line-width": ["interpolate", ["linear"], ["zoom"], 1, 0.4, 9, 1.2] } },
      { id: "places-major", type: "symbol", source: "ne", "source-layer": "places", minzoom: 3.5,
        filter: ["<=", ["get", "scalerank"], 1],
        layout: { "text-field": ["get", "name"], "text-font": ["Open_Sans_Regular"], "text-size": 12, "text-anchor": "left", "text-offset": [0.5, 0] },
        paint: { "text-color": "#e9d8fb", "text-halo-color": "#24093f", "text-halo-width": 1.2 } },
      { id: "places-mid", type: "symbol", source: "ne", "source-layer": "places", minzoom: 5.5,
        filter: ["all", [">", ["get", "scalerank"], 1], ["<=", ["get", "scalerank"], 4]],
        layout: { "text-field": ["get", "name"], "text-font": ["Open_Sans_Regular"], "text-size": 11, "text-anchor": "left", "text-offset": [0.5, 0] },
        paint: { "text-color": "#d9c2f5", "text-halo-color": "#24093f", "text-halo-width": 1.2 } },
      { id: "places-minor", type: "symbol", source: "ne", "source-layer": "places", minzoom: 7.5,
        filter: [">", ["get", "scalerank"], 4],
        layout: { "text-field": ["get", "name"], "text-font": ["Open_Sans_Regular"], "text-size": 10, "text-anchor": "left", "text-offset": [0.5, 0] },
        paint: { "text-color": "#c9b3e6", "text-halo-color": "#24093f", "text-halo-width": 1.2 } },
      { id: "office-dot", type: "circle", source: "offices",
        paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 1, 3.5, 9, 7], "circle-color": "#ffffff", "circle-stroke-color": "#4cc42c", "circle-stroke-width": 2 } },
      { id: "office-label", type: "symbol", source: "offices",
        layout: { "text-field": ["get", "name"], "text-font": ["Open_Sans_Bold"], "text-size": 12, "text-anchor": "left", "text-offset": [0.9, 0] },
        paint: { "text-color": "#ffffff", "text-halo-color": "#24093f", "text-halo-width": 1.4 } }
    ]
  };

  var map = new maplibregl.Map({
    container: host, style: style, center: [10, 25], zoom: 1.3, minZoom: 1, maxZoom: 9,
    attributionControl: false, renderWorldCopies: false, dragRotate: false, pitchWithRotate: false
  });
  map.touchZoomRotate.disableRotation();
  window.DYSNET_GLMAP = map;  // handy for debugging in the console
  map.on("error", function (e) { if (e && e.error) console.error("DysNet map:", e.error.message || e.error); });
  map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");

  // ── tooltip (same .map-tip as the SVG map) ─────────────────────────
  var tip = document.querySelector(".map-tip");
  var hideTimer = null;
  function hideSoon() { clearTimeout(hideTimer); hideTimer = setTimeout(function () { tip.style.display = "none"; }, 350); }
  function showTip(c, x, y) {
    tip.innerHTML = "<strong>" + c.name + "</strong><span class=\"status\">" + data.labels[c.status] + "</span><ul>" +
      c.orgs.map(function (o) { var u = orgUrl(o); return "<li>" + (u ? "<a href=\"" + u + "\" target=\"_blank\" rel=\"noopener external\">" + orgName(o) + "</a>" : orgName(o)) + "</li>"; }).join("") + "</ul>";
    tip.style.display = "block";
    var hero = host.parentNode.getBoundingClientRect(), hr = host.getBoundingClientRect();
    var left = Math.min(x + (hr.left - hero.left) + 14, hero.width - tip.offsetWidth - 12);
    var top = Math.min(y + (hr.top - hero.top) + 14, hero.height - tip.offsetHeight - 12);
    tip.style.left = Math.max(12, left) + "px"; tip.style.top = Math.max(12, top) + "px";
  }
  map.on("mousemove", "countries", function (e) {
    var a3 = e.features[0].properties.ADM0_A3, c = byA3[a3];
    map.setFilter("hover", ["==", ["get", "ADM0_A3"], c ? a3 : ""]);
    map.getCanvas().style.cursor = c ? "pointer" : "";
    if (c) { clearTimeout(hideTimer); showTip(c, e.point.x, e.point.y); } else hideSoon();
  });
  map.on("mouseleave", "countries", function () { map.setFilter("hover", ["==", ["get", "ADM0_A3"], ""]); map.getCanvas().style.cursor = ""; hideSoon(); });
  tip.addEventListener("mouseenter", function () { clearTimeout(hideTimer); });
  tip.addEventListener("mouseleave", hideSoon);
  // touch: tap a country to pin its tooltip
  map.on("click", "countries", function (e) {
    var c = byA3[e.features[0].properties.ADM0_A3];
    if (c) { clearTimeout(hideTimer); showTip(c, e.point.x, e.point.y); } else tip.style.display = "none";
  });

  // ── region views (guessed from the device time zone only) ──────────
  var REGIONS = {
    world: [[-170, -55], [180, 78]],
    europe: [[-25, 34], [45, 72]],
    americas: [[-170, -57], [-30, 75]],
    asiapacific: [[60, -50], [180, 55]],
    africa: [[-20, -37], [62, 42]]
  };
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
  var chips = document.querySelectorAll(".map-views button");
  function choose(key, guessed) {
    chips.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-view") === key ? "true" : "false"); });
    map.fitBounds(REGIONS[key], { padding: 24, duration: reduce ? 0 : 900, maxZoom: 5 });
    var g = document.querySelector(".map-guess");
    if (g) g.textContent = guessed ? "Showing " + LABELS[key] + ", guessed from your device’s time zone. Nothing is sent." : "Showing " + LABELS[key] + ". Scroll to zoom, drag to pan.";
  }
  chips.forEach(function (b) { b.addEventListener("click", function () { choose(b.getAttribute("data-view"), false); }); });
  map.once("load", function () {
    var first = guessRegion();
    map.fitBounds(REGIONS.world, { padding: 24, duration: 0 });
    setTimeout(function () { choose(first, first !== "world"); }, 400);
  });
})();
