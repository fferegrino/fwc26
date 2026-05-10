(() => {
  const gallery = document.getElementById("gallery");
  const searchEl = document.getElementById("sticker-search");
  const filterEl = document.getElementById("country-filter");
  const statusEl = document.getElementById("status-filter");
  const groupEl = document.getElementById("group-by-country");
  const compactEl = document.getElementById("compact-toggle");
  const globalCounterEl = document.getElementById("global-counter");

  function isProbablyMobile() {
    try {
      const mql =
        (q) => typeof window.matchMedia === "function" && window.matchMedia(q).matches;
      return (
        mql("(pointer: coarse)") ||
        mql("(hover: none)") ||
        mql("(max-width: 820px)")
      );
    } catch {
      return false;
    }
  }

  // Hide advanced toggles (still functional; just not shown).
  for (const el of [compactEl, groupEl]) {
    const label = el?.closest?.("label.toggle");
    if (label) {
      label.hidden = true;
      label.style.display = "none";
    }
  }

  // Default to compact view on mobile-ish devices.
  if (compactEl && isProbablyMobile()) {
    compactEl.checked = true;
    document.body.classList.add("compact");
  }

  compactEl?.addEventListener("change", () => {
    document.body.classList.toggle("compact", compactEl.checked);
  });

  // ---------------------------------------------------------------------------
  // URL <-> controls sync. Recognised query params:
  //   show=all|missing|owned|dupes   -> status filter
  //   country=<exact name>           -> country filter
  //   q=<text>                       -> search box
  //   group=true|false               -> "Group by country" toggle
  //   compact=true|false             -> "Compact" toggle
  // ---------------------------------------------------------------------------
  const VALID_STATUS = new Set(["all", "missing", "owned", "dupes"]);

  function parseBool(value) {
    if (value == null) return null;
    const v = String(value).toLowerCase();
    if (v === "1" || v === "true" || v === "yes" || v === "on") return true;
    if (v === "0" || v === "false" || v === "no" || v === "off") return false;
    return null;
  }

  function applyQueryToControls() {
    const params = new URLSearchParams(window.location.search);

    const show = params.get("show");
    if (show && VALID_STATUS.has(show) && statusEl) {
      statusEl.value = show;
    }

    const country = params.get("country");
    if (country && filterEl) {
      const has = Array.from(filterEl.options).some((o) => o.value === country);
      if (has) filterEl.value = country;
    }

    const q = params.get("q");
    if (q != null && searchEl) {
      searchEl.value = q;
    }

    const group = parseBool(params.get("group"));
    if (group != null && groupEl) {
      groupEl.checked = group;
    }

    const compact = parseBool(params.get("compact"));
    if (compact != null && compactEl) {
      compactEl.checked = compact;
      document.body.classList.toggle("compact", compact);
    }
  }

  function updateQueryFromControls() {
    const params = new URLSearchParams();
    if (statusEl && statusEl.value && statusEl.value !== "all") {
      params.set("show", statusEl.value);
    }
    if (filterEl && filterEl.value && filterEl.value !== "__all__") {
      params.set("country", filterEl.value);
    }
    const q = (searchEl?.value || "").trim();
    if (q) params.set("q", q);
    if (groupEl && !groupEl.checked) params.set("group", "false");

    const qs = params.toString();
    const url = qs
      ? `${window.location.pathname}?${qs}${window.location.hash}`
      : `${window.location.pathname}${window.location.hash}`;
    window.history.replaceState(null, "", url);
  }

  // ---------------------------------------------------------------------------
  // Sticker include filter. Edit this to control which rows from data.json
  // are loaded into the gallery. Return true to keep, false to drop.
  // ---------------------------------------------------------------------------
  const STICKER_CODE_RE = /^(00|[A-Z]{3}\d{1,2})$/;
  function includeSticker(row) {
    return STICKER_CODE_RE.test(row.sticker_code);
  }

  /** One horizontal strip per 3-letter prefix (or 00), 225×300px cells, hosted on ImageKit. */
  const SPRITE_BASE = "https://ik.imagekit.io/thatcsharpguy/fwc26";

  /** Max sticker number per prefix in the loaded data — strip width for CSS sprites. */
  function buildPrefixMaxNum(rows) {
    const max = new Map();
    for (const row of rows) {
      const code = row.sticker_code;
      if (code === "00") continue;
      const m = code.match(/^([A-Z]+)(\d+)$/);
      if (!m) continue;
      const prefix = m[1];
      const n = parseInt(m[2], 10);
      max.set(prefix, Math.max(max.get(prefix) ?? 0, n));
    }
    return max;
  }

  function spriteForCode(code, prefixMaxNum) {
    if (code === "00") {
      return { url: `${SPRITE_BASE}/00.webp`, count: 1, index: 0 };
    }
    const m = code.match(/^([A-Z]+)(\d+)$/);
    if (!m) return null;
    const prefix = m[1];
    const num = parseInt(m[2], 10);
    const count = prefixMaxNum.get(prefix);
    if (!count) return null;
    return {
      url: `${SPRITE_BASE}/${prefix}.webp`,
      count,
      index: Math.max(0, num - 1),
    };
  }

  // Special "countries" in the album that should appear before real nations.
  const SPECIAL_FIRST = [
    "We Are Panini",
    "FIFA World Cup 2026",
    "Host Countries and Cities",
  ];

  // Country -> 3-letter code, derived from the loaded dataset (e.g. "Mexico" -> "MEX").
  function buildCountryCodeMap(rows) {
    const map = new Map();
    // Special-case: all FWC* stickers should be treated as one group.
    map.set("FIFA World Cup 2026", "FWC");
    for (const row of rows) {
      const code = String(row?.sticker_code ?? "");
      const m = code.match(/^([A-Z]{3})\d+$/);
      if (!m) continue;
      const prefix = m[1];
      const country = row.country;
      if (!country) continue;
      if (!map.has(country)) map.set(country, prefix);
    }
    return map;
  }

  function codeFor(country, countryCodeMap) {
    return countryCodeMap.get(country) || "";
  }

  // Populated in init(); used by sorting + group headers.
  let countryCodeMap = new Map();

  // Pick a per-portrait CSS layout from the row's properties.
  function deriveLayout(row) {
    if (row.country === "We Are Panini") return "shiny";
    if (row.country === "FIFA World Cup 2026") return "shiny";
    if (row.country === "Host Countries and Cities") return "legend";
    if (row.name === "Emblem") return "wide";
    if (row.name === "Team Photo") return "wide";
    return "default";
  }

  // How many copies of a given sticker_code the user owns, per got.json.
  // got.json shape: { "MEX": [[1, 2], [2, 1]], "UZB": [[20, 1], [1, 0]], ... }
  // Each entry is [stickerNumber, count]. For codes without digits (e.g. "00"),
  // use the whole code as the key and 0 as the number, e.g. { "00": [[0, 1]] }.
  function countOf(code, got) {
    const m = code.match(/^([A-Z]+)(\d+)$/);
    const prefix = m ? m[1] : code;
    const num = m ? parseInt(m[2], 10) : 0;
    const arr = got[prefix] || [];
    const entry = arr.find((pair) => Array.isArray(pair) && pair[0] === num);
    return entry ? Number(entry[1]) || 0 : 0;
  }

  function toSticker(row, got, prefixMaxNum) {
    const sprite = spriteForCode(row.sticker_code, prefixMaxNum);
    const code = String(row.sticker_code || "");
    const country =
      code.startsWith("FWC") ? "FIFA World Cup 2026" : row.country;
    return {
      id: row.sticker_code,
      name: row.name,
      country,
      role: row.sticker_code,    // shown as subtitle so collectors see the code
      image: sprite?.url,
      sprite: sprite
        ? { count: sprite.count, index: sprite.index }
        : undefined,
      layout: deriveLayout(row),
      badge: undefined,
      count: countOf(row.sticker_code, got),
    };
  }

  function compareCountries(a, b, countryCodeMap) {
    const ai = SPECIAL_FIRST.indexOf(a);
    const bi = SPECIAL_FIRST.indexOf(b);
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
    const ac = codeFor(a, countryCodeMap) || a;
    const bc = codeFor(b, countryCodeMap) || b;
    const byCode = String(ac).localeCompare(String(bc));
    if (byCode) return byCode;
    return a.localeCompare(b);
  }

  function stickerEl(s) {
    const card = document.createElement("article");
    card.className = "sticker";
    card.dataset.layout = s.layout || "default";
    card.dataset.id = s.id;

    const photo = document.createElement("div");
    photo.className = "photo";
    if (s.image) {
      photo.style.backgroundImage = `url("${s.image}")`;
      if (s.sprite) {
        photo.classList.add("photo-sprite");
        photo.style.setProperty("--sprite-count", String(s.sprite.count));
        photo.style.setProperty("--sprite-index", String(s.sprite.index));
      }
    } else {
      photo.classList.add("placeholder");
      const code = document.createElement("span");
      code.className = "ph-code";
      code.textContent = s.id;
      const nm = document.createElement("span");
      nm.className = "ph-name";
      nm.textContent = s.name;
      photo.appendChild(code);
      photo.appendChild(nm);
      card.classList.add("no-image");
    }
    card.appendChild(photo);

    const cb = document.createElement("span");
    cb.className = "count-badge";
    if (s.count === 0) {
      cb.classList.add("count-badge--missing");
      cb.textContent = "\u2717"; /* ✗ */
      cb.title = "Missing";
    } else {
      card.classList.add("got");
      cb.classList.add("count-badge--owned");
      if (s.count === 1) {
        cb.textContent = "\u2713"; /* ✓ */
        cb.title = "Owned";
      } else {
        const extras = s.count - 1;
        cb.textContent = `+${extras}`;
        cb.title = `${s.count} owned (${extras} extra${extras === 1 ? "" : "s"})`;
      }
    }
    card.appendChild(cb);

    if (s.badge) {
      const b = document.createElement("span");
      b.className = "badge";
      b.textContent = s.badge;
      card.appendChild(b);
    }

    if (s.image) {
      const meta = document.createElement("div");
      meta.className = "meta";
      const h = document.createElement("h3");
      h.className = "name";
      h.textContent = s.name;
      meta.appendChild(h);
      if (s.role) {
        const p = document.createElement("p");
        p.className = "sub";
        p.textContent = s.role;
        meta.appendChild(p);
      }
      card.appendChild(meta);
    }

    return card;
  }

  function summarize(items, status) {
    const total = items.length;
    const owned = items.filter((s) => s.count > 0).length;
    const dupes = items.reduce((sum, s) => sum + Math.max(0, s.count - 1), 0);
    if (status === "missing") return `${total} missing`;
    if (status === "owned") return `${total} owned` + (dupes > 0 ? ` · +${dupes} dupes` : "");
    if (status === "dupes") return `${total} card${total === 1 ? "" : "s"} · +${dupes} dupes`;
    const pct = total > 0 ? Math.round((owned / total) * 100) : 0;
    return `${owned} / ${total} (${pct}%)` + (dupes > 0 ? ` · +${dupes} dupes` : "");
  }

  function updateGlobalCounter(stickers, status) {
    globalCounterEl.textContent = summarize(stickers, status);
  }

  function matchesStatus(s, status) {
    switch (status) {
      case "missing": return s.count === 0;
      case "owned":   return s.count > 0;
      case "dupes":   return s.count >= 2;
      default:        return true;
    }
  }

  function matchesSearch(s, rawQuery) {
    const q = (rawQuery || "").trim().toLowerCase();
    if (!q) return true;
    const code = String(s.id ?? "").toLowerCase();
    const name = String(s.name ?? "").toLowerCase();
    return code.includes(q) || name.includes(q);
  }

  function render(stickers) {
    const filter = filterEl.value;
    const status = statusEl.value;
    const grouped = groupEl.checked;

    const visible = stickers.filter(
      (s) =>
        (filter === "__all__" || s.country === filter) &&
        matchesStatus(s, status) &&
        matchesSearch(s, searchEl?.value)
    );

    updateGlobalCounter(visible, status);

    gallery.innerHTML = "";

    if (visible.length === 0) {
      const e = document.createElement("p");
      e.className = "empty";
      e.textContent = "No stickers to show.";
      gallery.appendChild(e);
      return;
    }

    if (!grouped || filter !== "__all__") {
      const m = document.createElement("div");
      m.className = "grid";
      visible.forEach((s) => m.appendChild(stickerEl(s)));
      gallery.appendChild(m);
      return;
    }

    const byCountry = new Map();
    for (const s of visible) {
      if (!byCountry.has(s.country)) byCountry.set(s.country, []);
      byCountry.get(s.country).push(s);
    }
    const orderedCountries = [...byCountry.keys()].sort((a, b) =>
      compareCountries(a, b, countryCodeMap)
    );

    for (const country of orderedCountries) {
      const items = byCountry.get(country);
      const section = document.createElement("section");
      section.className = "country-group";

      const title = document.createElement("h2");
      title.className = "country-group-title";
      const flag = codeFor(country, countryCodeMap);
      title.innerHTML =
        (flag ? `<span class="flag">${flag}</span>` : "") +
        `<span>${country}</span>` +
        `<span class="count">${summarize(items, status)}</span>`;
      section.appendChild(title);

      const m = document.createElement("div");
      m.className = "grid";
      items.forEach((s) => m.appendChild(stickerEl(s)));
      section.appendChild(m);

      gallery.appendChild(section);
    }
  }

  function showError(msg) {
    gallery.innerHTML = "";
    const e = document.createElement("p");
    e.className = "empty";
    e.textContent = msg;
    gallery.appendChild(e);
  }

  async function init() {
    let data;
    try {
      const res = await fetch("./data.json");
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      data = await res.json();
    } catch (err) {
      showError(
        "Couldn't load data.json. If you're opening index.html via file://, " +
        "serve the folder over HTTP instead (e.g. `python3 -m http.server`)."
      );
      console.error(err);
      return;
    }

    let got = {};
    try {
      const res = await fetch("./got.json");
      if (res.ok) got = await res.json();
    } catch {
      // got.json is optional — fall back to no owned stickers
    }

    const rows = Array.isArray(data?.rows) ? data.rows : [];
    const included = rows.filter(includeSticker);
    const prefixMaxNum = buildPrefixMaxNum(included);
    countryCodeMap = buildCountryCodeMap(included);
    const stickers = included.map((r) => toSticker(r, got, prefixMaxNum));

    const countries = [...new Set(stickers.map((s) => s.country))].sort((a, b) =>
      compareCountries(a, b, countryCodeMap)
    );
    for (const c of countries) {
      const opt = document.createElement("option");
      opt.value = c;
      const flag = codeFor(c, countryCodeMap);
      opt.textContent = `${flag ? flag + " " : ""}${c}`;
      filterEl.appendChild(opt);
    }

    applyQueryToControls();

    const onChange = () => {
      updateQueryFromControls();
      render(stickers);
    };

    filterEl.addEventListener("change", onChange);
    statusEl.addEventListener("change", onChange);
    groupEl.addEventListener("change", onChange);
    searchEl?.addEventListener("input", onChange);
    render(stickers);
  }

  init();
})();
