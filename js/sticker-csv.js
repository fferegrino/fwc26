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

function parseStickerCsv(text) {
  var raw = text.toUpperCase().split(",");
  var out = [];
  var lastStem = null;
  for (var i = 0; i < raw.length; i++) {
    var token = raw[i].trim();
    if (!token) continue;
    if (/^\d+$/.test(token)) {
      if (lastStem != null) {
        token = lastStem + token;
      }
    }
    var subTokens = expandAmpersandToken(token);
    for (var s = 0; s < subTokens.length; s++) {
      var sub = subTokens[s];
      var m = sub.match(STICKER_COUNT_SUFFIX_RE);
      if (m) {
        var code = m[1].trim();
        var n = parseInt(m[2], 10);
        if (!code || !isFinite(n) || n <= 0) continue;
        lastStem = stemFromStickerCode(code) || lastStem;
        for (var j = 0; j < n; j++) out.push(code);
      } else {
        out.push(sub);
        lastStem = stemFromStickerCode(sub) || lastStem;
      }
    }
  }
  return out;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { parseStickerCsv: parseStickerCsv, expandAmpersandToken: expandAmpersandToken };
}
