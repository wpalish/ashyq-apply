/*
 * «Горизонт» short: every pixel is a pure function of time.
 *
 * render(t) sets each element's state from t alone: no CSS transitions and no
 * requestAnimationFrame in the path, so frame N is the same on every run and
 * render.mjs can step through time at any speed. The beat sheet is PLAN.md §3.
 *
 * Numbers come from the demo run (ai-team/outputs/c1-t18-a1/logs/qa_t18_a3_seed.log)
 * and the demo corpus; build/data.js carries the globe's land dots and the
 * result cities from PR #20's table, and render.mjs asserts the counts.
 */
'use strict';

/* ------------------------------------------------------------------ copy -- */
// All on-screen words in one place, so the vocabulary check (PLAN.md §6) can read them.
const COPY = {
  h1: ['Найди,', 'где учиться'],
  h2: ['Сверь себя', 'с требованиями'],
  h3: ['Посчитай', 'настоящую цену'],
  h4: ['Проверь', 'каждый факт'],
  h5: ['Поделись', 'своим маршрутом'],
  hero2: ['Нет данных —', 'так и скажем'],
  demo: 'Демо-данные · цифры для примера',
  search: { what: 'Что изучать', where: 'Куда', budget: 'Бюджет в год', whatV: 'Computer Science', whereV: 'Весь мир', budgetV: 'до $6 000', go: 'Показать программы' },
  research: {
    kicker: 'Поиск идёт', title: 'Читаем сайты вузов за тебя',
    pages: 'страниц прочитано', facts: 'фактов, у каждого — источник',
    steps: ['Открываем страницы вузов', 'Сверяем требования с профилем', 'Считаем деньги после гранта', 'Проверяем сроки и даты'],
    note: '14 страниц не открылись — так и отмечено',
  },
  found: 'Нашли<br><em>20 программ</em><br>в 15 странах',
  pin: 'Гронинген · $1 848 в год',
  prog: {
    name: 'University of Groningen', sub: 'BSc Computing Science · Нидерланды · осень 2027',
    price: '$1 848', per: 'в год после гранта',
    rows: [
      { k: 'Требования', tone: 'warn', v: 'Ждём: оценка по математике', s: 'нужна для заявки' },
      { k: 'Профиль', tone: 'ok', v: 'Выше требований', s: 'отбор всё равно конкурсный' },
      { k: 'Деньги', tone: 'ok', v: 'Грант: учёба и проживание', s: 'Talent Grant · rug.nl · 14 сентября' },
    ],
  },
  money: {
    kicker: 'Деньги за год · Гронинген',
    rows: [['Обучение', 16500], ['Сборы', 600], ['Жильё', 7200], ['Питание', 3600], ['Страховка и книги', 2150]],
    total: 'Итого', grant: 'Talent Grant', rest: 'Остаётся',
    usd: '$1 848', per: 'в год',
    rate: 'По курсу $1 = €0.92 на 1 августа 2026', budget: 'В бюджете: до $6 000 в год',
  },
  quote: {
    kicker: 'Цитата со страницы гранта', title: 'Groningen Talent Grant',
    text: '«Covers tuition, all mandatory university fees, university housing and a meal allowance.»',
    val: '€28 350 в год · на 2026/27',
    stamp: 'rug.nl · страница гранта · проверено 14 сентября',
    nodataT: 'University of Vienna · итог не посчитан',
    nodataS: 'На сайте нет цены за питание. Мы не угадываем.',
  },
  plan: {
    kicker: 'План', title: 'Ближайший срок',
    flaps: ['0', '1', ' ', 'Д', 'Е', 'К'],
    who: 'University of Tokyo · PEAK <span>· 1 декабря 2026</span>',
    rows: [['Токио', '1 декабря'], ['Торонто', '15 января'], ['Гронинген', '1 мая']],
  },
  hero: { sub: 'фактов — <b>у каждого ссылка на сайт вуза и дата</b>', sub2: 'Угадывать не будем.' },
  stories: {
    brand: 'ASHYQ', demo: 'ДЕМО-ДАННЫЕ',
    a: { k: 'Мой маршрут', from: 'Казахстан', to: 'Гронинген', sub: 'BSc Computing Science · осень 2027', pill: 'Грант: учёба и проживание', src: 'rug.nl · проверено 14 сентября' },
    b: { uni: 'University of Tokyo · PEAK', h: 'Требования выполнены', rows: [['✓ IELTS', 'выше минимума 6.5'], ['✓ SAT', 'выше минимума 1 300'], ['→ Собеседование', 'впереди']], foot: 'По требованиям с u-tokyo.ac.jp · 14 сентября. Решение о приёме — за университетом.' },
    c: { h: 'Моя карта поступления', stats: [['20', 'программ'], ['15', 'стран'], ['3', 'в бюджете']], first: 'Первый срок — 1 декабря, Токио', src: 'Цены и сроки — с сайтов вузов · 14 сентября', band: 'ASHYQ Apply' },
  },
  end: { word: 'ASHYQ', apply: 'Apply', tag: 'Вузы и гранты —<br>с источником у каждой цифры', disc: 'В ролике демо-данные.<br>Решение о приёме и гранте — за университетом.' },
};

/* ------------------------------------------------------------- helpers -- */
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const prog = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, x) => a + (b - a) * x;
const E = {
  out: (x) => 1 - Math.pow(1 - x, 3),
  expo: (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
  inOut: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  in: (x) => x * x * x,
  back: (x) => { const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
};
const $ = (sel, root = document) => root.querySelector(sel);
function h(tag, attrs = {}, html = '') {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) el.setAttribute(k, v);
  if (html) el.innerHTML = html;
  return el;
}
function style(el, o) {
  if (o.o !== undefined) el.style.opacity = String(clamp(o.o));
  if (o.tf !== undefined) el.style.transform = o.tf;
  if (o.blur !== undefined) el.style.filter = o.blur > 0.05 ? `blur(${o.blur.toFixed(2)}px)` : 'none';
}
const eur = (n) => '€' + n.toLocaleString('ru-RU').replace(/ /g, ' ');
const sunSVG = (size, sun = '#FFC23D', door = '#0F1E36') =>
  `<svg class="sunmark" width="${size}" height="${size}" viewBox="0 0 32 32"><circle cx="16" cy="16" r="16" fill="${sun}"/><path d="M10.5 32V22.5a5.5 5.5 0 0 1 11 0V32Z" fill="${door}"/></svg>`;

/* ---------------------------------------------------------------- globe -- */
// PR #20's arithmetic (frontend/src/lib/globe.ts): orthographic, unit sphere,
// the 8 441 Natural Earth dots, great circles lifted towards the middle.
const RAD = Math.PI / 180;
const LAND = (() => {
  const bin = atob(window.GLOBE.land);
  const bytes = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i += 1) bytes[i] = bin.charCodeAt(i);
  const packed = new Int16Array(bytes.buffer);
  const out = new Float32Array(packed.length);
  for (let i = 0; i < packed.length; i += 1) out[i] = (packed[i] / 100) * RAD;
  return out;
})();
function projectRad(lat, lon, lat0, lon0, lift = 0) {
  const cosLat = Math.cos(lat), dl = lon - lon0, r = 1 + lift;
  return {
    x: r * cosLat * Math.sin(dl),
    y: r * (Math.cos(lat0) * Math.sin(lat) - Math.sin(lat0) * cosLat * Math.cos(dl)),
    z: r * (Math.sin(lat0) * Math.sin(lat) + Math.cos(lat0) * cosLat * Math.cos(dl)),
  };
}
const project = (p, c, lift = 0) => projectRad(p.lat * RAD, p.lon * RAD, c.lat * RAD, c.lon * RAD, lift);
function greatCircle(a, b, steps = 64, height = 0.18) {
  const v = ({ lat, lon }) => [Math.cos(lat * RAD) * Math.cos(lon * RAD), Math.cos(lat * RAD) * Math.sin(lon * RAD), Math.sin(lat * RAD)];
  const va = v(a), vb = v(b);
  const omega = Math.acos(clamp(va[0] * vb[0] + va[1] * vb[1] + va[2] * vb[2], -1, 1));
  const out = [];
  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps, s = Math.sin(omega);
    const wa = Math.sin((1 - t) * omega) / s, wb = Math.sin(t * omega) / s;
    const w = [wa * va[0] + wb * vb[0], wa * va[1] + wb * vb[1], wa * va[2] + wb * vb[2]];
    out.push({ point: { lat: Math.asin(clamp(w[2], -1, 1)) / RAD, lon: Math.atan2(w[1], w[0]) / RAD }, lift: height * Math.sin(Math.PI * t) * Math.min(1, omega / 1.2) });
  }
  return out;
}
function drawGlobe(ctx, g) {
  const { cx, cy, R, center, dot, alpha = 1, size = 3.2, fill } = g;
  const lat0 = center.lat * RAD, lon0 = center.lon * RAD;
  if (fill) {
    const grad = ctx.createRadialGradient(cx - R * 0.3, cy - R * 0.35, R * 0.1, cx, cy, R);
    grad.addColorStop(0, fill[0]); grad.addColorStop(1, fill[1]);
    ctx.globalAlpha = alpha; ctx.fillStyle = grad;
    ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.fill();
  }
  ctx.fillStyle = dot;
  // Two depth bands keep the limb soft without a per-dot alpha change.
  for (const [zMin, zMax, a] of [[0, 0.35, 0.45], [0.35, 1.01, 1]]) {
    ctx.globalAlpha = alpha * a;
    ctx.beginPath();
    for (let i = 0; i < LAND.length; i += 2) {
      const p = projectRad(LAND[i], LAND[i + 1], lat0, lon0);
      if (p.z <= zMin || p.z > zMax) continue;
      const x = cx + R * p.x, y = cy - R * p.y, r = size * (0.55 + 0.45 * p.z);
      ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, Math.PI * 2);
    }
    ctx.fill();
  }
  ctx.globalAlpha = 1;
}
const onGlobe = (g, p, lift = 0) => { const v = project(p, g.center, lift); return { x: g.cx + g.R * v.x, y: g.cy - g.R * v.y, z: v.z, v }; };
function drawRoute(ctx, g, a, b, k, color, width) {
  const pts = greatCircle(a, b, 80).map((q) => onGlobe(g, q.point, q.lift));
  const n = Math.max(1, Math.floor(k * (pts.length - 1)));
  ctx.strokeStyle = color; ctx.lineWidth = width; ctx.lineCap = 'round'; ctx.lineJoin = 'round';
  ctx.beginPath();
  let pen = false;
  for (let i = 0; i <= n; i += 1) {
    const p = pts[i];
    const seen = p.z > 0 || p.v.x * p.v.x + p.v.y * p.v.y > 1;
    if (!seen) { pen = false; continue; }
    if (pen) ctx.lineTo(p.x, p.y); else ctx.moveTo(p.x, p.y);
    pen = true;
  }
  ctx.stroke();
  return pts[n];
}
function marker(ctx, x, y, r, fill, ring, ringW = 5) {
  ctx.globalAlpha = 1;
  ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2);
  if (fill) { ctx.fillStyle = fill; ctx.fill(); }
  if (ring) { ctx.strokeStyle = ring; ctx.lineWidth = ringW; ctx.stroke(); }
}
function label(ctx, text, x, y, color, font = '600 30px Onest', align = 'left') {
  ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align; ctx.textBaseline = 'middle'; ctx.fillText(text, x, y);
}

const P = window.GLOBE.places;         // name → {lat, lon}
const HOME = P.Astana;
const RESULTS = window.GLOBE.results;  // the demo run's 20, each with its city

/* --------------------------------------------------------------- build -- */
const S = {}; // scenes by id
const scenesEl = $('#scenes');
function scene(id, html, cls = '') {
  const el = h('div', { class: `scene ${cls}`, id: `sc-${id}` }, html);
  scenesEl.appendChild(el);
  S[id] = el;
  return el;
}

function headline(id, lines, night = false) {
  let k = 0;
  const html = lines.map((line, li) => {
    const words = line.split(' ').map((w) => `<span class="w" data-k="${k++}">${w}</span>`).join(' ');
    const dot = li === lines.length - 1 ? '<span class="w dot" data-dot="1"></span>' : '';
    return `<span class="line"><span class="lw">${words}${dot}</span></span>`;
  }).join('');
  const el = scene(id, `<div class="headline ${night ? 'night' : ''}">${html}</div>`);
  el.style.opacity = '1';
  return el;
}

headline('h1', COPY.h1);
headline('h2', COPY.h2);
headline('h3', COPY.h3);
headline('h4', COPY.h4);
headline('h5', COPY.h5);
headline('hero2', COPY.hero2, true);

const c = COPY;
scene('start', `
  <div class="card" id="search">
    <div class="brandrow">${sunSVG(56)}<span>ASHYQ <small>Apply</small></span></div>
    <div class="field"><label>${c.search.what}</label><div class="v" id="typed"></div></div>
    <div class="field-row">
      <div class="field"><label>${c.search.where}</label><div class="v" id="whereV">${c.search.whereV}</div></div>
      <div class="field"><label>${c.search.budget}</label><div class="v" id="budgetV">${c.search.budgetV}</div></div>
    </div>
    <div class="btn-sun" id="go"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="#0F1E36" stroke-width="2.6" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="6.5"/><path d="m15.5 15.5 5 5"/></svg>${c.search.go}</div>
  </div>`);
scene('research', `
  <div class="kicker">${c.research.kicker}</div>
  <h2>${c.research.title}</h2>
  <div class="counters"><div class="counter"><b id="nPages">0</b><span>${c.research.pages}</span></div><div class="counter"><b id="nFacts">0</b><span>${c.research.facts}</span></div></div>
  <div class="steps">${c.research.steps.map((s) => `<div class="step"><i></i>${s}</div>`).join('')}</div>
  <div class="bar"><i id="barI"></i></div>
  <div class="note">${c.research.note}</div>`);
scene('found', `<div id="foundText">${c.found}</div>`);
scene('route', `<div id="pin">${c.pin}</div>
  <div class="card" id="prog">
    <h3>${c.prog.name}</h3><div class="sub">${c.prog.sub}</div>
    <div class="pricebox"><b>${c.prog.price}</b><span>${c.prog.per}</span></div>
    ${c.prog.rows.map((r) => `<div class="judg"><b>${r.k}</b><div class="r"><span class="pill ${r.tone}">${r.v}</span><small>${r.s}</small></div></div>`).join('')}
  </div>`);
{
  const sum = c.money.rows.reduce((a, [, v]) => a + v, 0);
  if (sum !== 30050) throw new Error(`money rows add up to ${sum}, not the corpus's €30 050`);
  scene('money', `<div class="card" id="money">
    <div class="kicker">${c.money.kicker}</div><div style="height:26px"></div>
    ${c.money.rows.map(([k, v]) => `<div class="mrow cost"><span>${k}</span><b>${eur(v)}</b></div>`).join('')}
    <div class="mrow total"><span>${c.money.total}</span><b>${eur(sum)}</b></div>
    <div class="mrow grant"><span>${c.money.grant}</span><b>− ${eur(28350)}</b></div>
    <div class="mrow rest"><span>${c.money.rest}</span><b id="restV">${eur(sum)}</b></div>
    <div id="usd">${c.money.usd} <small>${c.money.per}</small></div>
    <div id="rate">${c.money.rate}</div>
    <div id="budget" class="pill ok">✓ ${c.money.budget}</div>
  </div>`);
}
scene('source', `<div class="card" id="quote">
    <div class="kicker">${c.quote.kicker}</div><h3>${c.quote.title}</h3>
    <blockquote><mark id="hl">${c.quote.text}</mark></blockquote>
    <div class="val">${c.quote.val}</div>
    <div id="stamp" class="src">${c.quote.stamp}</div>
  </div>
  <div class="card" id="nodata"><b>${c.quote.nodataT}</b><p>${c.quote.nodataS}</p></div>`);
scene('plan', `<div class="kicker">${c.plan.kicker}</div><h3>${c.plan.title}</h3>
  <div class="flaps">${c.plan.flaps.map((ch) => (ch === ' ' ? '<div class="flap gap"></div>' : `<div class="flap"><span></span><div class="fold"></div></div>`)).join('')}</div>
  <div class="who">${c.plan.who}</div>
  ${c.plan.rows.map(([k, v], i) => `<div class="dl" style="top:${990 + i * 140}px"><b>${k}</b><span>${v}</span></div>`).join('')}`);
scene('hero', `<div id="big">0</div><div id="bigsub">${c.hero.sub}</div>`);
S.hero2.appendChild(h('div', { id: 'nogsub' }, c.hero.sub2));
scene('stories', `
  <div class="story night" id="stA">
    <div class="brandrow" style="color:#fff">${sunSVG(40)}<span>${c.stories.brand}</span></div>
    <div class="dchip">${c.stories.demo}</div>
    <div class="k" style="color:#FFD27A">${c.stories.a.k}</div>
    <h4>${c.stories.a.from}</h4>
    <canvas id="stAarc" width="464" height="130" style="left:38px;top:300px"></canvas>
    <h4 style="text-align:right;margin-top:150px">${c.stories.a.to}</h4>
    <p style="color:#A7B1C2">${c.stories.a.sub}</p>
    <div class="spill" style="background:#12352A;color:#6BE3A4">${c.stories.a.pill}</div>
    <p style="color:#8FD3F4">● ${c.stories.a.src}</p>
    <canvas id="stAglobe" width="540" height="300" style="left:0;bottom:0"></canvas>
  </div>
  <div class="story sunny" id="stB">
    <div class="brandrow">${sunSVG(40, '#0F1E36', '#FFC23D')}<span>${c.stories.brand}</span></div>
    <div class="dchip">${c.stories.demo}</div>
    <div style="margin-top:40px;width:96px;height:96px;border-radius:50%;background:#0F1E36;display:flex;align-items:center;justify-content:center"><svg width="52" height="52" viewBox="0 0 24 24" fill="none" stroke="#FFC23D" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"><path d="m5 12.5 4.5 4.5L19 7.5"/></svg></div>
    <p style="font-weight:700;margin-top:26px">${c.stories.b.uni}</p>
    <h4 style="margin-top:8px">${c.stories.b.h}</h4>
    <div class="req">${c.stories.b.rows.map(([k, v]) => `<div><b>${k}</b><span>${v}</span></div>`).join('')}</div>
    <p style="font-size:20px">${c.stories.b.foot}</p>
  </div>
  <div class="story white" id="stC">
    <div class="brandrow">${sunSVG(40)}<span>${c.stories.brand}</span></div>
    <div class="dchip">${c.stories.demo}</div>
    <h4>${c.stories.c.h}</h4>
    <canvas id="stCglobe" width="464" height="330" style="left:38px;top:300px"></canvas>
    <div class="stats" style="margin-top:360px">${c.stories.c.stats.map(([n, s]) => `<div><b>${n}</b><span>${s}</span></div>`).join('')}</div>
    <p style="font-weight:600">${c.stories.c.first}</p>
    <p class="muted" style="font-size:19px;margin-top:6px">${c.stories.c.src}</p>
    <div class="band">${sunSVG(40)}${c.stories.c.band}</div>
  </div>`);
scene('end', `<canvas id="rays" width="1080" height="1920"></canvas>
  <div class="mark">${sunSVG(200)}</div>
  <div id="word">${c.end.word}<span>${c.end.apply}</span></div>
  <div id="tag">${c.end.tag}</div><div id="disc">${c.end.disc}</div>`);

/* --------------------------------------------------------------- times -- */
// The beat sheet (PLAN.md §3). [in, out] of each scene, in seconds.
const T = {
  h1: [0.0, 1.6], start: [1.5, 3.35], research: [3.55, 4.62], found: [4.6, 5.32], h2: [5.2, 6.4],
  route: [6.3, 9.0], h3: [9.0, 10.2], money: [10.15, 12.62], h4: [12.6, 13.6], source: [13.55, 15.62],
  plan: [15.55, 17.75], hero: [17.9, 19.62], hero2: [19.45, 20.95], h5: [21.0, 22.2], stories: [22.15, 25.65],
  end: [25.6, 30.0],
};
const DURATION = 30;
const HEADLINE_Y = { h1: 840, h2: 840, h3: 840, h4: 840, h5: 840, hero2: 800 };

/* ------------------------------------------------------------- measure -- */
// Positions the render needs (dot centres, the button, the price box), measured
// once after the fonts load, with every transform at rest.
const M = {};
function measure() {
  for (const id of Object.keys(HEADLINE_Y)) {
    const box = $('.headline', S[id]);
    box.style.top = HEADLINE_Y[id] + 'px';
    let size = 128;
    box.style.fontSize = size + 'px';
    const widest = Math.max(...[...box.querySelectorAll('.lw')].map((l) => l.getBoundingClientRect().width));
    size = Math.min(128, Math.floor((size * 880) / widest));
    box.style.fontSize = size + 'px';
    const b = box.getBoundingClientRect();
    box.style.top = HEADLINE_Y[id] - b.height / 2 + 'px';
    const d = $('.dot', box).getBoundingClientRect();
    M[id] = { dot: { x: d.left + d.width / 2, y: d.top + d.height / 2, r: d.width / 2 } };
  }
  const go = $('#go').getBoundingClientRect();
  M.go = { x: go.left + go.width / 2, y: go.top + go.height / 2 };
  const pb = $('#prog .pricebox').getBoundingClientRect();
  M.price = { x: pb.left + pb.width / 2, y: pb.top + pb.height / 2 };
  $('#nogsub').style.top = M.hero2.dot.y + 110 + 'px';
  const word = $('#word');
  M.word = { w: word.getBoundingClientRect().width, h: word.getBoundingClientRect().height };
  drawStoryCanvases();
}

function drawStoryCanvases() {
  // Story A: the route as a dotted line, and the night globe rising under the card.
  const a = $('#stAarc').getContext('2d');
  a.setLineDash([2, 12]); a.lineCap = 'round'; a.strokeStyle = '#FFC23D'; a.lineWidth = 6;
  a.beginPath(); a.moveTo(24, 24); a.quadraticCurveTo(232, 150, 440, 100); a.stroke();
  marker(a, 24, 24, 12, '#FFC23D'); marker(a, 440, 100, 12, null, '#FFC23D', 5);
  const ag = $('#stAglobe').getContext('2d');
  drawGlobe(ag, { cx: 270, cy: 560, R: 420, center: { lat: 20, lon: 40 }, dot: '#3C4E70', size: 3.4 });
  ag.strokeStyle = '#FFC23D'; ag.lineWidth = 5; ag.beginPath(); ag.arc(270, 560, 422, Math.PI * 1.18, Math.PI * 1.82); ag.stroke();
  // Story C: the map with home and the results it can place; the rest are counted in the stats.
  const cg = $('#stCglobe').getContext('2d');
  const g = { cx: 232, cy: 170, R: 158, center: { lat: 38, lon: 45 }, dot: '#9AA4B2', size: 2.1, fill: ['#FFFFFF', '#EEF1F5'] };
  drawGlobe(cg, g);
  drawRoute(cg, g, HOME, P.Groningen, 1, '#E8A317', 4);
  for (const r of RESULTS) { const p = onGlobe(g, P[r.city]); if (p.z > 0.05) marker(cg, p.x, p.y, 6, null, '#E8A317', 3.5); }
  const hp = onGlobe(g, HOME); marker(cg, hp.x, hp.y, 8, '#0F1E36');
}

/* -------------------------------------------------------------- render -- */
const glc = $('#globeLight').getContext('2d');
const gnc = $('#globeNight').getContext('2d');

function headlineAt(id, t, opts = {}) {
  const [t0, t1] = T[id];
  const el = S[id];
  if (t < t0 - 0.01 || t > t1 + 0.4) { el.style.visibility = 'hidden'; return; }
  el.style.visibility = 'visible';
  const words = el.querySelectorAll('.w:not(.dot)');
  const exit = opts.noExit ? 0 : E.inOut(prog(t, t1 - 0.3, t1));
  words.forEach((w, k) => {
    const s = t0 + (opts.delay ?? 0.06) + k * 0.085;
    const q = E.expo(prog(t, s, s + 0.6));
    // A small per-word lag gives the line a wave, like a horizon settling.
    const wave = Math.sin(k * 1.7) * 14 * (1 - q);
    style(w, { o: q * 1.4 * (1 - exit), tf: `translate3d(0, ${((1 - q) * 90 + wave - exit * 60).toFixed(1)}px, 0) scale(${(1 - exit * 0.04).toFixed(3)})`, blur: (1 - q) * 12 + exit * 14 });
  });
  const dot = $('.dot', el);
  const ds = opts.dotAt ?? t0 + (opts.delay ?? 0.06) + words.length * 0.085 + 0.12;
  const dq = E.back(prog(t, ds, ds + 0.4));
  if (opts.dotExit) opts.dotExit(dot, t, dq);
  else style(dot, { o: prog(t, ds, ds + 0.05) * (1 - exit), tf: `scale(${Math.max(0, dq).toFixed(3)})` });
}

function nightClip(t) {
  const el = $('#night');
  let clip = 'circle(0px at 50% 50%)';
  if (t >= 3.2 && t < 3.8) {
    const r = 2300 * E.inOut(prog(t, 3.22, 3.72));
    clip = `circle(${r.toFixed(1)}px at ${M.go.x}px ${M.go.y}px)`;
  } else if (t >= 3.8 && t < 5.2) clip = 'none';
  else if (t >= 5.2 && t < 5.62) {
    const r = 2300 * (1 - E.inOut(prog(t, 5.2, 5.6)));
    clip = `circle(${Math.max(0, r).toFixed(1)}px at ${M.h2.dot.x}px ${M.h2.dot.y}px)`;
  } else if (t >= 17.55 && t < 21.3) {
    // The horizon: a globe's limb rising, then setting.
    const up = E.inOut(prog(t, 17.55, 18.15)), down = E.inOut(prog(t, 20.75, 21.28));
    const top = lerp(1960, -320, up) + (2280 * down);
    const R = 2600;
    clip = `circle(${R}px at 540px ${(top + R).toFixed(1)}px)`;
  }
  el.style.clipPath = clip;
  el.style.visibility = clip.startsWith('circle(0px') ? 'hidden' : 'visible';
  return clip !== 'circle(0px at 50% 50%)';
}

function sceneWindow(id, t, fadeIn = 0.25, fadeOut = 0.25) {
  const [a, b] = T[id];
  const el = S[id];
  const vin = E.out(prog(t, a, a + fadeIn)), vout = E.inOut(prog(t, b - fadeOut, b));
  const on = t >= a && t <= b;
  el.style.visibility = on ? 'visible' : 'hidden';
  el.style.opacity = on ? String(vin * (1 - vout)) : '0';
  return { on, vin, vout, a, b };
}

function render(t) {
  // Background light drifts slowly: the only motion when nothing else moves.
  $('#glow').style.setProperty('--gx', (72 + 10 * Math.sin(t * 0.21)).toFixed(2) + '%');
  $('#glow').style.setProperty('--gy', (10 + 6 * Math.cos(t * 0.17)).toFixed(2) + '%');
  glc.clearRect(0, 0, 1080, 1920);
  gnc.clearRect(0, 0, 1080, 1920);
  const night = nightClip(t);

  // 1 — «Найди, где учиться.» The sun dot drops into the search button.
  headlineAt('h1', t, {
    dotExit: (dot, tt, dq) => {
      const k = E.inOut(prog(tt, 1.3, 1.75));
      const d = M.h1.dot;
      const dx = (M.go.x - d.x) * k, dy = (M.go.y - d.y) * k;
      style(dot, { o: prog(tt, 0.9, 0.95) * (1 - prog(tt, 1.62, 1.8)), tf: `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px) scale(${(Math.max(0, dq) * (1 + k * 2.2)).toFixed(3)})` });
    },
  });

  // 2 — start: the search card over the rising globe.
  {
    const w = sceneWindow('start', t, 0.35, 0.01);
    if (t >= 1.4 && t < 3.9) {
      const rise = E.expo(prog(t, 1.45, 2.4));
      drawGlobe(glc, { cx: 540, cy: lerp(2900, 2280, rise), R: 1100, center: { lat: 32, lon: 58 + t * 5 }, dot: '#9AA4B2', alpha: 0.75, size: 3.6, fill: ['#FFFFFF', '#EEF1F5'] });
      const g = { cx: 540, cy: lerp(2900, 2280, rise), R: 1100, center: { lat: 32, lon: 58 + t * 5 } };
      const hp = onGlobe(g, HOME);
      if (hp.z > 0) { marker(glc, hp.x, hp.y, 13, '#0F1E36'); marker(glc, hp.x, hp.y, 26 + 6 * Math.sin(t * 5), null, 'rgba(15,30,54,0.25)', 3); }
    }
    if (w.on) {
      const q = E.expo(prog(t, 1.5, 2.15));
      style($('#search'), { tf: `translate3d(0, ${((1 - q) * 380).toFixed(1)}px, 0)`, blur: (1 - q) * 10 });
      const n = Math.floor(prog(t, 2.05, 2.7) * c.search.whatV.length);
      const typing = t < 3.1;
      $('#typed').innerHTML = c.search.whatV.slice(0, n) + (typing && Math.floor(t * 3) % 2 === 0 ? '<span class="caret"></span>' : '');
      style($('#whereV'), { o: prog(t, 2.72, 2.85), tf: `translateY(${(1 - E.out(prog(t, 2.72, 2.9))) * 16}px)` });
      style($('#budgetV'), { o: prog(t, 2.86, 3.0), tf: `translateY(${(1 - E.out(prog(t, 2.86, 3.04))) * 16}px)` });
      const press = Math.sin(Math.PI * prog(t, 3.06, 3.26));
      style($('#go'), { tf: `scale(${(1 - press * 0.05).toFixed(3)})` });
    }
  }

  // 2b — the research moment, at night.
  {
    const w = sceneWindow('research', t, 0.2, 0.12);
    if (night && t >= 3.2 && t < 5.7) {
      const g = { cx: 540, cy: lerp(2500, 2150, E.expo(prog(t, 3.4, 4.4))), R: 1000, center: { lat: 34, lon: 48 + t * 6 } };
      drawGlobe(gnc, { ...g, dot: '#3C4E70', size: 3.6 });
      RESULTS.forEach((r, i) => {
        const p = onGlobe(g, P[r.city]);
        const k = E.back(prog(t, 4.6 + i * 0.02, 4.85 + i * 0.02));
        if (p.z > 0.02 && k > 0) marker(gnc, p.x, p.y, 9 * k, '#FFC23D');
      });
      const hp = onGlobe(g, HOME);
      if (hp.z > 0) marker(gnc, hp.x, hp.y, 11, '#fff');
    }
    if (w.on) {
      const t0 = 3.72, step = 0.2;
      $('#nPages').textContent = String(Math.round(E.out(prog(t, t0, 4.5)) * 96));
      $('#nFacts').textContent = String(Math.round(E.out(prog(t, t0 + 0.05, 4.55)) * 414));
      S.research.querySelectorAll('.step').forEach((el, i) => {
        const on = t >= t0 + i * step, done = t >= t0 + (i + 1) * step;
        el.className = 'step' + (done ? ' done' : on ? ' on' : '');
        const icon = el.querySelector('i');
        icon.style.transform = on && !done ? `rotate(${(t * 900) % 360}deg)` : 'none';
        style(el, { o: 0.35 + 0.65 * E.out(prog(t, t0 + i * step - 0.1, t0 + i * step + 0.1)), tf: `translateX(${((1 - E.out(prog(t, 3.55 + i * 0.05, 3.9 + i * 0.05))) * 40).toFixed(1)}px)` });
      });
      $('#barI').style.width = (prog(t, t0, t0 + 4 * step) * 100).toFixed(1) + '%';
      style($('#sc-research .note'), { o: prog(t, 4.35, 4.5) });
      style(S.research, { tf: `translateY(${(-w.vout * 60).toFixed(1)}px)`, blur: w.vout * 10 });
    }
    const f = sceneWindow('found', t, 0.2, 0.14);
    if (f.on) style($('#foundText'), { tf: `translateY(${((1 - E.expo(prog(t, 4.6, 5.0))) * 80).toFixed(1)}px) scale(${(1 + f.vout * 0.06).toFixed(3)})`, blur: (1 - E.expo(prog(t, 4.6, 4.9))) * 12 + f.vout * 10 });
  }

  // 3 — «Сверь себя с требованиями.» The night closes into its full stop.
  headlineAt('h2', t, { delay: 0.18, dotAt: 5.5 });

  // 4 — the route home → Groningen lands on its price, which becomes the programme.
  {
    const w = sceneWindow('route', t, 0.3, 0.3);
    if (t >= 6.3 && t < 9.0) {
      const turn = E.inOut(prog(t, 6.35, 7.5));
      const lift = E.inOut(prog(t, 7.55, 8.1));
      const g = { cx: 540, cy: lerp(1000, 700, lift), R: lerp(600, 440, lift), center: { lat: lerp(40, 49, turn), lon: lerp(64, 36, turn) } };
      const fade = E.out(prog(t, 6.3, 6.6)) * (1 - E.inOut(prog(t, 8.7, 9.0)));
      glc.globalAlpha = fade;
      drawGlobe(glc, { ...g, dot: '#9AA4B2', size: 3.6, alpha: fade, fill: ['#FFFFFF', '#EEF1F5'] });
      glc.globalAlpha = fade;
      const k = E.inOut(prog(t, 6.75, 7.5));
      if (k > 0) drawRoute(glc, g, HOME, P.Groningen, k, '#E8A317', 7);
      const hp = onGlobe(g, HOME), gp = onGlobe(g, P.Groningen);
      marker(glc, hp.x, hp.y, 13 * fade, '#0F1E36');
      label(glc, 'Астана', hp.x + 24, hp.y + 4, `rgba(15,30,54,${fade * (1 - lift)})`);
      const arrive = E.back(prog(t, 7.45, 7.8));
      if (arrive > 0) marker(glc, gp.x, gp.y, 14 * arrive, '#fff', '#E8A317', 6);
      glc.globalAlpha = 1;
      // The pin rides the city, then flies into the card's price.
      const pin = $('#pin');
      const pinIn = E.back(prog(t, 7.5, 7.85)), toCard = E.inOut(prog(t, 7.85, 8.25));
      const px = lerp(gp.x, M.price.x, toCard), py = lerp(gp.y - 70, M.price.y, toCard);
      const pw = pin.offsetWidth, ph = pin.offsetHeight;
      style(pin, { o: prog(t, 7.5, 7.56) * (1 - prog(t, 8.1, 8.25)), tf: `translate(${(px - pw / 2).toFixed(1)}px, ${(py - ph / 2).toFixed(1)}px) scale(${(Math.max(0, pinIn) * (1 - toCard * 0.5)).toFixed(3)})` });
    }
    if (w.on) {
      const q = E.expo(prog(t, 7.8, 8.4));
      style($('#prog'), { o: prog(t, 7.8, 7.95), tf: `translate3d(0, ${((1 - q) * 260).toFixed(1)}px, 0) scale(${(0.94 + 0.06 * q).toFixed(3)})`, blur: (1 - q) * 8 });
      style($('#prog .pricebox'), { o: prog(t, 8.12, 8.25) });
      S.route.querySelectorAll('.judg').forEach((row, i) => {
        const r = E.expo(prog(t, 8.15 + i * 0.16, 8.6 + i * 0.16));
        style(row, { o: r, tf: `translateX(${((1 - r) * 60).toFixed(1)}px)` });
      });
      style(S.route, { tf: `translateY(${(-w.vout * 80).toFixed(1)}px)`, blur: w.vout * 12 });
    }
  }

  // 5 — «Посчитай настоящую цену.»
  headlineAt('h3', t);

  // 6 — the money as arithmetic.
  {
    const w = sceneWindow('money', t, 0.25, 0.22);
    if (w.on) {
      const q = E.expo(prog(t, 10.15, 10.7));
      style($('#money'), { tf: `translate3d(0, ${((1 - q) * 200).toFixed(1)}px, 0) rotate(${((1 - q) * -2).toFixed(2)}deg)`, blur: (1 - q) * 8 + w.vout * 12 });
      S.money.querySelectorAll('.cost').forEach((row, i) => {
        const r = E.expo(prog(t, 10.35 + i * 0.09, 10.75 + i * 0.09));
        style(row, { o: r, tf: `translateY(${((1 - r) * 24).toFixed(1)}px)` });
      });
      style($('#money .total'), { o: E.out(prog(t, 10.85, 11.0)) });
      const g = E.expo(prog(t, 11.1, 11.5));
      style($('#money .grant'), { o: g, tf: `translateX(${((1 - g) * 120).toFixed(1)}px)` });
      style($('#money .rest'), { o: E.out(prog(t, 11.2, 11.35)) });
      const k = E.out(prog(t, 11.25, 11.8));
      $('#restV').textContent = eur(Math.round(lerp(30050, 1700, k) / 50) * 50);
      const u = E.back(prog(t, 11.8, 12.15));
      style($('#usd'), { o: prog(t, 11.8, 11.9), tf: `scale(${(0.85 + 0.15 * Math.max(0, u)).toFixed(3)})` });
      $('#usd').style.transformOrigin = 'left center';
      style($('#rate'), { o: prog(t, 11.95, 12.1) });
      const bq = E.back(prog(t, 12.08, 12.3));
      style($('#budget'), { o: prog(t, 12.08, 12.14), tf: `scale(${(0.8 + 0.2 * Math.max(0, bq)).toFixed(3)})` });
      $('#budget').style.transformOrigin = 'left center';
    }
  }

  // 7 — «Проверь каждый факт.»
  headlineAt('h4', t);

  // 8 — the source: the grant's own words, highlighted and stamped; then what we cannot know.
  {
    const w = sceneWindow('source', t, 0.25, 0.22);
    if (w.on) {
      const q = E.expo(prog(t, 13.55, 14.1));
      style($('#quote'), { tf: `translate3d(0, ${((1 - q) * 200).toFixed(1)}px, 0)`, blur: (1 - q) * 8 + w.vout * 12 });
      $('#hl').style.backgroundSize = `${(E.inOut(prog(t, 13.9, 14.55)) * 100).toFixed(1)}% 100%`;
      style($('#quote .val'), { o: prog(t, 14.3, 14.45) });
      const s = E.back(prog(t, 14.55, 14.85));
      style($('#stamp'), { o: prog(t, 14.55, 14.6), tf: `scale(${(1.25 - 0.25 * Math.max(0, s)).toFixed(3)}) rotate(${((1 - s) * -4).toFixed(2)}deg)` });
      const n = E.expo(prog(t, 14.85, 15.3));
      style($('#nodata'), { o: n, tf: `translateY(${((1 - n) * 120).toFixed(1)}px)`, blur: w.vout * 12 });
    }
  }

  // 9 — the plan: a split-flap board settles on the nearest deadline.
  {
    const w = sceneWindow('plan', t, 0.25, 0.3);
    if (w.on) {
      const pool = 'АБВГДЕЖЗИКЛМНОПРСТ0123456789';
      S.plan.querySelectorAll('.flap:not(.gap)').forEach((flap, i) => {
        const target = c.plan.flaps.filter((ch) => ch !== ' ')[i];
        const settle = 15.9 + i * 0.13;
        const span = flap.querySelector('span'), fold = flap.querySelector('.fold');
        if (t < settle) {
          const step = Math.floor(t / 0.055);
          span.textContent = pool[(step * 7 + i * 5) % pool.length];
          fold.style.transform = `scaleY(${Math.abs(Math.cos(Math.PI * ((t / 0.055) % 1))).toFixed(3)})`;
          fold.style.opacity = '1';
        } else { span.textContent = target; fold.style.opacity = '0'; }
        const inq = E.expo(prog(t, 15.6 + i * 0.05, 16.0 + i * 0.05));
        style(flap, { o: inq, tf: `translateY(${((1 - inq) * 60).toFixed(1)}px)` });
      });
      style($('#sc-plan .who'), { o: prog(t, 16.55, 16.7) });
      S.plan.querySelectorAll('.dl').forEach((row, i) => {
        const r = E.expo(prog(t, 16.7 + i * 0.1, 17.1 + i * 0.1));
        style(row, { o: r, tf: `translateY(${((1 - r) * 80).toFixed(1)}px)` });
        row.style.boxShadow = i === 0 ? 'inset 10px 0 0 #FFC23D, 0 6px 18px rgba(15,30,54,.10)' : '';
      });
      style(S.plan, { tf: `translateY(${(-w.vout * 120).toFixed(1)}px)`, blur: w.vout * 10 });
    }
  }

  // 10 — the hero: night rises as a horizon; 414 facts light the results.
  {
    if (night && t >= 17.55 && t < 21.3) {
      const turn = prog(t, 17.6, 21.2);
      const g = { cx: 540, cy: lerp(2300, 1880, E.expo(prog(t, 17.7, 18.7))), R: 900, center: { lat: 30, lon: lerp(52, 64, turn) } };
      drawGlobe(gnc, { ...g, dot: '#3C4E70', size: 3.8 });
      let hidden = 0;
      const hiddenBy = {};
      RESULTS.forEach((r, i) => {
        const p = onGlobe(g, P[r.city]);
        if (p.z <= 0.02) { hidden += 1; hiddenBy[r.region] = (hiddenBy[r.region] || 0) + 1; return; }
        const k = E.back(prog(t, 18.2 + i * 0.045, 18.5 + i * 0.045));
        if (k <= 0) return;
        marker(gnc, p.x, p.y, 28 * k, 'rgba(255,194,61,0.18)');
        marker(gnc, p.x, p.y, 10 * k, '#FFC23D');
      });
      // Markers and edge chips always add up to the list (PR #20, concept N).
      const chips = Object.entries(hiddenBy);
      const shown = RESULTS.length - hidden;
      if (shown + chips.reduce((a, [, n]) => a + n, 0) !== RESULTS.length) throw new Error('markers and chips do not add up');
      const ck = E.out(prog(t, 18.9, 19.2));
      gnc.globalAlpha = ck;
      const left = chips.filter(([rg]) => window.GLOBE.side[rg] === 'left');
      const right = chips.filter(([rg]) => window.GLOBE.side[rg] !== 'left');
      const chip = (txt, x, y, align) => {
        gnc.font = '600 30px Onest';
        const w = gnc.measureText(txt).width + 44;
        const x0 = align === 'left' ? x : x - w;
        gnc.fillStyle = '#16263F'; gnc.strokeStyle = '#2A3D61'; gnc.lineWidth = 2;
        gnc.beginPath(); gnc.roundRect(x0, y - 30, w, 60, 30); gnc.fill(); gnc.stroke();
        label(gnc, txt, x0 + 22, y + 1, '#FFFFFF', '600 30px Onest');
      };
      left.forEach(([rg, n], i) => chip(`← ${rg} · ${n}`, 80, 1300 + i * 76, 'left'));
      right.forEach(([rg, n], i) => chip(`${rg} · ${n} →`, 940, 1300 + i * 76, 'right'));
      gnc.globalAlpha = 1;
      M.heroCount = { shown, hidden };
    }
    const w = sceneWindow('hero', t, 0.3, 0.25);
    if (w.on) {
      const k = E.out(prog(t, 18.1, 19.1));
      $('#big').textContent = String(Math.round(414 * k));
      style($('#big'), { tf: `translateY(${((1 - E.expo(prog(t, 17.9, 18.4))) * 120 - w.vout * 80).toFixed(1)}px)`, blur: (1 - E.expo(prog(t, 17.9, 18.3))) * 16 + w.vout * 14 });
      style($('#bigsub'), { o: prog(t, 18.6, 18.8), tf: `translateY(${((1 - E.out(prog(t, 18.6, 18.9))) * 30 - w.vout * 60).toFixed(1)}px)` });
    }
    headlineAt('hero2', t, { delay: 0.15 });
    // «Угадывать не будем.» sits under the second line.
    if (t >= 19.4 && t <= 21.0) {
      const q = E.expo(prog(t, 19.95, 20.35)), out = E.inOut(prog(t, 20.6, 20.9));
      style($('#nogsub'), { o: q * (1 - out), tf: `translateY(${((1 - q) * 30 - out * 40).toFixed(1)}px)`, blur: (1 - q) * 8 + out * 10 });
    }
  }

  // 11 — «Поделись своим маршрутом.»
  headlineAt('h5', t, { delay: 0.25 });

  // 12 — three story cards fan out in depth.
  {
    const w = sceneWindow('stories', t, 0.05, 0.3);
    if (w.on) {
      const cards = [['#stA', -345, 60, -160, 20, -5, 0.74], ['#stB', 0, 0, 60, 0, 0, 0.94], ['#stC', 345, 60, -160, -20, 5, 0.74]];
      const drift = lerp(7, -7, E.inOut(prog(t, 22.6, 25.2)));
      cards.forEach(([sel, x, y, z, ry, rz, sc], i) => {
        const q = E.expo(prog(t, 22.2 + i * 0.11, 23.0 + i * 0.11));
        const out = E.in(prog(t, 25.25 + (2 - i) * 0.05, 25.62));
        const bob = Math.sin(t * 1.7 + i * 2.1) * 10;
        const tx = x * q, ty = lerp(1500, y, q) + bob - out * 300, tz = lerp(-400, z, q) - out * 600;
        const rx = lerp(55, 0, q) + out * 20;
        style($(sel), {
          o: prog(t, 22.2 + i * 0.11, 22.35 + i * 0.11) * (1 - out),
          tf: `translate3d(${tx.toFixed(1)}px, ${ty.toFixed(1)}px, ${tz.toFixed(1)}px) rotateX(${rx.toFixed(2)}deg) rotateY(${(ry * q + drift).toFixed(2)}deg) rotateZ(${(rz * q).toFixed(2)}deg) scale(${sc})`,
          blur: out * 14,
        });
      });
      $('#stB').style.zIndex = '2';
    }
  }

  // 13 — the end card: the sun rises with rays, the name follows, then the promise we can keep.
  {
    const w = sceneWindow('end', t, 0.01, 0.01);
    if (t >= 25.6) {
      const rise = E.expo(prog(t, 25.7, 27.2));
      const g = { cx: 540, cy: lerp(2900, 2360, rise), R: 1150, center: { lat: 30, lon: 60 + t * 3 } };
      drawGlobe(glc, { ...g, dot: '#9AA4B2', alpha: 0.7, size: 3.6, fill: ['#FFFFFF', '#EEF1F5'] });
      const hp = onGlobe(g, HOME);
      if (hp.z > 0) marker(glc, hp.x, hp.y, 13, '#0F1E36');
    }
    if (w.on) {
      const s = E.back(prog(t, 25.7, 26.2));
      const slide = E.inOut(prog(t, 26.3, 26.8));
      const markSize = lerp(200, 132, slide);
      const gap = 30;
      const total = markSize + gap + M.word.w;
      const rowY = 880;
      const mx = lerp(540, 540 - total / 2 + markSize / 2, slide);
      const mark = $('#sc-end .mark');
      style(mark, { tf: `translate(${(mx - 100).toFixed(1)}px, ${(rowY - 100).toFixed(1)}px) scale(${(Math.max(0, s) * markSize / 200).toFixed(3)})` });
      const word = $('#word');
      const wx = 540 - total / 2 + markSize + gap;
      const reveal = E.out(prog(t, 26.78, 27.2));
      word.style.clipPath = `inset(-20px ${((1 - reveal) * 100).toFixed(1)}% -20px 0)`;
      style(word, { o: reveal > 0 ? 1 : 0, tf: `translate(${wx.toFixed(1)}px, ${(rowY - M.word.h / 2).toFixed(1)}px)` });
      // Rays: twelve short gold strokes, out and gone, around where the sun first rises.
      const rc = $('#rays').getContext('2d');
      rc.clearRect(0, 0, 1080, 1920);
      const rq = prog(t, 25.95, 26.55);
      if (rq > 0 && rq < 1) {
        rc.strokeStyle = '#E8A317'; rc.lineWidth = 8; rc.lineCap = 'round'; rc.globalAlpha = 1 - E.in(rq);
        for (let i = 0; i < 12; i += 1) {
          const a = (i / 12) * Math.PI * 2 - Math.PI / 2;
          const r0 = 130 + E.out(rq) * 90, r1 = r0 + 46 * (1 - rq) + 10;
          rc.beginPath(); rc.moveTo(540 + Math.cos(a) * r0, rowY + Math.sin(a) * r0); rc.lineTo(540 + Math.cos(a) * r1, rowY + Math.sin(a) * r1); rc.stroke();
        }
        rc.globalAlpha = 1;
      }
      const tq = E.expo(prog(t, 27.05, 27.6));
      style($('#tag'), { o: tq, tf: `translateY(${((1 - tq) * 40).toFixed(1)}px)`, blur: (1 - tq) * 8 });
      style($('#disc'), { o: E.out(prog(t, 27.5, 27.9)) });
    }
  }

  // The demo label rides every UI scene, in the palette of the moment.
  {
    const ui = [[1.9, 3.3], [3.75, 5.15], [6.6, 8.85], [10.3, 12.45], [13.7, 17.45], [18.3, 20.6], [22.4, 25.3]];
    let o = 0;
    for (const [a, b] of ui) o = Math.max(o, prog(t, a, a + 0.15) * (1 - prog(t, b - 0.15, b)));
    const chip = $('#demo');
    chip.className = (t > 3.5 && t < 5.3) || (t > 17.9 && t < 21) ? 'night' : '';
    chip.style.opacity = String(o);
  }
  window.__t = t;
}

window.render = render;
window.DURATION = DURATION;
window.COPY = COPY;
// Each face's subsets load only when asked for, so ask for the letters we use
// (and the Kazakh ones, which the old faces lacked) before measuring anything.
const FACES = ['800 40px Montserrat', '400 40px Onest', '500 40px Onest', '600 40px Onest', '700 40px Onest'];
const SAMPLE = 'Найди Қазақстан ӘҒҢӨҰҮҺ €30 050 $1 848 — «»→✓·';
window.__ready = Promise.all(FACES.map((f) => document.fonts.load(f, SAMPLE))).then(() => document.fonts.ready).then(() => {
  const missing = FACES.filter((f) => !document.fonts.check(f, SAMPLE));
  measure();
  render(0);
  return { missing };
});
