/* Behavior for a listing-kit page. No framework. Reads settings from #listing-data. */
(function () {
  'use strict';
  var data = JSON.parse(document.getElementById('listing-data').textContent);
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  /* ---------- gallery ---------- */
  var track = $('#track');
  var figs = $$('figure', track);
  var counter = $('#gal-count');
  var current = 0;

  function goTo(i) {
    i = Math.max(0, Math.min(figs.length - 1, i));
    track.scrollTo({ left: figs[i].offsetLeft - track.offsetLeft, behavior: 'smooth' });
  }
  function updateCounter() {
    var w = track.clientWidth || 1;
    current = Math.round(track.scrollLeft / w);
    if (counter) counter.textContent = (current + 1) + ' / ' + figs.length;
  }
  if (track && figs.length) {
    track.addEventListener('scroll', function () { window.requestAnimationFrame(updateCounter); }, { passive: true });
    $('#gal-prev').addEventListener('click', function () { goTo(current - 1); });
    $('#gal-next').addEventListener('click', function () { goTo(current + 1); });
    track.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') { e.preventDefault(); goTo(current + 1); }
      if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(current - 1); }
    });
    updateCounter();
  }

  /* ---------- lightbox ---------- */
  var lb = $('#lightbox');
  var lbImg = $('#lb-img');
  var lbCap = $('#lb-cap');
  var lbIndex = 0;
  var photos = data.photos || [];

  function showLb(i) {
    lbIndex = (i + photos.length) % photos.length;
    var p = photos[lbIndex];
    lbImg.src = p.large;
    lbImg.alt = p.alt;
    lbCap.textContent = (p.caption || p.alt) + '  (' + (lbIndex + 1) + ' of ' + photos.length + ')';
  }
  if (lb && typeof lb.showModal === 'function') {
    $$('button.open', track).forEach(function (b, i) {
      b.addEventListener('click', function () { showLb(i); lb.showModal(); });
    });
    $('#lb-close').addEventListener('click', function () { lb.close(); });
    $('#lb-prev').addEventListener('click', function () { showLb(lbIndex - 1); });
    $('#lb-next').addEventListener('click', function () { showLb(lbIndex + 1); });
    lb.addEventListener('keydown', function (e) {
      if (e.key === 'ArrowRight') showLb(lbIndex + 1);
      if (e.key === 'ArrowLeft') showLb(lbIndex - 1);
    });
    lb.addEventListener('click', function (e) { if (e.target === lb) lb.close(); });
    var startX = null;
    lb.addEventListener('pointerdown', function (e) { startX = e.clientX; });
    lb.addEventListener('pointerup', function (e) {
      if (startX === null) return;
      var dx = e.clientX - startX;
      startX = null;
      if (Math.abs(dx) > 50) showLb(lbIndex + (dx < 0 ? 1 : -1));
    });
  }

  /* ---------- open houses: mark ended ones ---------- */
  $$('[data-end]').forEach(function (li) {
    if (new Date(li.getAttribute('data-end')).getTime() < Date.now()) {
      li.classList.add('past');
      var tag = document.createElement('span');
      tag.className = 'note';
      tag.textContent = 'This open house has ended.';
      $('.when', li).appendChild(tag);
    }
  });

  /* ---------- map, loaded only when it nears the screen ---------- */
  var mapEl = $('#map');
  function loadMap() {
    var css = document.createElement('link');
    css.rel = 'stylesheet';
    css.href = data.assets + 'leaflet/leaflet.css';
    document.head.appendChild(css);
    var js = document.createElement('script');
    js.src = data.assets + 'leaflet/leaflet.js';
    js.onload = function () {
      var m = data.map;
      var map = window.L.map(mapEl, { scrollWheelZoom: false }).setView([m.lat, m.lng], m.zoom);
      window.L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
        maxZoom: 19,
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      }).addTo(map);
      if (m.approximate) {
        window.L.circle([m.lat, m.lng], { radius: 350, color: data.accent, fillColor: data.accent, fillOpacity: 0.2 }).addTo(map);
      } else {
        var icon = window.L.divIcon({ className: '', html: '<div class="pin"></div>', iconSize: [26, 26], iconAnchor: [13, 26] });
        window.L.marker([m.lat, m.lng], { icon: icon, keyboard: false, alt: data.title }).addTo(map);
      }
    };
    document.head.appendChild(js);
  }
  if (mapEl) {
    if ('IntersectionObserver' in window) {
      var io = new IntersectionObserver(function (entries) {
        if (entries[0].isIntersecting) { io.disconnect(); loadMap(); }
      }, { rootMargin: '300px' });
      io.observe(mapEl);
    } else {
      loadMap();
    }
  }

  /* ---------- mortgage estimate ---------- */
  var mform = $('#mortgage-form');
  var money = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
  function num(id) { return parseFloat($('#' + id).value) || 0; }
  function recalc() {
    var r = window.Mortgage.monthlyPayment({
      price: num('m-price'), downPct: num('m-down'), ratePct: num('m-rate'), years: Math.max(1, num('m-years')),
      taxRatePct: num('m-tax'), insurancePerYear: num('m-ins'), hoaMonthly: data.mortgage.hoaMonthly
    });
    $('#m-total').textContent = money.format(r.total) + ' / month';
    $('#m-pi').textContent = money.format(r.principal_interest);
    $('#m-taxo').textContent = money.format(r.tax);
    $('#m-inso').textContent = money.format(r.insurance);
    $('#m-hoao').textContent = money.format(r.hoa);
    $('#m-loan').textContent = money.format(r.loan);
  }
  if (mform) {
    mform.addEventListener('input', recalc);
    mform.addEventListener('submit', function (e) { e.preventDefault(); recalc(); });
    recalc();
  }

  /* ---------- lead form: mailto, or a form endpoint ---------- */
  var lead = $('#lead-form');
  var leadStatus = $('#lead-status');
  function say(msg, ok) {
    leadStatus.className = ok ? 'status-ok' : 'status-err';
    leadStatus.textContent = msg;
  }
  if (lead) {
    lead.addEventListener('submit', function (e) {
      if (lead.elements._gotcha && lead.elements._gotcha.value) { e.preventDefault(); return; }
      var f = lead.elements;
      var body = 'Name: ' + f.name.value + '\nEmail: ' + f.email.value + '\nPhone: ' + f.phone.value + '\n\n' + f.message.value;
      var subject = 'Question about ' + data.title;
      var href = 'mailto:' + data.lead.email + '?subject=' + encodeURIComponent(subject) + '&body=' + encodeURIComponent(body);
      e.preventDefault();
      if (data.lead.mode === 'endpoint') {
        var fd = new FormData(lead);
        fetch(data.lead.endpoint, { method: 'POST', body: fd, headers: { Accept: 'application/json' } })
          .then(function (res) {
            if (!res.ok) throw new Error('bad status');
            lead.reset();
            say('Thanks. Your message was sent.', true);
          })
          .catch(function () {
            say('The message could not be sent. Use the email link below instead.', false);
            var a = document.createElement('a');
            a.href = href;
            a.textContent = ' Email the agent';
            leadStatus.appendChild(a);
          });
      } else {
        window.location.href = href;
        say('Your email app should open with the message filled in. If it did not, email ' + data.lead.email + ' directly.', true);
      }
    });
  }

  /* ---------- share ---------- */
  var url = window.location.href.split('#')[0];
  var text = data.title + ' at ' + data.address;
  var map = {
    'share-email': 'mailto:?subject=' + encodeURIComponent(text) + '&body=' + encodeURIComponent(url),
    'share-sms': 'sms:?&body=' + encodeURIComponent(text + ' ' + url),
    'share-fb': 'https://www.facebook.com/sharer/sharer.php?u=' + encodeURIComponent(url),
    'share-x': 'https://twitter.com/intent/tweet?text=' + encodeURIComponent(text) + '&url=' + encodeURIComponent(url)
  };
  Object.keys(map).forEach(function (id) { var a = document.getElementById(id); if (a) a.href = map[id]; });
  var copy = $('#share-copy');
  if (copy) {
    copy.addEventListener('click', function () {
      var done = function () { copy.textContent = 'Link copied'; setTimeout(function () { copy.textContent = 'Copy link'; }, 2000); };
      if (navigator.clipboard) navigator.clipboard.writeText(url).then(done, function () { window.prompt('Copy this link', url); });
      else window.prompt('Copy this link', url);
    });
  }
  var native = $('#share-native');
  if (native && navigator.share) {
    native.hidden = false;
    native.addEventListener('click', function () { navigator.share({ title: data.title, text: text, url: url }).catch(function () {}); });
  }
  var pr = $('#print-btn');
  if (pr) pr.addEventListener('click', function () { window.print(); });
})();
