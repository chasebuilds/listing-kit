/* Fair-housing wording checker engine. Same logic as listing_kit/fairhousing.py.
   Works in the browser (window.FairHousing) and in Node (module.exports). A writing aid, not legal advice. */
(function (root) {
  'use strict';

  /* Curly quotes and en/em dashes become ASCII, one character for one character. */
  var FOLD = { 0x2019: "'", 0x2018: "'", 0x201c: '"', 0x201d: '"', 0x2013: '-', 0x2014: '-' };

  function normalize(text) {
    var out = '';
    for (var i = 0; i < text.length; i++) {
      var code = text.charCodeAt(i);
      out += FOLD[code] || text.charAt(i);
    }
    return out;
  }

  function check(text, data) {
    var folded = normalize(text);
    var win = data.window;
    var found = [];
    data.rules.forEach(function (rule) {
      var re = new RegExp(rule.pattern, 'gi');
      var unless = (rule.unless || []).map(function (u) { return new RegExp(u, 'i'); });
      var m;
      while ((m = re.exec(folded)) !== null) {
        if (m[0].length === 0) { re.lastIndex++; continue; }
        var lo = Math.max(0, m.index - win);
        var hi = Math.min(folded.length, m.index + m[0].length + win);
        var around = folded.slice(lo, hi);
        if (unless.some(function (u) { return u.test(around); })) continue;
        found.push({
          rule_id: rule.id, category: rule.category, severity: rule.severity, basis: rule.basis || 'judgment',
          start: m.index, end: m.index + m[0].length, match: text.slice(m.index, m.index + m[0].length),
          reason: rule.reason, suggest: rule.suggest
        });
      }
    });
    found.sort(function (a, b) { return a.start - b.start || (a.rule_id < b.rule_id ? -1 : a.rule_id > b.rule_id ? 1 : 0); });
    return found;
  }

  function flags(findings) {
    return findings.filter(function (f) { return f.severity === 'avoid' || f.severity === 'review'; });
  }

  var api = { normalize: normalize, check: check, flags: flags };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.FairHousing = api;
})(typeof window !== 'undefined' ? window : globalThis);
