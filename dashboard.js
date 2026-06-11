/* Boom Bound dashboard — vanilla JS behaviours */
(function () {
  'use strict';

  var PEARL_RATE = 1.82; // EUR per pearl, 2025 rate
  var LS = 'boombound.';

  /* ── weekend-specific URL (?wk=w1 / ?wk=w2) ─────────── */
  var wkParam = new URLSearchParams(location.search).get('wk');
  if (wkParam !== 'w1' && wkParam !== 'w2') wkParam = null;

  /* ── countdowns ─────────────────────────────────────────── */
  var weekends = [
    { id: 'cdW1', name: 'Tomorrowland Weekend 1', dates: '17–19 July 2026',
      start: new Date('2026-07-17T12:00:00+02:00'), end: new Date('2026-07-20T01:00:00+02:00') },
    { id: 'cdW2', name: 'Tomorrowland Weekend 2', dates: '24–26 July 2026',
      start: new Date('2026-07-24T12:00:00+02:00'), end: new Date('2026-07-27T01:00:00+02:00') }
  ];
  function pad(n) { return String(n).padStart(2, '0'); }
  function tick() {
    var now = Date.now();
    weekends.forEach(function (w) {
      var card = document.getElementById(w.id);
      if (!card) return;
      var diff = w.start.getTime() - now;
      if (diff <= 0 && now < w.end.getTime()) {
        card.classList.add('live');
        card.querySelectorAll('.cd-unit b').forEach(function (b) { b.textContent = '00'; });
        return;
      }
      if (diff <= 0) diff = 0;
      var d = Math.floor(diff / 86400000);
      var h = Math.floor(diff / 3600000) % 24;
      var m = Math.floor(diff / 60000) % 60;
      var s = Math.floor(diff / 1000) % 60;
      var map = { d: d, h: pad(h), m: pad(m), s: pad(s) };
      card.querySelectorAll('.cd-unit b').forEach(function (b) {
        b.textContent = map[b.getAttribute('data-u')];
      });
    });
  }
  tick();
  setInterval(tick, 1000);

  if (wkParam) {
    var hideCd = document.getElementById(wkParam === 'w1' ? 'cdW2' : 'cdW1');
    if (hideCd) hideCd.style.display = 'none';
    var cds = document.querySelector('.countdowns');
    if (cds) cds.style.gridTemplateColumns = '1fr';
    var kicker = document.querySelector('.hero .kicker');
    if (kicker) kicker.textContent = 'Summer 2026 · De Schorre · ' + (wkParam === 'w1' ? 'Weekend 1' : 'Weekend 2');
    var heroTitle = document.getElementById('heroTitle');
    if (heroTitle) heroTitle.textContent = 'Tomorrowland Weekend ' + (wkParam === 'w1' ? '1' : '2');
  }

  /* ── shareable countdown (WhatsApp etc.) ─────────────── */
  var logoImg = new Image();
  logoImg.src = 'assets/logo-white.png';
  function cssVar(name, fallback) {
    var v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
  }
  function buildShareCard(w, days) {
    var c = document.createElement('canvas');
    c.width = 1080; c.height = 1080;
    var x = c.getContext('2d');
    var accent = cssVar('--accent', '#c9f24f');
    x.fillStyle = '#141519';
    x.fillRect(0, 0, 1080, 1080);
    x.fillStyle = accent;
    x.fillRect(0, 0, 1080, 8);
    if (logoImg.complete && logoImg.naturalWidth) {
      x.drawImage(logoImg, 540 - 130, 70, 260, 260);
    }
    x.textAlign = 'center';
    try { x.letterSpacing = '6px'; } catch (e) {}
    x.fillStyle = accent;
    x.font = '500 42px "IBM Plex Mono", monospace';
    x.fillText(w.name.toUpperCase(), 540, 430);
    x.fillStyle = '#f4f5f2';
    try { x.letterSpacing = '0px'; } catch (e) {}
    x.font = '500 330px "IBM Plex Mono", monospace';
    x.fillText(String(days), 540, 730);
    try { x.letterSpacing = '10px'; } catch (e) {}
    x.fillStyle = '#9a9da6';
    x.font = '500 40px "IBM Plex Mono", monospace';
    x.fillText(days === 1 ? 'DAY TO GO' : 'DAYS TO GO', 540, 810);
    x.fillStyle = '#f4f5f2';
    try { x.letterSpacing = '2px'; } catch (e) {}
    x.font = '700 52px "Bricolage Grotesque", sans-serif';
    x.fillText(w.dates, 540, 930);
    x.fillStyle = '#9a9da6';
    x.font = '400 30px "IBM Plex Mono", monospace';
    x.fillText('@asyoulikeitfests', 540, 990);
    return c;
  }
  document.querySelectorAll('.cd-share').forEach(function (btn) {
    btn.addEventListener('click', function () {
      var w = weekends.filter(function (k) { return k.id === btn.getAttribute('data-cd'); })[0];
      if (!w) return;
      var days = Math.max(0, Math.ceil((w.start.getTime() - Date.now()) / 86400000));
      var text = days > 0
        ? days + (days === 1 ? ' day' : ' days') + ' until ' + w.name + ' — ' + w.dates
        : w.name + ' is here!';
      var doShare = function () {
        buildShareCard(w, days).toBlob(function (blob) {
          var file = blob ? new File([blob], 'countdown.png', { type: 'image/png' }) : null;
          if (file && navigator.canShare && navigator.canShare({ files: [file] })) {
            navigator.share({ files: [file], text: text, title: w.name }).catch(function () {});
          } else if (navigator.share) {
            navigator.share({ title: w.name, text: text, url: location.href }).catch(function () {});
          } else {
            var full = text + ' ' + location.href;
            (navigator.clipboard ? navigator.clipboard.writeText(full) : Promise.reject()).then(function () {
              var old = btn.textContent;
              btn.textContent = 'Copied to clipboard';
              setTimeout(function () { btn.textContent = old; }, 1800);
            }).catch(function () { window.prompt('Copy this:', full); });
          }
        }, 'image/png');
      };
      if (document.fonts && document.fonts.ready) document.fonts.ready.then(doShare);
      else doShare();
    });
  });

  /* ── pearl converter ────────────────────────────────────── */
  var GBP_EUR = 1.17; // EUR per £1, fallback estimate; refreshed live below
  var inEur = document.getElementById('inEur');
  var inPearls = document.getElementById('inPearls');
  var inGbp = document.getElementById('inGbp');
  function fmt(n, dp) { return Number(n.toFixed(dp === undefined ? 2 : dp)).toString(); }
  function syncFromEur() {
    var v = parseFloat(inEur.value);
    inPearls.value = isFinite(v) ? fmt(v / PEARL_RATE, 1) : '';
    inGbp.value = isFinite(v) ? fmt(v / GBP_EUR) : '';
  }
  function syncFromPearls() {
    var v = parseFloat(inPearls.value);
    inEur.value = isFinite(v) ? fmt(v * PEARL_RATE) : '';
    inGbp.value = isFinite(v) ? fmt(v * PEARL_RATE / GBP_EUR) : '';
  }
  function syncFromGbp() {
    var v = parseFloat(inGbp.value);
    inEur.value = isFinite(v) ? fmt(v * GBP_EUR) : '';
    inPearls.value = isFinite(v) ? fmt(v * GBP_EUR / PEARL_RATE, 1) : '';
  }
  inEur.addEventListener('input', syncFromEur);
  inPearls.addEventListener('input', syncFromPearls);
  inGbp.addEventListener('input', syncFromGbp);
  function updateGbpNotes(live) {
    var note = document.getElementById('gbpRateNote');
    if (note) note.textContent = 'Using £1 = €' + fmt(GBP_EUR) + (live ? ' (live rate).' : '.');
    var pg = document.getElementById('pearlGbp');
    if (pg) pg.textContent = '£' + fmt(PEARL_RATE / GBP_EUR);
  }
  syncFromEur();
  updateGbpNotes(false);
  fetch('https://api.frankfurter.app/latest?from=GBP&to=EUR')
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data && data.rates && isFinite(data.rates.EUR)) {
        GBP_EUR = data.rates.EUR;
        syncFromEur();
        updateGbpNotes(true);
        if (typeof refreshDrinkGbp === 'function') refreshDrinkGbp();
        if (typeof updateRound === 'function') updateRound();
      }
    })
    .catch(function () { /* fallback rate stays */ });

  /* ── top-up helper ──────────────────────────────────────── */
  var planPearls = document.getElementById('planPearls');
  var topupOut = document.getElementById('topupOut');
  function updateTopup() {
    var p = parseFloat(planPearls.value);
    if (!isFinite(p) || p <= 0) { topupOut.innerHTML = 'Enter how many Pearls you expect to spend.'; return; }
    var eurNeeded = p * PEARL_RATE;
    var topup = Math.max(20, Math.ceil(eurNeeded / 20) * 20);
    var bonus = Math.floor(topup / 100) * 2;
    var got = topup / PEARL_RATE + bonus;
    topupOut.innerHTML =
      'That costs <b>€' + fmt(eurNeeded) + '</b>. Top up <b>€' + topup + '</b> (multiples of €20) → ' +
      '<b>' + fmt(topup / PEARL_RATE, 1) + ' Pearls</b>' +
      (bonus ? ' + <b>' + bonus + ' bonus</b> if topped up online early' : '') +
      ' = ' + fmt(got, 1) + ' total.';
  }
  planPearls.addEventListener('input', updateTopup);
  updateTopup();

  /* ── drinks table + round builder ───────────────────────── */
  var DRINKS = [
    ['Water 0.5L', 2],
    ['Soft drink (Coke / Fanta / Sprite)', 2],
    ['Red Bull', 2.5],
    ['Jupiler beer 0.25L', 2],
    ['Hoegaarden Rosée', 2.25],
    ['Corona', 3.5],
    ['Jupiler XL 0.4L', 3.75],
    ['Wine (white / rosé)', 4.75],
    ['Sparkling wine (coupe)', 5.75],
    ['Spirit + mixer (vodka, gin, rum…)', 6.75],
    ['Cocktail', 7.5]
  ];
  var qty = DRINKS.map(function () { return 0; });
  var rowsEl = document.getElementById('drinkRows');
  DRINKS.forEach(function (d, i) {
    var tr = document.createElement('tr');
    tr.innerHTML =
      '<td>' + d[0] + '</td>' +
      '<td class="num pearls">' + d[1] + ' ⚪</td>' +
      '<td class="num">€' + (d[1] * PEARL_RATE).toFixed(2) + '</td>' +
      '<td class="num drink-gbp" data-pearls="' + d[1] + '"></td>' +
      '<td class="num"><div class="stepper">' +
      '<button type="button" data-i="' + i + '" data-d="-1" aria-label="remove">−</button>' +
      '<span class="qty" id="qty-' + i + '">0</span>' +
      '<button type="button" data-i="' + i + '" data-d="1" aria-label="add">+</button>' +
      '</div></td>';
    rowsEl.appendChild(tr);
  });
  function refreshDrinkGbp() {
    document.querySelectorAll('.drink-gbp').forEach(function (td) {
      var p = parseFloat(td.getAttribute('data-pearls'));
      td.textContent = '£' + (p * PEARL_RATE / GBP_EUR).toFixed(2);
    });
  }
  refreshDrinkGbp();
  function updateRound() {
    var count = 0, pearls = 0;
    qty.forEach(function (q, i) {
      count += q;
      pearls += q * DRINKS[i][1];
      document.getElementById('qty-' + i).textContent = q;
    });
    document.getElementById('roundCount').textContent = count;
    document.getElementById('roundPearls').textContent = fmt(pearls, 2) + ' ⚪';
    document.getElementById('roundEur').textContent = '€' + (pearls * PEARL_RATE).toFixed(2);
    document.getElementById('roundGbp').textContent = '£' + (pearls * PEARL_RATE / GBP_EUR).toFixed(2);
  }
  rowsEl.addEventListener('click', function (e) {
    var btn = e.target.closest('button[data-i]');
    if (!btn) return;
    var i = +btn.getAttribute('data-i');
    qty[i] = Math.max(0, qty[i] + (+btn.getAttribute('data-d')));
    updateRound();
  });
  document.getElementById('roundReset').addEventListener('click', function () {
    qty = qty.map(function () { return 0; });
    updateRound();
  });
  updateRound();

  /* ── itinerary notes ────────────────────────────────────── */
  var MAP_MEET = 'https://maps.app.goo.gl/UuAgZRUKoJ6MRKpK9';
  var MAP_DECATHLON = 'https://www.google.com/maps/search/?api=1&query=Decathlon+Breda';
  var ITIN = {
    w1: { title: 'Weekend 1 plan', lines: [
      '<b>Thursday 16 July</b> — Amsterdam Centraal Station meeting point at 11:30 CET · <a href="' + MAP_MEET + '" target="_blank" rel="noopener">meeting point on Google Maps ↗</a>',
      'Decathlon stop: <a href="https://www.decathlon.nl/landing/decathlon-breda/_/R-a-sportwinkel-breda" target="_blank" rel="noopener">Decathlon – Breda ↗</a> · <a href="' + MAP_DECATHLON + '" target="_blank" rel="noopener">on Google Maps ↗</a>',
      '<b>Monday 20 July</b> — Depart DreamVille at 09:30 (CET)',
      'Arrive at Amsterdam Schiphol Airport around 15:00'
    ] },
    w2: { title: 'Weekend 2 plan', lines: [
      '<b>Thursday 23 July</b> — Amsterdam Centraal Station meeting point at 11:30 CET · <a href="' + MAP_MEET + '" target="_blank" rel="noopener">meeting point on Google Maps ↗</a>',
      'Decathlon stop: <a href="https://www.decathlon.nl/landing/decathlon-breda/_/R-a-sportwinkel-breda" target="_blank" rel="noopener">Decathlon – Breda ↗</a> · <a href="' + MAP_DECATHLON + '" target="_blank" rel="noopener">on Google Maps ↗</a>',
      '<b>Monday 27 July</b> — Depart DreamVille at 09:30 (CET)',
      'Arrive at Amsterdam Schiphol Airport around 15:00'
    ] }
  };
  var itinGrid = document.getElementById('itinGrid');
  var itinTabs = document.getElementById('itinTabs');
  var currentWk = wkParam || localStorage.getItem(LS + 'itin.tab') || 'w1';
  function renderItin() {
    itinGrid.innerHTML = '';
    var wk = ITIN[currentWk];
    var div = document.createElement('div');
    div.className = 'itin-day';
    var h = document.createElement('h4');
    h.textContent = wk.title;
    div.appendChild(h);
    var ul = document.createElement('ul');
    ul.className = 'itin-plan';
    wk.lines.forEach(function (item) {
      var li = document.createElement('li');
      li.innerHTML = item;
      ul.appendChild(li);
    });
    div.appendChild(ul);
    itinGrid.appendChild(div);
    itinTabs.querySelectorAll('button').forEach(function (b) {
      b.classList.toggle('active', b.getAttribute('data-wk') === currentWk);
    });
  }
  itinTabs.addEventListener('click', function (e) {
    var b = e.target.closest('button[data-wk]');
    if (!b) return;
    currentWk = b.getAttribute('data-wk');
    localStorage.setItem(LS + 'itin.tab', currentWk);
    renderItin();
  });
  renderItin();
  if (wkParam) itinTabs.style.display = 'none';


  /* ── weather: Boom, Belgium via Open-Meteo ───────────── */
  var WMO = function (c) {
    if (c === 0) return 'Clear';
    if (c <= 2) return 'Partly cloudy';
    if (c === 3) return 'Overcast';
    if (c <= 49) return 'Fog';
    if (c <= 59) return 'Drizzle';
    if (c <= 69) return 'Rain';
    if (c <= 84) return 'Showers';
    return 'Storm';
  };
  (function loadWeather() {
    var now = document.getElementById('weatherNow');
    var days = document.getElementById('weatherDays');
    if (!now) return;
    fetch('https://api.open-meteo.com/v1/forecast?latitude=51.088&longitude=4.366&current=temperature_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Europe%2FBrussels&forecast_days=7')
      .then(function (r) { return r.json(); })
      .then(function (data) {
        now.innerHTML = '<b>' + Math.round(data.current.temperature_2m) + '°C</b>' +
          '<span>' + WMO(data.current.weather_code) + ' · right now in Boom</span>';
        var d = data.daily;
        days.innerHTML = d.time.map(function (t, i) {
          var wd = new Date(t + 'T12:00:00').toLocaleDateString('en-GB', { weekday: 'short' });
          return '<div class="weather-day">' +
            '<div class="wd">' + wd + '</div>' +
            '<div class="wc">' + WMO(d.weather_code[i]) + '</div>' +
            '<div class="wt">' + Math.round(d.temperature_2m_max[i]) + '° <small>' + Math.round(d.temperature_2m_min[i]) + '°</small></div>' +
            '<div class="wc">' + d.precipitation_probability_max[i] + '% rain</div>' +
            '</div>';
        }).join('');
      })
      .catch(function () {
        now.innerHTML = '<span>Forecast unavailable right now — check back later.</span>';
      });
  })();

  /* ── packing checklist ──────────────────────────────────── */
  var PACK = [
    ['Clothing', [
      'Comfortable shoes', 'Slides / Crocs', 'Socks (bring more than you think)', 'Underwear',
      'Clothes (for five days)', 'Tracksuit', 'Hoodie / jumper', 'Spray / rain jacket or poncho',
      'Swim shorts / bikini (optional)', 'Boots / gummies / wellies (if any chance of rain)',
      'Thermals / warm clothes (to sleep in)'
    ]],
    ['Toiletries / Hygiene', [
      'Sunscreen', 'Lip balm', 'Toothbrush', 'Toothpaste', 'Deodorant', 'Dry shampoo',
      'Wet wipes / baby wipes', 'Hairspray / wax', 'Towel (quick-dry swimming towels are great)',
      'Baby powder / petroleum jelly (for chafing)', 'Hand sanitiser', 'Hairbrush', 'Moisturiser'
    ]],
    ['Camping', [
      'Tent and air mattress (if not included)', "Don't forget the pump!",
      'Sleeping bag and pillow (if not included)', 'Small padlock for tent (avoid physical keys)',
      'Noise-cancelling headphones / earplugs', 'Bin bags / plastic bags',
      'Small light for campsite (head torches are great)', 'Tarp (especially if rain is likely)',
      'Speaker', 'Extra batteries', 'Camp chair', 'Duct tape', 'Plates / cutlery', 'Zip lock bags'
    ]],
    ['General Essentials', [
      'Ticket (printed out & downloaded on phone)', 'A form of ID (foreign licences usually accepted)',
      'Cash as a backup', 'Phone', "Power bank & cord (don't rely on charging stations)",
      'Earplugs', 'Condoms / contraceptives', 'Spare bottlecaps (festicaps are worth it)',
      'Sunglasses / hats etc.', 'Walkie-talkies for the group (service is usually okay)'
    ]],
    ['Festival Essentials', [
      'Bum bag or small bag (it will be searched)', 'Chewing gum / sweets for glucose',
      'Mini sunscreen tube', 'Band-aids & blister patches', 'Earplugs',
      'Festival map downloaded on your phone', 'FULLY charged phone'
    ]],
    ['Camping Drinks / Food', [
      'Water bottles (varying sizes)', 'Liquor IN PLASTIC BOTTLES', 'Mixers (OJ, Coke, Red Bull etc.)',
      'Beers (can be bought in Mag Greens too)', 'Non-perishable food and snacks',
      'Carb-heavy snacks (for the hangovers)', 'Sugar-heavy food / drinks (for the glucose)', 'Protein bars'
    ]],
    ['First Aid / Medical', [
      'Panadol', 'Ibuprofen', 'Aspirin', 'Electrolyte tablets / powder', 'Band-aids',
      'Deep Heat (great on the final days)', 'Blister patches',
      'Personal medication (in proper box; doctor\u2019s note if controlled)', 'Menstrual products',
      'Fungal cream (athlete\u2019s foot from showers etc.)'
    ]],
    ['Optional Extras', [
      'Disposable camera', 'Vitamins / supplements', 'Jewellery', 'Glasses', 'Small mirror',
      'Camelbak (dedicated hydration / convenient daydrinking)', 'Eye mask', 'Eyedrops',
      'Rolling papers', 'Lighter', 'Vape', 'Aloe vera lotion', 'Test strips', 'Flag',
      'Battery-operated fan', 'Extra towel', 'Thermos', 'Umbrella (for campsite)',
      'Uno / deck of cards', 'Football'
    ]]
  ];
  function slug(s) { return s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 40); }
  var packCats = document.getElementById('packCats');
  PACK.forEach(function (cat) {
    var catName = cat[0], items = cat[1];
    var box = document.createElement('div');
    box.className = 'pack-cat';
    var h = document.createElement('h3');
    var counter = document.createElement('span');
    counter.className = 'count';
    h.textContent = catName + ' ';
    h.appendChild(counter);
    box.appendChild(h);
    var grid = document.createElement('div');
    grid.className = 'check-grid pack';
    var cbs = [];
    function updateCount() {
      var done = cbs.filter(function (c) { return c.checked; }).length;
      counter.textContent = done + '/' + items.length;
      counter.classList.toggle('all-done', done === items.length);
    }
    items.forEach(function (item) {
      var key = LS + 'pack.' + slug(catName) + '.' + slug(item);
      var label = document.createElement('label');
      var cb = document.createElement('input');
      cb.type = 'checkbox';
      cb.checked = localStorage.getItem(key) === '1';
      label.classList.toggle('done', cb.checked);
      cb.addEventListener('change', function () {
        localStorage.setItem(key, cb.checked ? '1' : '0');
        label.classList.toggle('done', cb.checked);
        updateCount();
      });
      var span = document.createElement('span');
      span.textContent = item;
      label.appendChild(cb);
      label.appendChild(span);
      grid.appendChild(label);
      cbs.push(cb);
    });
    box.appendChild(grid);
    packCats.appendChild(box);
    updateCount();
  });
})();
