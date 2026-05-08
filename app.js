(() => {
  const gallery = document.getElementById("gallery");
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
  compactEl?.closest("label.toggle")?.setAttribute("hidden", "");
  groupEl?.closest("label.toggle")?.setAttribute("hidden", "");

  // Default to compact view on mobile-ish devices.
  if (compactEl && isProbablyMobile()) {
    compactEl.checked = true;
    document.body.classList.add("compact");
  }

  compactEl.addEventListener("change", () => {
    document.body.classList.toggle("compact", compactEl.checked);
  });

  // ---------------------------------------------------------------------------
  // Sticker include filter. Edit this to control which rows from data.json
  // are loaded into the gallery. Return true to keep, false to drop.
  // ---------------------------------------------------------------------------
  const STICKER_CODE_RE = /^(00|[A-Z]{3}\d{1,2})$/;
  function includeSticker(row) {
    return STICKER_CODE_RE.test(row.sticker_code);
  }

  // Special "countries" in the album that should appear before real nations.
  const SPECIAL_FIRST = [
    "We Are Panini",
    "FIFA World Cup 2026",
    "Host Countries and Cities",
  ];

  // Country -> flag emoji. Covers the 48 FWC26 nations + a few extras.
  const FLAGS = {
    "Algeria": "🇩🇿", "Argentina": "🇦🇷", "Australia": "🇦🇺", "Austria": "🇦🇹",
    "Belgium": "🇧🇪", "Bolivia": "🇧🇴", "Bosnia and Herzegovina": "🇧🇦",
    "Brazil": "🇧🇷", "Cameroon": "🇨🇲", "Canada": "🇨🇦", "Chile": "🇨🇱",
    "Colombia": "🇨🇴", "Costa Rica": "🇨🇷", "Croatia": "🇭🇷", "Curaçao": "🇨🇼",
    "Czechia": "🇨🇿", "Denmark": "🇩🇰", "Ecuador": "🇪🇨", "Egypt": "🇪🇬",
    "El Salvador": "🇸🇻", "England": "🏴\u{E0067}\u{E0062}\u{E0065}\u{E006E}\u{E0067}\u{E007F}",
    "France": "🇫🇷", "Germany": "🇩🇪", "Ghana": "🇬🇭", "Haiti": "🇭🇹",
    "Honduras": "🇭🇳", "Hungary": "🇭🇺", "Iceland": "🇮🇸", "Iran": "🇮🇷",
    "Iraq": "🇮🇶", "Ireland": "🇮🇪", "Israel": "🇮🇱", "Italy": "🇮🇹",
    "Ivory Coast": "🇨🇮", "Jamaica": "🇯🇲", "Japan": "🇯🇵", "Jordan": "🇯🇴",
    "Kazakhstan": "🇰🇿", "Kuwait": "🇰🇼", "Mali": "🇲🇱", "Mexico": "🇲🇽",
    "Morocco": "🇲🇦", "Netherlands": "🇳🇱", "New Zealand": "🇳🇿", "Nigeria": "🇳🇬",
    "Norway": "🇳🇴", "Panama": "🇵🇦", "Paraguay": "🇵🇾", "Peru": "🇵🇪",
    "Poland": "🇵🇱", "Portugal": "🇵🇹", "Qatar": "🇶🇦", "Romania": "🇷🇴",
    "Saudi Arabia": "🇸🇦", "Scotland": "🏴\u{E0067}\u{E0062}\u{E0073}\u{E0063}\u{E0074}\u{E007F}",
    "Senegal": "🇸🇳", "Serbia": "🇷🇸", "Slovakia": "🇸🇰", "South Africa": "🇿🇦",
    "South Korea": "🇰🇷", "Spain": "🇪🇸", "Suriname": "🇸🇷", "Sweden": "🇸🇪",
    "Switzerland": "🇨🇭", "Trinidad and Tobago": "🇹🇹", "Tunisia": "🇹🇳",
    "Türkiye": "🇹🇷", "Turkey": "🇹🇷", "Ukraine": "🇺🇦",
    "United Arab Emirates": "🇦🇪", "Uruguay": "🇺🇾", "USA": "🇺🇸",
    "Uzbekistan": "🇺🇿", "Venezuela": "🇻🇪", "Wales": "🏴\u{E0067}\u{E0062}\u{E0077}\u{E006C}\u{E0073}\u{E007F}",
  };

  function flagFor(country) {
    return FLAGS[country] || "";
  }

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

  function toSticker(row, got) {
    return {
      id: row.sticker_code,
      name: row.name,
      country: row.country,
      role: row.sticker_code,    // shown as subtitle so collectors see the code
      image: undefined,           // populate later when you scan/upload images
      layout: deriveLayout(row),
      badge: undefined,
      count: countOf(row.sticker_code, got),
    };
  }

  function compareCountries(a, b) {
    const ai = SPECIAL_FIRST.indexOf(a);
    const bi = SPECIAL_FIRST.indexOf(b);
    if (ai !== -1 && bi !== -1) return ai - bi;
    if (ai !== -1) return -1;
    if (bi !== -1) return 1;
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

    if (s.count > 0) {
      card.classList.add("got");
      const cb = document.createElement("span");
      cb.className = "count-badge";
      cb.textContent = `×${s.count}`;
      cb.title = `${s.count} owned`;
      card.appendChild(cb);
    }

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

  function render(stickers) {
    const filter = filterEl.value;
    const status = statusEl.value;
    const grouped = groupEl.checked;

    const visible = stickers.filter(
      (s) =>
        (filter === "__all__" || s.country === filter) &&
        matchesStatus(s, status)
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
    const orderedCountries = [...byCountry.keys()].sort(compareCountries);

    for (const country of orderedCountries) {
      const items = byCountry.get(country);
      const section = document.createElement("section");
      section.className = "country-group";

      const title = document.createElement("h2");
      title.className = "country-group-title";
      const flag = flagFor(country);
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
    const stickers = rows.filter(includeSticker).map((r) => toSticker(r, got));

    const countries = [...new Set(stickers.map((s) => s.country))].sort(compareCountries);
    for (const c of countries) {
      const opt = document.createElement("option");
      opt.value = c;
      const flag = flagFor(c);
      opt.textContent = `${flag ? flag + " " : ""}${c}`;
      filterEl.appendChild(opt);
    }

    filterEl.addEventListener("change", () => render(stickers));
    statusEl.addEventListener("change", () => render(stickers));
    groupEl.addEventListener("change", () => render(stickers));
    render(stickers);
  }

  init();
})();
