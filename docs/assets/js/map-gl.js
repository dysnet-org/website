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
      ne: { type: "vector", url: "pmtiles://" + base + "/assets/map/ne10m.pmtiles?v=4", attribution: "Natural Earth" },
      dots: { type: "vector", url: "pmtiles://" + base + "/assets/map/dots.pmtiles?v=1" },
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
      // Estimated people living with a limb difference: grey dots, 1 per 1,000 / 100 / 10 / 1 people by zoom band.
      // Base density is 100 per 100,000; a condition of prevalence r per 100,000 keeps dots with u < r*100.
      { id: "dots1000", type: "circle", source: "dots", "source-layer": "dots", minzoom: 0, maxzoom: 4, filter: ["<", ["get", "u"], 4500],
        paint: { "circle-color": "#fbf8ff", "circle-opacity": 0.95, "circle-stroke-color": "#2a0d47", "circle-stroke-width": ["interpolate", ["linear"], ["zoom"], 0, 0.5, 3.9, 0.8], "circle-radius": ["interpolate", ["linear"], ["zoom"], 0, 1.5, 3.9, 2.3] } },
      { id: "dots100", type: "circle", source: "dots", "source-layer": "dots", minzoom: 4, maxzoom: 6, filter: ["<", ["get", "u"], 4500],
        paint: { "circle-color": "#fbf8ff", "circle-opacity": 0.95, "circle-stroke-color": "#2a0d47", "circle-stroke-width": 0.8, "circle-radius": ["interpolate", ["linear"], ["zoom"], 4, 2.0, 5.9, 2.5] } },
      { id: "dots10", type: "circle", source: "dots", "source-layer": "dots", minzoom: 6, maxzoom: 9, filter: ["<", ["get", "u"], 4500],
        paint: { "circle-color": "#fbf8ff", "circle-opacity": 0.95, "circle-stroke-color": "#2a0d47", "circle-stroke-width": 0.8, "circle-radius": ["interpolate", ["linear"], ["zoom"], 6, 2.1, 8.9, 2.7] } },
      { id: "dots1", type: "circle", source: "dots", "source-layer": "dots", minzoom: 9, filter: ["<", ["get", "u"], 4500],
        paint: { "circle-color": "#fbf8ff", "circle-opacity": 0.95, "circle-stroke-color": "#2a0d47", "circle-stroke-width": 0.9, "circle-radius": 2.8 } },
      // City names from GeoNames (cities of 15,000+, CC BY 4.0), tiered by population at build time
      // (tippecanoe per-feature minzoom): megacities/capitals from z2, towns of 15-20k only at z9.
      { id: "cities", type: "symbol", source: "ne", "source-layer": "cities", minzoom: 2.5,
        layout: {
          "text-field": ["get", "name"], "text-font": ["case", ["==", ["get", "cap"], 1], ["literal", ["Open_Sans_Bold"]], ["literal", ["Open_Sans_Regular"]]],
          "text-size": ["interpolate", ["linear"], ["zoom"],
            3, ["step", ["get", "pop"], 10, 500000, 11.5, 2000000, 13],
            9, ["step", ["get", "pop"], 10.5, 50000, 12, 200000, 13.5, 1000000, 15]],
          "text-variable-anchor": ["left", "right", "top", "bottom"], "text-radial-offset": 0.55, "text-justify": "auto",
          "symbol-sort-key": ["-", 0, ["get", "pop"]], "text-max-width": 8
        },
        paint: {
          "text-color": ["step", ["get", "pop"], "#b9a0dc", 50000, "#cdb8ea", 200000, "#e2d3f7", 1000000, "#f7f1fd"],
          "text-halo-color": "#24093f", "text-halo-width": 1.3
        } },
      { id: "cities-dot", type: "circle", source: "ne", "source-layer": "cities", minzoom: 5,
        paint: { "circle-radius": ["interpolate", ["linear"], ["zoom"], 5, 1.2, 9, 2.3], "circle-color": "#24093f", "circle-stroke-color": "#e2d3f7", "circle-stroke-width": 0.8 } },
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

  var DOT_LAYERS = ["dots1000", "dots100", "dots10", "dots1"];

  // ── estimated-people dots: condition selector + live legend ──────────
  (function () {
    var box = document.getElementById("map-dots"), sel = document.getElementById("dot-condition"), legend = document.getElementById("dot-legend");
    if (!box || !sel || !data.rates) return;
    var LAYERS = DOT_LAYERS;
    data.rates.forEach(function (r, i) {
      var o = document.createElement("option"); o.value = i; o.textContent = r[0]; sel.appendChild(o);
    });
    function band() { var z = map.getZoom(); return z < 4 ? 1000 : z < 6 ? 100 : z < 9 ? 10 : 1; }
    function dotsInView() {
      var layers = LAYERS.filter(function (l) { return map.getLayer(l); });
      var seen = {}, n = 0;
      map.queryRenderedFeatures({ layers: layers }).forEach(function (f) {
        var k = f.geometry.coordinates.join(",");   // a dot on a tile edge can appear in two tiles
        if (!seen[k]) { seen[k] = 1; n++; }
      });
      return n;
    }
    function legendText() {
      var r = data.rates[+sel.value], per = band(), n = dotsInView(), fmt = function (x) { return x.toLocaleString("en"); };
      var scale = per === 1 ? fmt(n) + " people in view" : "1 dot = " + fmt(per) + " people · " + fmt(n) + " dots in view ≈ " + fmt(n * per) + " people";
      return scale + " · " + r[0].toLowerCase() + " · about " + r[1] + " per 100,000 births (" + r[2] + ")";
    }
    function update() {
      var r = data.rates[+sel.value];
      LAYERS.forEach(function (id) { if (map.getLayer(id)) map.setFilter(id, ["<", ["get", "u"], Math.round(r[1] * 100)]); });
      legend.textContent = legendText();
    }
    map.on("idle", function () { legend.textContent = legendText(); });  // recount once tiles have settled after any move
    sel.addEventListener("change", update);

    // click a dot: what does it stand for?
    var popup = new maplibregl.Popup({ closeButton: true, closeOnClick: true, maxWidth: "20rem", className: "dot-popup" });
    function dotInfo(e) {
      var per = band(), r = data.rates[+sel.value];
      var people = per === 1 ? "<strong>1 person</strong>" : "<strong>about " + per.toLocaleString("en") + " people</strong>";
      var zoomHint = per === 1 ? "" : " Zoom in to see them one by one: at city zoom, 1 dot = 1 person.";
      popup.setLngLat(e.lngLat).setHTML(
        "<p class=\"dp-main\">This dot stands for " + people + " estimated to live with <em>" + r[0].toLowerCase() + "</em> around here.</p>" +
        "<p class=\"dp-sub\">1 dot = " + (per === 1 ? "1 person" : per.toLocaleString("en") + " people") + " at this zoom level." + zoomHint + "</p>" +
        "<p class=\"dp-foot\">Estimate: " + r[1] + " per 100,000 births (" + r[2] + ") × population living here (GHSL 2025). Not an observed case; the registry exists to make the real ones visible.</p>"
      ).addTo(map);
    }
    LAYERS.forEach(function (id) {
      map.on("click", id, dotInfo);
      map.on("mouseenter", id, function () { map.getCanvas().style.cursor = "pointer"; });
      map.on("mouseleave", id, function () { map.getCanvas().style.cursor = ""; });
    });
    map.on("zoom", function () { var per = band(); if (legend.getAttribute("data-per") !== String(per)) { legend.setAttribute("data-per", per); update(); } });
    map.on("load", function () { box.hidden = false; update(); });
  })();

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
    if (map.queryRenderedFeatures(e.point, { layers: DOT_LAYERS.filter(function (l) { return map.getLayer(l); }) }).length) return; // a dot was clicked
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
