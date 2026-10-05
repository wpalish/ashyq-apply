"""Landing scroll animation concept (Unimatch, palette E).

One sticky stage, scrubbed by scroll (the scroll-video skill's model: page height gives the distance,
a smoothed playhead follows it, forward and back). Drawn live rather than from a video, because every
frame is our own globe and our own numbers - no footage to invent.

  0.00-0.18  night: the question, the globe turning, Astana lit
  0.18-0.44  routes leave Astana one by one in each country's colour; "20 programmes · 15 countries"
  0.44-0.62  the globe rises and dims; three passes fly in and stack
  0.62-0.82  the top pass opens: price - grant = left to pay, if awarded
  0.82-1.00  the three separate answers, the source line, the call to action

Honesty: the numbers are the bundled demo corpus and say so on the pass; no %, no "chance";
"if awarded" stays next to the price. Reduced motion shows the last frame, still.
"""
import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from gen3 import FACES  # noqa: E402

LAND = json.load(open(os.path.join(HERE, 'land.json')))
COL = dict(NL='#3E5C76', BE='#5E4B6E', JP='#7A3B3B', DE='#3F6F6A', CA='#6B5A2E', GB='#44497F', KR='#55623A', AT='#6E4A55')
TINT = dict(NL='#9DBAD3', BE='#BCA9D0', JP='#D9A1A1', DE='#93C7BE', CA='#D2BE8C', GB='#A9ADE0', KR='#B9C79A', AT='#CFA3B0')
CITIES = [  # name, lon, lat, colour key
    ('Groningen', 6.6, 53.2, 'NL'), ('Leuven', 4.7, 50.9, 'BE'), ('Vienna', 16.4, 48.2, 'AT'),
    ('Tokyo', 139.7, 35.7, 'JP'), ('Singapore', 103.8, 1.35, 'KR'), ('Toronto', -79.4, 43.7, 'CA'),
]

HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Unimatch — landing motion concept</title>
<style>__FACES__
*{box-sizing:border-box} html,body{margin:0;background:#101014;color:#fff;font-family:Inter,system-ui,sans-serif;-webkit-font-smoothing:antialiased;font-variant-numeric:tabular-nums}
#track{height:640vh;position:relative}
#stage{position:sticky;top:0;height:100vh;overflow:hidden}
canvas{position:absolute;inset:0;width:100%;height:100%}
.layer{position:absolute;left:0;right:0;padding:0 22px;will-change:opacity,transform}
.eb{font:700 11.5px Inter;letter-spacing:.16em;text-transform:uppercase}
.h1{font:800 38px/1.04 Inter;letter-spacing:-.045em;margin:10px 0 0}
.sub{font:500 15px/1.5 Inter;color:#B9B9C4;margin-top:12px}
.brand{position:absolute;left:22px;top:22px;display:flex;align-items:center;gap:9px;z-index:5}
.brand i{width:24px;height:24px;border-radius:8px;background:conic-gradient(from 200deg,__C_NL__,__C_JP__,__C_BE__,__C_GB__,__C_DE__,__C_NL__)}
.brand b{font:800 18px Inter;letter-spacing:-.03em}
.pass{position:absolute;left:22px;right:22px;border-radius:26px;padding:18px 20px;color:#fff;overflow:hidden;will-change:transform,opacity;box-shadow:0 20px 40px rgba(0,0,0,.35)}
.pass:before{content:"";position:absolute;right:-40px;top:-40px;width:150px;height:150px;border-radius:50%;background:rgba(255,255,255,.12)}
.pass .c{font:700 11px Inter;letter-spacing:.07em;opacity:.8}
.pass .n{font:800 30px/1.05 Inter;letter-spacing:-.045em}
.pass .s{font:600 13px Inter;margin-top:6px;opacity:.95}
.pass .p{position:absolute;right:20px;top:18px;text-align:right}
.pass .p b{display:block;font:800 24px Inter;letter-spacing:-.03em}
.pass .p span{font:600 10.5px Inter;opacity:.8}
.demo{display:inline-block;font:700 10px Inter;letter-spacing:.04em;padding:3px 8px;border-radius:999px;background:rgba(255,255,255,.16);margin-top:10px}
.sheet{position:absolute;left:14px;right:14px;border-radius:22px;background:#fff;color:#111114;padding:6px 16px 10px;will-change:transform,opacity}
.row{display:flex;justify-content:space-between;align-items:baseline;padding:10px 0;border-top:1px solid #E3E1DC;will-change:opacity,transform;overflow:hidden;max-height:80px}
#answers{overflow:hidden;max-height:0}
.h1.sm{font-size:30px}
.row:first-child{border-top:0}
.row small{display:block;font:400 12px Inter;color:#5E5E6A}
.row b{font:600 15px Inter}
.row.total b{font:800 26px Inter;letter-spacing:-.03em}
.j{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid #E3E1DC;font:400 13.5px Inter}
.j em{font-style:normal;width:92px;flex:none;font:600 12px Inter;color:#5E5E6A}
.j i{font:700 12px Inter;font-style:normal;padding:4px 9px;border-radius:999px;white-space:nowrap}
.cta{display:inline-flex;align-items:center;gap:8px;height:52px;padding:0 24px;border-radius:999px;background:#fff;color:#111114;font:700 16px Inter}
.fine{font:500 11.5px/1.5 Inter;color:#9A9AA8;margin-top:10px}
.hint{position:absolute;left:0;right:0;bottom:26px;text-align:center;font:600 12px Inter;color:#8E8E9C;letter-spacing:.08em}
@media (min-width:900px){ .layer{padding:0 max(22px,calc(50vw - 520px))} .h1{font-size:64px} .pass,.sheet{left:auto;right:max(22px,calc(50vw - 520px));width:440px} .h1.sm{font-size:52px} }
</style></head><body>
<div id="track"><div id="stage">
<canvas id="globe" aria-hidden="true"></canvas>
<div class="brand"><i></i><b>unimatch</b></div>

<div class="layer" id="s1" style="top:96px"><div class="eb" style="color:__T_NL__">Study abroad, read for you</div>
<h1 class="h1">Where can you study — and what will it cost?</h1>
<div class="sub">We read the official pages, and every fact keeps its source and the date it was read.</div></div>

<div class="layer" id="s2" style="top:96px;opacity:0"><div class="eb" style="color:__T_BE__">From your city</div>
<div class="h1">From Astana to 15 countries</div>
<div class="sub" id="s2sub">20 programmes that match what you study and where you would go. Six of the routes are drawn here.</div></div>

<div class="layer" id="s3" style="top:96px;opacity:0"><div class="eb" style="color:__T_JP__">Each programme, a pass</div>
<div class="h1">One card per programme, in its country's colour</div></div>

<div class="layer" id="s4" style="top:96px;opacity:0"><div class="eb" style="color:__T_DE__">The price that matters</div>
<div class="h1">What is left to pay — and the word <i style="font-style:italic">if</i> stays</div></div>

<div class="layer" id="s5" style="top:92px;opacity:0"><div class="eb" style="color:__T_CA__">Requirements · profile · money</div>
<div class="h1 sm">Three answers, never one score</div></div>

<div class="pass" id="pJP" style="background:__C_JP__;top:0;opacity:0"><div class="c">JAPAN</div><div class="n">Tokyo</div><div class="s">University of Tokyo · PEAK</div><div class="p"><b>1,986</b><span>USD a year, if awarded</span></div></div>
<div class="pass" id="pBE" style="background:__C_BE__;top:0;opacity:0"><div class="c">BELGIUM</div><div class="n">Leuven</div><div class="s">KU Leuven · BSc Informatics</div><div class="p"><b>7,554</b><span>USD a year, if awarded</span></div></div>
<div class="pass" id="pNL" style="background:__C_NL__;top:0;opacity:0"><div class="c">NETHERLANDS · FALL 2027</div><div class="n">Groningen</div><div class="s">University of Groningen · BSc Computing Science</div>
<div class="p"><b id="big">32,663</b><span id="bigsub">USD a year, price</span></div><div class="demo">Example · demo data</div></div>

<div class="sheet" id="sheet" style="top:0;opacity:0">
<div class="row" id="r1"><span><b>Price a year</b><small>tuition, housing, living, fees</small></span><b>32,663</b></div>
<div class="row" id="r2"><span><b>Groningen Talent Grant</b><small>competitive · if awarded</small></span><b style="color:#106B3C">− 30,815</b></div>
<div class="row total" id="r3"><span><b style="font:700 15px Inter">Left to pay a year</b><small>if the grant is awarded</small></span><b>1,848</b></div>
<div id="answers" style="opacity:0">
<div class="j"><em>Requirements</em><i style="background:#FFF1DB;color:#8A5200">Pending</i>waiting on minimum GPA</div>
<div class="j"><em>Your profile</em><i style="background:#E5EDFF;color:#2440B8">Stronger</i>above the minimums</div>
<div class="j"><em>Money</em><i style="background:#DDF6E8;color:#106B3C">Full ride</i>Talent Grant, competitive</div>
<div style="font:400 11px Inter;color:#5E5E6A;padding-top:6px">rug.nl · demo fixture · read Oct 05</div></div></div>

<div class="layer" id="s6" style="bottom:44px;opacity:0"><span class="cta">Start with your profile →</span>
<div class="fine">Free to start. None of this predicts an admission decision — that is the university's.</div></div>
<div class="hint" id="hint">SCROLL</div>
</div></div>
<script>
const LAND = __LAND__;
const CITIES = __CITIES__;
const TINT = __TINT__;
const HOME = [71.4, 51.2];
const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
const cv = document.getElementById('globe'), ctx = cv.getContext('2d');
let W = 0, H = 0, DPR = 1;
function size() {
  DPR = Math.min(2, devicePixelRatio || 1); W = innerWidth; H = innerHeight;
  cv.width = W * DPR; cv.height = H * DPR; ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
}
addEventListener('resize', size); size();
const clamp = (x) => Math.max(0, Math.min(1, x));
const seg = (p, a, b) => clamp((p - a) / (b - a));
const ease = (t) => t < .5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
const lerp = (a, b, t) => a + (b - a) * t;
const rad = Math.PI / 180;
function vec(lon, lat) { return [Math.cos(lat * rad) * Math.cos(lon * rad), Math.cos(lat * rad) * Math.sin(lon * rad), Math.sin(lat * rad)]; }
function project(v, lon0, lat0, R, cx, cy, alt = 1) {
  // rotate so (lon0, lat0) faces the viewer; orthographic
  const l = Math.atan2(v[1], v[0]) - lon0 * rad, la = Math.asin(Math.max(-1, Math.min(1, v[2] / Math.hypot(...v))));
  const p0 = lat0 * rad;
  const cosc = Math.sin(p0) * Math.sin(la) + Math.cos(p0) * Math.cos(la) * Math.cos(l);
  const x = cx + alt * R * Math.cos(la) * Math.sin(l);
  const y = cy - alt * R * (Math.cos(p0) * Math.sin(la) - Math.sin(p0) * Math.cos(la) * Math.cos(l));
  return [x, y, cosc];
}
function slerp(a, b, t) {
  const d = Math.max(-1, Math.min(1, a[0] * b[0] + a[1] * b[1] + a[2] * b[2])), om = Math.acos(d), s = Math.sin(om);
  const k1 = Math.sin((1 - t) * om) / s, k2 = Math.sin(t * om) / s;
  return [a[0] * k1 + b[0] * k2, a[1] * k1 + b[1] * k2, a[2] * k1 + b[2] * k2];
}
const LANDV = LAND.map(([lo, la]) => vec(lo, la));
const HOMEV = vec(...HOME);
function draw(p) {
  ctx.clearRect(0, 0, W, H);
  const wide = W >= 900;
  const rise = ease(seg(p, .44, .6));
  const R0 = wide ? Math.min(W, H) * .52 : Math.min(W, H) * .62;
  const R = lerp(R0, R0 * .78, rise);
  const cx = wide ? lerp(W * .36, W * .30, rise) : W / 2;
  const cy = lerp(H * (wide ? .78 : .86), H * (wide ? .55 : .42), rise);
  const lon0 = lerp(20, 58, ease(seg(p, 0, .44)));
  const lat0 = 34;
  const dim = 1 - .55 * rise;
  // disc
  const g = ctx.createRadialGradient(cx, cy - R * .4, R * .1, cx, cy, R);
  g.addColorStop(0, '#20202A'); g.addColorStop(1, '#101014');
  ctx.globalAlpha = 1; ctx.fillStyle = g; ctx.beginPath(); ctx.arc(cx, cy, R, 0, Math.PI * 2); ctx.fill();
  ctx.strokeStyle = 'rgba(255,255,255,.08)'; ctx.lineWidth = 1; ctx.stroke();
  // land dots, three depth bands
  for (const v of LANDV) {
    const [x, y, c] = project(v, lon0, lat0, R, cx, cy);
    if (c <= 0.02 || y < -4 || y > H + 4) continue;
    ctx.fillStyle = c > .55 ? '#7A7A90' : c > .25 ? '#55556A' : '#3A3A46';
    ctx.globalAlpha = dim; ctx.fillRect(x - 1.2, y - 1.2, 2.4, 2.4);
  }
  // routes, one by one
  CITIES.forEach(([name, lon, lat, key], i) => {
    const t = ease(seg(p, .2 + i * .035, .3 + i * .035));
    if (t <= 0) return;
    const to = vec(lon, lat), n = 64, upto = Math.max(1, Math.round(n * t));
    ctx.beginPath(); let started = false, last = null;
    for (let k = 0; k <= upto; k++) {
      const s = k / n, v = slerp(HOMEV, to, s), alt = 1 + .22 * Math.sin(Math.PI * s) * Math.min(1, Math.acos(Math.max(-1, Math.min(1, HOMEV[0]*to[0]+HOMEV[1]*to[1]+HOMEV[2]*to[2]))) / 1.2);
      const [x, y, c] = project(v, lon0, lat0, R, cx, cy, alt);
      if (c < -0.15) { started = false; continue; }
      if (!started) { ctx.moveTo(x, y); started = true; } else ctx.lineTo(x, y);
      last = [x, y, c];
    }
    ctx.globalAlpha = dim; ctx.strokeStyle = TINT[key]; ctx.lineWidth = 2.4; ctx.lineCap = 'round'; ctx.stroke();
    if (t >= 1 && last && last[2] > 0) { ctx.fillStyle = TINT[key]; ctx.beginPath(); ctx.arc(last[0], last[1], 5, 0, 7); ctx.fill(); }
  });
  // home
  const [hx, hy, hc] = project(HOMEV, lon0, lat0, R, cx, cy);
  if (hc > 0) {
    const pulse = 10 + 6 * Math.sin(performance.now() / 380);
    ctx.globalAlpha = dim * .35; ctx.strokeStyle = '#fff'; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(hx, hy, pulse, 0, 7); ctx.stroke();
    ctx.globalAlpha = dim; ctx.fillStyle = '#fff'; ctx.beginPath(); ctx.arc(hx, hy, 6.5, 0, 7); ctx.fill();
    ctx.font = '700 10.5px Inter'; ctx.textAlign = 'center'; ctx.fillText('ASTANA', hx, hy + 24);
  }
  ctx.globalAlpha = 1;
}
const $ = (id) => document.getElementById(id);
const fade = (el, a) => { el.style.opacity = a; el.style.transform = `translateY(${(1 - a) * 18}px)`; };
function fmt(n) { return Math.round(n).toLocaleString('en-US'); }
function layout(p) {
  const wide = W >= 900;
  fade($('s1'), 1 - seg(p, .11, .17));
  fade($('s2'), Math.min(seg(p, .16, .22), 1 - seg(p, .41, .46)));
  fade($('s3'), Math.min(seg(p, .46, .5), 1 - seg(p, .6, .64)));
  fade($('s4'), Math.min(seg(p, .64, .68), 1 - seg(p, .8, .84)));
  fade($('s5'), seg(p, .84, .88));
  $('hint').style.opacity = 1 - seg(p, .02, .08);
  // passes fly in and stack
  const fin = ease(seg(p, .84, .9));
  const base = lerp(wide ? H * .30 : H * .42, wide ? H * .30 : H * .21 + 22, fin);
  [['pJP', 0, 26, 5], ['pBE', 1, 13, -4], ['pNL', 2, 0, 0]].forEach(([id, i, off, rot]) => {
    const t = ease(seg(p, .48 + i * .03, .58 + i * .03));
    const el = $(id), open = ease(seg(p, .62, .7));
    const y = lerp(H + 40, base - off * (1 - open * (id === 'pNL' ? 0 : -1)), t);
    const r = lerp(rot * 3, id === 'pNL' ? 0 : rot, t);
    el.style.opacity = t; el.style.top = '0'; el.style.transform = `translateY(${y}px) rotate(${r}deg)`;
    if (id !== 'pNL') el.style.opacity = t * (1 - open);
  });
  // the top pass: price counts down as the grant comes off
  const g = ease(seg(p, .77, .8));
  // no counting down: every figure shown is one the page states (price, then what is left)
  $('big').textContent = g < .5 ? '32,663' : '1,848';
  $('bigsub').textContent = g < .5 ? 'USD a year, price' : 'USD a year left, if awarded';
  $('big').parentElement.style.opacity = g > 0 && g < 1 ? Math.abs(2 * g - 1) : 1;
  const sh = $('sheet'), sTop = base + (wide ? 150 : 158);
  const so = ease(seg(p, .64, .7));
  sh.style.opacity = seg(p, .64, .655); sh.style.transform = `translateY(${lerp(sTop + 40, sTop, so)}px)`;
  // the sheet grows a line at a time instead of opening empty
  [['r1', .645], ['r2', .71], ['r3', .77]].forEach(([id, a]) => { const t = seg(p, a, a + .03); fade($(id), t); const el = $(id); el.style.maxHeight = `${80 * t}px`; el.style.paddingTop = el.style.paddingBottom = `${10 * t}px`; });
  // on a phone the arithmetic gives way to the three answers; the total stays
  if (!wide) ['r1', 'r2'].forEach((id) => { const el = $(id); el.style.maxHeight = `${80 * (1 - fin)}px`; el.style.paddingTop = el.style.paddingBottom = `${10 * (1 - fin)}px`; if (fin > 0) el.style.opacity = Math.min(+el.style.opacity, 1 - fin); });
  $('r3').style.borderTop = !wide && fin > .5 ? '0' : '';
  const ans = seg(p, .86, .9); $('answers').style.maxHeight = `${200 * ans}px`; fade($('answers'), ans);
  fade($('s6'), seg(p, .92, .96));
}
let target = 0, cur = 0, last = performance.now();
function progress() { const r = document.documentElement.scrollHeight - innerHeight; return r > 0 ? clamp(scrollY / r) : 0; }
addEventListener('scroll', () => { target = progress(); }, { passive: true });
function frame(now) {
  const dt = Math.min((now - last) / 1000, .1); last = now;
  cur += (target - cur) * (1 - Math.exp(-dt * 9));
  draw(cur); layout(cur);
  requestAnimationFrame(frame);
}
if (reduce) { document.getElementById('track').style.height = '100vh'; cur = target = 1; }
document.fonts.ready.then(() => { target = progress(); requestAnimationFrame(frame); });
window.__setP = (v) => { target = cur = v; };
</script></body></html>'''

out = HTML.replace('__FACES__', FACES).replace('__LAND__', json.dumps(LAND)).replace('__CITIES__', json.dumps(CITIES)).replace('__TINT__', json.dumps(TINT))
for k, v in COL.items():
    out = out.replace(f'__C_{k}__', v)
for k, v in TINT.items():
    out = out.replace(f'__T_{k}__', v)
os.makedirs(os.path.join(HERE, 'landing'), exist_ok=True)
open(os.path.join(HERE, 'landing', 'index.html'), 'w').write(out)
print('ok', len(out))
