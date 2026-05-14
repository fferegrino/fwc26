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

function parseStickerCsv(text) {
  var raw = text.split(",");
  var out = [];
  for (var i = 0; i < raw.length; i++) {
    var token = raw[i].trim();
    if (!token) continue;
    var subTokens = expandAmpersandToken(token);
    for (var s = 0; s < subTokens.length; s++) {
      var sub = subTokens[s];
      var m = sub.match(STICKER_COUNT_SUFFIX_RE);
      if (m) {
        var code = m[1].trim();
        var n = parseInt(m[2], 10);
        if (!code || !isFinite(n) || n <= 0) continue;
        for (var j = 0; j < n; j++) out.push(code);
      } else {
        out.push(sub);
      }
    }
  }
  return out;
}
