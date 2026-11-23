/* In-page wording checker UI. Uses FairHousing from checker.js. Text never leaves the browser. */
(function () {
  'use strict';
  var rules = JSON.parse(document.getElementById('rules-data').textContent);
  var box = document.getElementById('text');
  var preview = document.getElementById('preview');
  var list = document.getElementById('findings');
  var summary = document.getElementById('summary');
  var sample = box.value;
  var RANK = { note: 1, review: 2, avoid: 3 };

  function el(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text !== undefined) e.textContent = text;
    return e;
  }

  function renderPreview(text, findings) {
    preview.textContent = '';
    var level = new Array(text.length).fill(0);
    findings.forEach(function (f) {
      for (var i = f.start; i < f.end; i++) level[i] = Math.max(level[i], RANK[f.severity]);
    });
    var names = ['', 'note', 'review', 'avoid'];
    var i = 0;
    while (i < text.length) {
      var j = i;
      while (j < text.length && level[j] === level[i]) j++;
      var chunk = text.slice(i, j);
      if (level[i]) {
        var m = el('mark', names[level[i]], chunk);
        m.setAttribute('title', names[level[i]]);
        preview.appendChild(m);
      } else {
        preview.appendChild(document.createTextNode(chunk));
      }
      i = j;
    }
  }

  function run() {
    var text = box.value;
    var findings = window.FairHousing.check(text, rules);
    renderPreview(text, findings);
    list.textContent = '';
    var counts = { avoid: 0, review: 0, note: 0 };
    findings.forEach(function (f) { counts[f.severity]++; });
    if (!text.trim()) {
      summary.textContent = 'Paste or type a description above.';
      return;
    }
    if (!findings.length) {
      summary.textContent = 'No marked wording found. That does not mean the text is compliant.';
    } else {
      summary.textContent = counts.avoid + ' to avoid, ' + counts.review + ' to review, ' + counts.note + ' style notes.';
    }
    findings.forEach(function (f) {
      var li = el('li');
      li.appendChild(el('span', 'sev ' + f.severity, f.severity));
      var q = el('q', '', f.match);
      li.appendChild(q);
      li.appendChild(el('div', 'meta', f.category.replace(/_/g, ' ') + ' | rule ' + f.rule_id + ' | basis: ' + f.basis));
      li.appendChild(el('div', '', f.reason));
      var s = el('div');
      s.appendChild(el('strong', '', 'Try instead: '));
      s.appendChild(document.createTextNode(f.suggest));
      li.appendChild(s);
      list.appendChild(li);
    });
  }

  var timer;
  box.addEventListener('input', function () { clearTimeout(timer); timer = setTimeout(run, 150); });
  document.getElementById('run').addEventListener('click', run);
  document.getElementById('sample').addEventListener('click', function () { box.value = sample; run(); });
  document.getElementById('clear').addEventListener('click', function () { box.value = ''; run(); box.focus(); });
  run();
})();
