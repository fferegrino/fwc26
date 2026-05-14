var STICKER_COUNT_SUFFIX_RE = /^\s*([^(]+?)\s*\(\s*(\d+)\s*\)\s*$/;

function expandAmpersandToken(token) {
  if (token.indexOf("&") === -1) return [token];
  var parts = token.split("&");
  var out = [];
  var prefix = "";
  for (var i = 0; i < parts.length; i++) {
    var part = parts[i].trim();
    if (!part) continue;
    var pm = part.match(/^([^\d(]+)/);
    if (pm) {
      prefix = pm[1].trim();
      out.push(part);
    } else {
      out.push(prefix + part);
    }
  }
  return out;
}

/** Letter/digit-style codes: stem is all but the trailing digit run (e.g. BIH + 10). */
function stemFromStickerCode(code) {
  var m = String(code).trim().match(/^(.+?)(\d+)$/);
  return m ? m[1] : null;
}

/** Expand a range like "SWE7-9" into ["SWE7","SWE8","SWE9"]. */
function expandRangeToken(token) {
  var m = token.match(/^(.*?)(\d+)\s*-\s*(\d+)$/);
  if (!m) return [token];
  var prefix = m[1];
  var start = parseInt(m[2], 10);
  var end = parseInt(m[3], 10);
  if (!isFinite(start) || !isFinite(end) || end < start) return [token];
  var out = [];
  for (var i = start; i <= end; i++) out.push(prefix + i);
  return out;
}

function parseStickerCsv(text) {
  var raw = text.toUpperCase().split(",");
  var out = [];
  var lastStem = null;
  for (var i = 0; i < raw.length; i++) {
    var token = raw[i].trim();
    if (!token) continue;
    if (/^\d+(\s*-\s*\d+)?$/.test(token)) {
      if (lastStem != null) {
        token = lastStem + token;
      }
    }
    var subTokens = expandAmpersandToken(token);
    for (var s = 0; s < subTokens.length; s++) {
      var sub = subTokens[s];
      var m = sub.match(STICKER_COUNT_SUFFIX_RE);
      var codes, count;
      if (m) {
        codes = expandRangeToken(m[1].trim());
        count = parseInt(m[2], 10);
        if (!isFinite(count) || count <= 0) continue;
      } else {
        codes = expandRangeToken(sub);
        count = 1;
      }
      for (var c = 0; c < codes.length; c++) {
        var code = codes[c];
        if (!code) continue;
        lastStem = stemFromStickerCode(code) || lastStem;
        for (var j = 0; j < count; j++) out.push(code);
      }
    }
  }
  return out;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    parseStickerCsv: parseStickerCsv,
    expandAmpersandToken: expandAmpersandToken,
    expandRangeToken: expandRangeToken,
  };
}
