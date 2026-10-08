"""Writes the nine frame sub-compositions of the Unimatch short (usage: gen_frames.py <project dir>).

Each frame is one bare <template> fragment (HyperFrames frame-worker contract): styles and the
GSAP load inside the template, the root styled by #root, a full-bleed ground on its own clip, one
paused timeline registered at window.__timelines[frame_id], ids and classes prefixed per frame.
Canvas 1080 x 1920; everything that matters sits above y = 1600.
"""
import json
import sys
from pathlib import Path

P = Path(sys.argv[1])
OUT = P / 'compositions' / 'frames'
OUT.mkdir(parents=True, exist_ok=True)
ROUTES = json.loads((P / 'capture/assets/images/routes.json').read_text())
# The owner's wordmark (traced from the supplied artwork), inlined so it can take currentColor.
LOGO = (P / 'capture/assets/images/unimatch-logo.svg').read_text().strip()
LOGO_RATIO = 736 / 3700  # height / width of its viewBox
DOT = (0.2904, 0.1601)  # the dot of the i (its centre, measured on the artwork), as a fraction of the logo box

NIGHT, PAPER, INK, CREAM, MUTED = '#101014', '#F3F2EF', '#111114', '#F3F2EF', '#A9A9B6'
ACCENT = '#D2BE8C'
PASS = {1: '#3E5C76', 2: '#5E4B6E', 3: '#7A3B3B', 4: '#3F6F6A', 5: '#6B5A2E', 7: '#55623A', 8: '#6E4A55'}
TINT = {1: '#9DBAD3', 2: '#BCA9D0', 3: '#D9A1A1', 4: '#93C7BE', 5: '#D2BE8C', 7: '#B9C79A', 8: '#CFA3B0'}

FONTS = ''.join(
    f'@font-face{{font-family:"Inter";font-weight:{w};font-style:normal;font-display:block;'
    f'src:url("assets/fonts/Inter-{w}.woff2") format("woff2");}}'
    for w in (400, 500, 600, 700, 800)
)


def frame(fid, pre, dur, ground, css, body, js):
    """One frame file. `pre` is the id/class prefix (CSS idents cannot start with a digit)."""
    html = f'''<template>
<script src="https://cdn.jsdelivr.net/npm/gsap@3.14.2/dist/gsap.min.js"></script>
<style>
{FONTS}
#root {{ position: absolute; inset: 0; overflow: hidden; font-family: "Inter"; -webkit-font-smoothing: antialiased; }}
#{pre}-bg {{ position: absolute; inset: 0; background: {ground}; }}
#{pre}-stage {{ position: absolute; inset: 0; }}
#{pre}-cam {{ position: absolute; inset: 0; transform-origin: 50% 40%; }}
.{pre}-abs {{ position: absolute; }}
.{pre}-kicker {{ position: absolute; left: 64px; margin: 0; font-size: 26px; font-weight: 700; letter-spacing: 0.16em; text-transform: uppercase; }}
.{pre}-display {{ position: absolute; left: 64px; right: 64px; margin: 0; display: grid; justify-items: start; font-weight: 800; letter-spacing: -0.045em; line-height: 0.95; }}
.{pre}-line {{ display: block; }}
{css}
</style>
<div id="root" data-composition-id="{fid}" data-width="1080" data-height="1920">
  <div id="{pre}-bg" class="clip" data-start="0" data-duration="{dur}" data-track-index="0"></div>
  <div id="{pre}-stage" class="clip" data-start="0" data-duration="{dur}" data-track-index="1">
    <div id="{pre}-cam">
{body}
    </div>
  </div>
</div>
<script>
(function () {{
  const tl = gsap.timeline({{ paused: true }});
  const D = {dur};
  tl.fromTo("#{pre}-cam", {{ scale: 1 }}, {{ scale: 1.04, duration: D, ease: "none" }}, 0);
{js}
  window.__timelines["{fid}"] = tl;
}})();
</script>
</template>
'''
    (OUT / f'{fid}.html').write_text(html)


def rise(sel, at, dur=0.5, y=40, ease='power3.out', blur=6):
    return (f'  tl.fromTo("{sel}", {{ y: {y}, opacity: 0, filter: "blur({blur}px)" }}, '
            f'{{ y: 0, opacity: 1, filter: "blur(0px)", duration: {dur}, ease: "{ease}" }}, {at});\n')


def pass_card(pre, pid, country, city, sub, price, price_sub, slot, extra='', behind=False):
    w = ' data-layout-allow-overlap' if behind else ''
    return f'''      <div class="{pre}-pass" id="{pre}-{pid}" style="background:{PASS[slot]}">
        <p class="{pre}-pc"{w}>{country}</p>
        <p class="{pre}-pn"{w}>{city}</p>
        <p class="{pre}-ps"{w}>{sub}</p>
        <div class="{pre}-pp"><b{w}>{price}</b><span{w}>{price_sub}</span></div>
        {extra}
      </div>'''


def pass_css(pre, top_h=300):
    return f'''
.{pre}-pass {{ position: absolute; left: 64px; width: 952px; min-height: {top_h}px; box-sizing: border-box; padding: 40px 44px; display: grid; align-content: start; justify-items: start; border-radius: 40px; color: #fff; overflow: hidden; box-shadow: 0 24px 48px rgba(17,17,20,0.18); }}
.{pre}-pass::before {{ content: ""; position: absolute; right: -90px; top: -90px; width: 320px; height: 320px; border-radius: 50%; background: rgba(255,255,255,0.12); }}
.{pre}-pass p {{ position: relative; margin: 0; }}
.{pre}-pc {{ font-size: 22px; font-weight: 700; letter-spacing: 0.08em; color: rgba(255,255,255,0.88); }}
.{pre}-pn {{ font-size: 78px; font-weight: 800; letter-spacing: -0.045em; line-height: 1.1; margin-top: 14px !important; }}
.{pre}-ps {{ font-size: 27px; font-weight: 600; margin-top: 16px !important; max-width: 560px; line-height: 1.3; }}
.{pre}-pp {{ position: absolute; right: 44px; top: 40px; display: grid; justify-items: end; text-align: right; }}
.{pre}-pp b {{ font-size: 58px; font-weight: 800; letter-spacing: -0.03em; font-variant-numeric: tabular-nums; }}
.{pre}-pp span {{ font-size: 21px; font-weight: 600; color: rgba(255,255,255,0.9); margin-top: 4px; }}
.{pre}-demo {{ position: relative; margin-top: 18px; padding: 7px 16px; border-radius: 999px; background: rgba(255,255,255,0.18); font-size: 20px; font-weight: 700; letter-spacing: 0.04em; }}
'''


# ── 01 · the question ───────────────────────────────────────────────────────────────────────────
def f01():
    pre, dur = 'f01', 3
    tabs = [
        ('Tuition fees 2027/28 (PDF)', 1, 60, 660, -4), ('Scholarships — who can apply', 2, 360, 590, 3),
        ('Admission requirements', 3, 110, 515, 6), ('Cost of living', 4, 450, 440, -5),
        ('Application deadlines', 5, 40, 365, 2), ('Recognition of foreign diplomas', 8, 260, 290, -3),
        ('Fees for non-EU students', 7, 90, 215, 5), ('Grant FAQ', 1, 500, 140, -2),
    ]
    body = [f'      <div id="{pre}-pile" data-layout-allow-overlap class="{pre}-abs" style="left:0;top:0;width:1080px;height:800px">']
    for i, (title, slot, x, y, _r) in enumerate(tabs):
        body.append(f'        <div class="{pre}-tab" id="{pre}-tab{i}" style="left:{x}px;top:{y}px;border-top-color:{TINT[slot]}">'
                    f'<i style="background:{TINT[slot]}"></i><span data-layout-allow-overlap>{title}</span><em data-layout-allow-overlap>×</em></div>')
    body.append('      </div>')
    line1, line2 = 'where can i', 'study'
    chars = lambda s, k: ''.join(f'<span class="{pre}-ch" id="{pre}-c{k}-{j}">{c if c != " " else "&nbsp;"}</span>' for j, c in enumerate(s))
    body.append(f'      <p class="{pre}-kicker" id="{pre}-kick" style="top:850px;color:{ACCENT}">Study abroad</p>')
    body.append(f'      <div class="{pre}-display" id="{pre}-q1" style="top:905px;font-size:130px;color:{CREAM}">'
                f'<span class="{pre}-line">{chars(line1, 1)}<span class="{pre}-caret" id="{pre}-caret1"></span></span>'
                f'<span class="{pre}-line">{chars(line2, 2)}<span class="{pre}-caret" id="{pre}-caret2"></span></span></div>')
    body.append(f'      <div class="{pre}-display" id="{pre}-q2" style="top:1180px;font-size:130px;color:{CREAM}">'
                f'<span class="{pre}-line" id="{pre}-q2a">— and what will</span>'
                f'<span class="{pre}-line" id="{pre}-q2b">it <span style="color:{ACCENT}">cost?</span></span></div>')
    css = f'''
.{pre}-tab {{ position: absolute; display: flex; align-items: center; gap: 18px; height: 98px; padding: 0 30px; box-sizing: border-box; min-width: 520px; border-radius: 24px 24px 6px 6px; background: #22222C; border-top: 4px solid; color: #D6D6DF; font-size: 33px; font-weight: 600; white-space: nowrap; box-shadow: 0 18px 36px rgba(0,0,0,0.45); }}
.{pre}-tab i {{ flex: none; width: 22px; height: 22px; border-radius: 50%; }}
.{pre}-tab span {{ flex: 1; }}
.{pre}-tab em {{ font-style: normal; color: #6E6E7C; font-size: 30px; }}
.{pre}-ch {{ display: none; }}
.{pre}-caret {{ display: inline-block; width: 9px; height: 0.82em; margin-left: 6px; background: {ACCENT}; vertical-align: -0.06em; opacity: 0; }}
'''
    js = ''
    # typing: line 1 over 0.05–0.62s, line 2 over 0.70–0.98s
    t = 0.05
    for j in range(len(line1)):
        js += f'  tl.set("#{pre}-c1-{j}", {{ display: "inline" }}, {t:.3f});\n'; t += 0.052
    t = 0.70
    for j in range(len(line2)):
        js += f'  tl.set("#{pre}-c2-{j}", {{ display: "inline" }}, {t:.3f});\n'; t += 0.056
    # caret: on line 1 until 0.66, then line 2; blinks on the half-beat after typing
    js += f'  tl.set("#{pre}-caret1", {{ opacity: 1 }}, 0.0);\n  tl.set("#{pre}-caret1", {{ opacity: 0 }}, 0.68);\n'
    js += f'  tl.set("#{pre}-caret2", {{ opacity: 1 }}, 0.68);\n'
    for k, tt in enumerate([1.25, 1.5, 1.75, 2.0]):
        js += f'  tl.set("#{pre}-caret2", {{ opacity: {0 if k % 2 == 0 else 1} }}, {tt});\n'
    js += rise(f'#{pre}-kick', 0.0, 0.4, 16)
    for i, (_t, _s, _x, _y, r) in enumerate(tabs):
        at = 1.0 + i * 0.125
        js += (f'  tl.fromTo("#{pre}-tab{i}", {{ y: -260, rotation: {r * 3}, opacity: 0 }}, '
               f'{{ y: 0, rotation: {r}, opacity: 1, duration: 0.42, ease: "power3.out" }}, {at:.3f});\n')
    js += f'  tl.fromTo("#{pre}-pile", {{ scale: 1, y: 0 }}, {{ scale: 0.94, y: 18, duration: 1.0, ease: "power2.in" }}, 2.0);\n'
    js += (f'  tl.fromTo("#{pre}-q2a", {{ scale: 1.18, opacity: 0, filter: "blur(10px)" }}, '
           f'{{ scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.45, ease: "expo.out" }}, 2.0);\n')
    js += (f'  tl.fromTo("#{pre}-q2b", {{ scale: 1.18, opacity: 0, filter: "blur(10px)" }}, '
           f'{{ scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.45, ease: "expo.out" }}, 2.25);\n')
    css += f'#{pre}-q2a, #{pre}-q2b {{ transform-origin: 0% 50%; }}\n#{pre}-pile {{ transform-origin: 50% 100%; }}\n'
    frame('01-hook', pre, dur, NIGHT, css, '\n'.join(body), js)


# ── 02 · one place ──────────────────────────────────────────────────────────────────────────────
def f02():
    pre, dur = 'f02', 2
    W = 860
    H = W * LOGO_RATIO
    LX, LY = (1080 - W) / 2, 806 - H / 2
    dx0, dy0 = LX + DOT[0] * W, LY + DOT[1] * H
    ghosts = [(-200, 180), (820, 120), (980, 560), (900, 1250), (-180, 1180), (200, 1500), (700, 1600), (-120, 700)]
    body = []
    for i, (x, y) in enumerate(ghosts):
        body.append(f'      <div class="{pre}-ghost" id="{pre}-g{i}" style="left:{x}px;top:{y}px"></div>')
    body.append(f'''      <div id="{pre}-logo" class="{pre}-abs" style="left:{LX:.0f}px;top:{LY:.0f}px;width:{W}px;height:{H:.0f}px;color:{INK}">{LOGO}</div>
      <div id="{pre}-dot" class="{pre}-abs" style="left:{dx0 - 18:.0f}px;top:{dy0 - 18:.0f}px;width:36px;height:36px;border-radius:50%;background:{INK}"></div>
      <p id="{pre}-tag" class="{pre}-abs" style="left:0;right:0;top:948px;margin:0;text-align:center;font-size:46px;font-weight:600;letter-spacing:-0.02em;color:rgba(17,17,20,0.58)">official pages, read for you.</p>
      <div id="{pre}-rule" class="{pre}-abs" style="left:330px;top:1036px;width:420px;height:2px;background:{INK};transform-origin:50% 50%"></div>''')
    css = f'''
.{pre}-ghost {{ position: absolute; width: 360px; height: 58px; border-radius: 18px 18px 6px 6px; background: rgba(17,17,20,0.10); }}
#{pre}-logo svg {{ display: block; width: 100%; height: 100%; }}
'''
    js = ''
    for i, (x, y) in enumerate(ghosts):
        tx, ty = dx0 - 180 - x, dy0 - 29 - y
        js += (f'  tl.fromTo("#{pre}-g{i}", {{ x: 0, y: 0, scale: 1, opacity: 1 }}, '
               f'{{ x: {tx:.0f}, y: {ty:.0f}, scale: 0.08, opacity: 0, duration: 0.5, ease: "power3.in" }}, {i * 0.02:.2f});\n')
    # the dot lands where every tab went, then the whole wordmark opens out of it
    js += f'  tl.fromTo("#{pre}-dot", {{ scale: 0 }}, {{ scale: 1, duration: 0.25, ease: "back.out(2.2)" }}, 0.45);\n'
    js += (f'  tl.fromTo("#{pre}-logo", {{ clipPath: "circle(0% at {DOT[0] * 100:.1f}% {DOT[1] * 100:.1f}%)", scale: 1.06 }}, '
           f'{{ clipPath: "circle(140% at {DOT[0] * 100:.1f}% {DOT[1] * 100:.1f}%)", scale: 1, duration: 0.8, ease: "power3.inOut" }}, 0.62);\n')
    js += f'  tl.to("#{pre}-dot", {{ opacity: 0, duration: 0.05 }}, 1.1);\n'
    js += rise(f'#{pre}-tag', 1.2, 0.5, 24)
    js += f'  tl.fromTo("#{pre}-rule", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.45, ease: "power3.out" }}, 1.4);\n'
    frame('02-logo', pre, dur, PAPER, css, '\n'.join(body), js)


# ── 03 · from Astana ────────────────────────────────────────────────────────────────────────────
def f03():
    pre, dur = 'f03', 4
    S, OX, OY = 0.6, -60, 640  # globe plate: 2000-unit viewBox shown 1200 px wide at (OX, OY)
    sx = lambda v: OX + v * S
    sy = lambda v: OY + v * S
    keep = ['Groningen', 'Leuven', 'Vienna', 'Tokyo', 'Singapore']
    routes = [r for r in ROUTES['routes'] if r['city'] in keep]
    routes.sort(key=lambda r: keep.index(r['city']))
    hx, hy = ROUTES['home']
    label_at = {'Groningen': (-70, -66), 'Leuven': (-190, 4), 'Vienna': (14, 18), 'Tokyo': (-150, -64), 'Singapore': (-220, 18)}
    paths = ''.join(
        f'<path id="{pre}-r{i}" d="{r["d"]}" pathLength="1" fill="none" stroke="{TINT[r["slot"]]}" stroke-width="7" '
        f'stroke-linecap="round" stroke-dasharray="1 1" stroke-dashoffset="1"/>'
        for i, r in enumerate(routes))
    ends = ''.join(
        f'<circle id="{pre}-e{i}" cx="{r["end"][0]}" cy="{r["end"][1]}" r="13" fill="{TINT[r["slot"]]}"/>'
        for i, r in enumerate(routes))
    labels = ''.join(
        f'<p class="{pre}-city" id="{pre}-l{i}" style="left:{sx(r["end"][0]) + label_at[r["city"]][0]:.0f}px;'
        f'top:{sy(r["end"][1]) + label_at[r["city"]][1]:.0f}px;color:{TINT[r["slot"]]}">{r["city"]}</p>'
        for i, r in enumerate(routes))
    body = f'''      <div id="{pre}-globe" class="{pre}-abs" style="left:{OX}px;top:{OY}px;width:1200px;height:1200px">
        <img id="{pre}-plate" src="assets/images/globe-night.svg" alt="" style="position:absolute;inset:0;width:1200px;height:1200px">
        <svg id="{pre}-svg" viewBox="0 0 2000 2000" width="1200" height="1200" style="position:absolute;inset:0;overflow:visible">{paths}{ends}
          <circle id="{pre}-pulse" cx="{hx}" cy="{hy}" r="22" fill="none" stroke="#fff" stroke-width="5"/>
          <circle cx="{hx}" cy="{hy}" r="17" fill="#fff"/>
        </svg>
      </div>
      {labels}
      <p class="{pre}-city" id="{pre}-home" style="left:{sx(hx) - 64:.0f}px;top:{sy(hy) + 26:.0f}px;color:#fff;letter-spacing:0.14em;font-size:22px">ASTANA</p>
      <p class="{pre}-kicker" id="{pre}-kick" style="top:196px;color:{ACCENT}">From your city</p>
      <div class="{pre}-display" style="top:246px;font-size:112px;color:{CREAM}">
        <span class="{pre}-line" id="{pre}-h1">from astana</span>
        <span class="{pre}-line" id="{pre}-h2">to <span style="color:{ACCENT}">15</span> countries.</span>
      </div>
      <p class="{pre}-abs" id="{pre}-tag" style="left:64px;top:500px;margin:0;font-size:30px;font-weight:600;color:{MUTED}">demo run · 20 programmes</p>'''
    css = f'''
.{pre}-city {{ position: absolute; margin: 0; font-size: 28px; font-weight: 700; white-space: nowrap; text-shadow: 0 0 8px {NIGHT}, 0 0 18px {NIGHT}; }}
#{pre}-cam {{ transform-origin: {sx(hx):.0f}px {sy(hy):.0f}px; }}
#{pre}-pulse {{ transform-origin: {hx}px {hy}px; transform-box: view-box; }}
'''
    js = (f'  tl.fromTo("#{pre}-globe", {{ y: 320, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.9, ease: "power3.out" }}, 0);\n')
    js += f'  tl.fromTo("#{pre}-pulse", {{ scale: 1, opacity: 0.6 }}, {{ scale: 3.2, opacity: 0, duration: 0.8, ease: "power2.out" }}, 0.6);\n'
    js += rise(f'#{pre}-home', 0.6, 0.4, 12)
    js += rise(f'#{pre}-kick', 0.05, 0.4, 16)
    js += rise(f'#{pre}-h1', 0.2, 0.5, 40)
    for i in range(len(routes)):
        at = 1.0 + i * 0.4
        js += f'  tl.fromTo("#{pre}-r{i}", {{ strokeDashoffset: 1 }}, {{ strokeDashoffset: 0, duration: 0.45, ease: "power2.inOut" }}, {at:.2f});\n'
        js += (f'  tl.fromTo("#{pre}-e{i}", {{ scale: 0, transformOrigin: "50% 50%" }}, '
               f'{{ scale: 1, duration: 0.3, ease: "back.out(2)" }}, {at + 0.42:.2f});\n')
        js += rise(f'#{pre}-l{i}', at + 0.42, 0.3, 10, blur=4)
    js += rise(f'#{pre}-h2', 3.0, 0.5, 40)
    js += rise(f'#{pre}-tag', 3.25, 0.4, 16)
    frame('03-routes', pre, dur, NIGHT, css, body, js)


# ── 04 · a pass each ────────────────────────────────────────────────────────────────────────────
def f04():
    pre, dur = 'f04', 2
    body = '\n'.join([
        pass_card(pre, 'p3', 'JAPAN', 'Tokyo', 'University of Tokyo · PEAK', '1,986', 'USD a year, if awarded', 3, behind=True),
        pass_card(pre, 'p2', 'BELGIUM', 'Leuven', 'KU Leuven · BSc Informatics', '7,554', 'USD a year, if awarded', 2, behind=True),
        pass_card(pre, 'p1', 'NETHERLANDS · FALL 2027', 'Groningen', 'University of Groningen · BSc Computing Science',
                  '32,663', 'USD a year, price', 1, f'<span class="{pre}-demo" id="{pre}-demo">Example · demo data</span>'),
        f'''      <div class="{pre}-display" style="top:230px;font-size:120px;color:{INK}">
        <span class="{pre}-line" id="{pre}-h1">one pass</span>
        <span class="{pre}-line" id="{pre}-h2">per programme.</span>
      </div>''',
    ])
    css = pass_css(pre, 330) + f'''
#{pre}-p3 {{ top: 590px; }} #{pre}-p2 {{ top: 770px; }} #{pre}-p1 {{ top: 950px; }}
'''
    js = ''
    for i, (pid, r) in enumerate([('p3', 5), ('p2', -3), ('p1', 0)]):
        js += (f'  tl.fromTo("#{pre}-{pid}", {{ y: 1150, rotation: {r * 4 + (12 if r == 0 else 0)}, opacity: 0 }}, '
               f'{{ y: 0, rotation: {r}, opacity: 1, duration: 0.6, ease: "power3.out" }}, {i * 0.32:.2f});\n')
    js += rise(f'#{pre}-h1', 1.0, 0.45, 36)
    js += rise(f'#{pre}-h2', 1.15, 0.45, 36)
    js += (f'  tl.fromTo("#{pre}-demo", {{ scale: 0.6, opacity: 0 }}, '
           f'{{ scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2)" }}, 1.45);\n')
    frame('04-passes', pre, dur, PAPER, css, body, js)


# ── 05 · what is left ───────────────────────────────────────────────────────────────────────────
def f05():
    pre, dur = 'f05', 4
    swap = (f'<div class="{pre}-pp" id="{pre}-pp-a"><b>32,663</b><span>USD a year, price</span></div>'
            f'<div class="{pre}-pp" id="{pre}-pp-b"><b>1,848</b><span>USD a year left, if awarded</span></div>'
            f'<span class="{pre}-demo">Example · demo data</span>')
    card = f'''      <div class="{pre}-pass" id="{pre}-p1" style="background:{PASS[1]}">
        <p class="{pre}-pc">NETHERLANDS · FALL 2027</p>
        <p class="{pre}-pn">Groningen</p>
        <p class="{pre}-ps">University of Groningen · BSc Computing Science</p>
        {swap}
      </div>'''
    body = f'''      <div class="{pre}-display" style="top:200px;font-size:124px;color:{INK}">
        <span class="{pre}-line" id="{pre}-h1">what's left</span>
        <span class="{pre}-line" id="{pre}-h2">to pay.</span>
      </div>
      <div id="{pre}-sheet">
        <div class="{pre}-row" id="{pre}-r1"><span><b>Price a year</b><small>tuition, housing, living, fees</small></span><b>32,663</b></div>
        <div class="{pre}-row" id="{pre}-r2"><span><b>Groningen Talent Grant</b><small>competitive · if awarded</small></span><b style="color:#177A4C">− 30,815</b></div>
        <div class="{pre}-row {pre}-total" id="{pre}-r3"><span><b>Left to pay a year</b><small>if the grant is awarded</small></span><b>1,848</b></div>
      </div>
{card}
      <div id="{pre}-stamp">if awarded</div>
      <p class="{pre}-abs" id="{pre}-src" style="left:64px;top:1480px;margin:0;font-size:26px;font-weight:600;color:rgba(17,17,20,0.55)">rug.nl · demo fixture · read Oct 05</p>'''
    css = pass_css(pre, 300) + f'''
#{pre}-p1 {{ top: 470px; }}
#{pre}-pp-b {{ opacity: 0; }}
#{pre}-sheet {{ position: absolute; left: 48px; width: 984px; top: 850px; box-sizing: border-box; padding: 26px 44px 18px; border-radius: 36px; background: #fff; color: {INK}; box-shadow: 0 18px 40px rgba(17,17,20,0.10); }}
.{pre}-row {{ display: flex; justify-content: space-between; align-items: baseline; gap: 24px; padding: 26px 0; border-top: 2px solid #E3E1DC; }}
.{pre}-row:first-child {{ border-top: 0; }}
.{pre}-row span {{ display: grid; gap: 6px; }}
.{pre}-row span b {{ font-size: 38px; font-weight: 700; letter-spacing: -0.02em; }}
.{pre}-row small {{ font-size: 26px; color: #5E5E6A; font-weight: 500; }}
.{pre}-row > b {{ font-size: 46px; font-weight: 700; font-variant-numeric: tabular-nums; }}
.{pre}-total > b {{ font-size: 96px; font-weight: 800; letter-spacing: -0.04em; }}
#{pre}-stamp {{ position: absolute; left: 64px; top: 1370px; padding: 14px 30px; border: 5px solid {PASS[5]}; border-radius: 16px; color: {PASS[5]}; font-size: 40px; font-weight: 800; letter-spacing: 0.06em; text-transform: uppercase; }}
'''
    js = rise(f'#{pre}-h1', 0.05, 0.45, 36) + rise(f'#{pre}-h2', 0.25, 0.45, 36)
    js += f'  tl.fromTo("#{pre}-p1", {{ y: 80, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.55, ease: "power3.out" }}, 0.4);\n'
    js += f'  tl.fromTo("#{pre}-sheet", {{ y: -260, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.6, ease: "power3.out" }}, 0.95);\n'
    for i, at in enumerate([1.05, 1.55, 2.5]):
        js += rise(f'#{pre}-r{i + 1}', at, 0.45, 26, blur=4)
    js += f'  tl.fromTo("#{pre}-pp-a", {{ y: 0, opacity: 1 }}, {{ y: -30, opacity: 0, duration: 0.25, ease: "power2.in" }}, 2.55);\n'
    js += f'  tl.fromTo("#{pre}-pp-b", {{ y: 30, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.35, ease: "power3.out" }}, 2.75);\n'
    js += (f'  tl.fromTo("#{pre}-stamp", {{ scale: 1.6, rotation: -14, opacity: 0 }}, '
           f'{{ scale: 1, rotation: -6, opacity: 1, duration: 0.35, ease: "expo.out" }}, 3.0);\n')
    js += rise(f'#{pre}-src', 3.2, 0.4, 12)
    frame('05-money', pre, dur, PAPER, css, body, js)


# ── 06 · answers, not odds ──────────────────────────────────────────────────────────────────────
def f06():
    pre, dur = 'f06', 4
    rows = [('requirements', 'Pending', '#FFF3DB', '#8A5A00', 'waiting on minimum GPA'),
            ('your profile', 'Stronger', '#E7F0FA', '#1D4F91', 'above the minimums'),
            ('money', 'Competitive', '#E7F0FA', '#1D4F91', 'Talent Grant, if awarded')]
    body = [f'      <p class="{pre}-kicker" id="{pre}-kick" style="top:250px;color:{ACCENT}">Requirements · profile · money</p>']
    for i, (label, chip, bg, fg, note) in enumerate(rows):
        top = 340 + i * 262
        body.append(f'''      <div class="{pre}-row" id="{pre}-row{i}" style="top:{top}px">
        <p class="{pre}-label">{label}</p>
        <div class="{pre}-meta"><span class="{pre}-chip" style="background:{bg};color:{fg}">{chip}</span><span class="{pre}-note">{note}</span></div>
      </div>''')
        if i:
            body.append(f'      <div class="{pre}-hair" id="{pre}-hair{i}" style="top:{top - 22}px"></div>')
    body.append(f'''      <div class="{pre}-display" style="top:1150px;font-size:148px;color:{CREAM}">
        <span class="{pre}-line" id="{pre}-c1">answers,</span>
        <span class="{pre}-line" id="{pre}-c2" style="color:{ACCENT}">not odds.</span>
      </div>
      <p class="{pre}-abs" id="{pre}-note" style="left:64px;top:1470px;margin:0;font-size:35px;font-weight:600;color:{MUTED}">three separate answers — never one score</p>''')
    css = f'''
.{pre}-row {{ position: absolute; left: 64px; right: 64px; transform-origin: 0% 50%; }}
.{pre}-label {{ margin: 0; font-size: 108px; font-weight: 800; letter-spacing: -0.045em; line-height: 1; color: {CREAM}; }}
.{pre}-meta {{ display: flex; align-items: center; gap: 24px; margin-top: 22px; }}
.{pre}-chip {{ padding: 12px 30px; border-radius: 999px; font-size: 38px; font-weight: 700; }}
.{pre}-note {{ font-size: 35px; font-weight: 500; color: {MUTED}; }}
.{pre}-hair {{ position: absolute; left: 64px; width: 952px; height: 2px; background: #2C2C36; transform-origin: 0% 50%; }}
'''
    js = rise(f'#{pre}-kick', 0.05, 0.4, 14)
    for i, at in enumerate([0.15, 1.15, 2.15]):
        js += (f'  tl.fromTo("#{pre}-row{i}", {{ scale: 1.22, opacity: 0, filter: "blur(10px)" }}, '
               f'{{ scale: 1, opacity: 1, filter: "blur(0px)", duration: 0.42, ease: "expo.out" }}, {at});\n')
    for i in (1, 2):
        js += f'  tl.fromTo("#{pre}-hair{i}", {{ scaleX: 0 }}, {{ scaleX: 1, duration: 0.5, ease: "power3.out" }}, {1.05 + (i - 1):.2f});\n'
    js += rise(f'#{pre}-c1', 3.0, 0.5, 40) + rise(f'#{pre}-c2', 3.2, 0.5, 40) + rise(f'#{pre}-note', 3.45, 0.45, 14)
    frame('06-answers', pre, dur, NIGHT, css, '\n'.join(body), js)


# ── 07 · one at a time ──────────────────────────────────────────────────────────────────────────
def f07():
    pre, dur = 'f07', 3
    body = '\n'.join([
        f'''      <div class="{pre}-display" style="top:200px;font-size:124px;color:{INK}">
        <span class="{pre}-line" id="{pre}-h1">decide</span>
        <span class="{pre}-line" id="{pre}-h2">one at a time.</span>
      </div>''',
        pass_card(pre, 'p3', 'JAPAN', 'Tokyo', 'University of Tokyo · PEAK', '1,986', 'USD a year, if awarded', 3, behind=True),
        pass_card(pre, 'p2', 'BELGIUM', 'Leuven', 'KU Leuven · BSc Informatics', '7,554', 'USD a year, if awarded', 2, behind=True),
        pass_card(pre, 'p1', 'NETHERLANDS', 'Groningen', 'University of Groningen · BSc Computing Science', '1,848', 'USD a year left, if awarded', 1, behind=True),
        f'''      <div id="{pre}-btns">
        <span class="{pre}-btn" id="{pre}-b0">Not for me</span>
        <span class="{pre}-btn" id="{pre}-b1">Maybe</span>
        <span class="{pre}-btn {pre}-keep" id="{pre}-b2">Keep</span>
      </div>
      <div id="{pre}-piles" data-layout-allow-overlap>
        <span class="{pre}-pile" id="{pre}-kept">Kept · <i id="{pre}-k0" data-layout-allow-overlap>0</i><i id="{pre}-k1" data-layout-allow-overlap>1</i></span>
        <span class="{pre}-pile" id="{pre}-maybe">Maybe · <i id="{pre}-m0" data-layout-allow-overlap>0</i><i id="{pre}-m1" data-layout-allow-overlap>1</i></span>
      </div>''',
    ])
    css = pass_css(pre, 300) + f'''
#{pre}-p3 {{ top: 600px; }} #{pre}-p2 {{ top: 645px; }} #{pre}-p1 {{ top: 690px; }}
#{pre}-btns {{ position: absolute; left: 64px; right: 64px; top: 1130px; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 24px; }}
.{pre}-btn {{ display: grid; place-items: center; height: 126px; border-radius: 999px; border: 3px solid {INK}; color: {INK}; font-size: 38px; font-weight: 700; }}
.{pre}-keep {{ background: {INK}; color: #fff; }}
#{pre}-piles {{ position: absolute; left: 64px; top: 1310px; display: flex; gap: 22px; }}
.{pre}-pile {{ position: relative; padding: 16px 32px; border-radius: 999px; background: #fff; color: {INK}; font-size: 34px; font-weight: 700; box-shadow: 0 8px 20px rgba(17,17,20,0.08); }}
.{pre}-pile i {{ font-style: normal; display: inline-block; min-width: 0.7em; }}
#{pre}-k1, #{pre}-m1 {{ position: absolute; right: 28px; opacity: 0; }}
'''
    js = rise(f'#{pre}-h1', 0.05, 0.45, 36) + rise(f'#{pre}-h2', 0.2, 0.45, 36)
    js += f'  tl.set("#{pre}-p2 > *, #{pre}-p3 > *", {{ opacity: 0 }}, 0);\n'
    js += f'  tl.to("#{pre}-p2 > *", {{ opacity: 1, duration: 0.3 }}, 1.35);\n'
    js += f'  tl.to("#{pre}-p3 > *", {{ opacity: 1, duration: 0.3 }}, 2.35);\n'
    # the front card lands first; the two behind fan out from under it (never seen as blank plates)
    js += (f'  tl.fromTo("#{pre}-p1", {{ y: 900, rotation: 6, opacity: 0 }}, '
           f'{{ y: 0, rotation: 0, opacity: 1, duration: 0.55, ease: "power3.out" }}, 0.1);\n')
    for pid, r, dy, at in (('p2', -4, 45, 0.6), ('p3', 6, 90, 0.7)):
        js += (f'  tl.fromTo("#{pre}-{pid}", {{ y: {dy}, rotation: 0, opacity: 0 }}, '
               f'{{ y: 0, rotation: {r}, opacity: 1, duration: 0.4, ease: "power3.out" }}, {at});\n')
    js += f'  tl.fromTo("#{pre}-btns", {{ y: 40, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.4, ease: "power3.out" }}, 0.55);\n'
    js += f'  tl.fromTo("#{pre}-piles", {{ y: 20, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.4, ease: "power3.out" }}, 0.7);\n'
    # Keep: press, Groningen to the Kept pile, the deck re-fans
    js += f'  tl.fromTo("#{pre}-b2", {{ scale: 1 }}, {{ scale: 0.9, duration: 0.1, ease: "power2.out" }}, 1.0);\n'
    js += f'  tl.to("#{pre}-b2", {{ scale: 1, duration: 0.18, ease: "power2.out" }}, 1.1);\n'
    js += (f'  tl.to("#{pre}-p1", {{ x: -300, y: 640, scale: 0.18, rotation: -8, opacity: 0, duration: 0.45, ease: "power3.in" }}, 1.08);\n')
    js += f'  tl.to("#{pre}-k0", {{ opacity: 0, duration: 0.1 }}, 1.5);\n  tl.to("#{pre}-k1", {{ opacity: 1, duration: 0.1 }}, 1.5);\n'
    js += f'  tl.fromTo("#{pre}-kept", {{ scale: 1 }}, {{ scale: 1.12, duration: 0.12, ease: "power2.out" }}, 1.5);\n  tl.to("#{pre}-kept", {{ scale: 1, duration: 0.2 }}, 1.62);\n'
    js += f'  tl.to("#{pre}-p2", {{ y: 40, rotation: 0, duration: 0.4, ease: "power3.out" }}, 1.3);\n'
    js += f'  tl.to("#{pre}-p3", {{ y: 20, rotation: -3, duration: 0.4, ease: "power3.out" }}, 1.35);\n'
    # Maybe: press, Leuven to the Maybe pile, Tokyo comes up
    js += f'  tl.fromTo("#{pre}-b1", {{ scale: 1 }}, {{ scale: 0.9, duration: 0.1, ease: "power2.out" }}, 2.0);\n'
    js += f'  tl.to("#{pre}-b1", {{ scale: 1, duration: 0.18, ease: "power2.out" }}, 2.1);\n'
    js += (f'  tl.to("#{pre}-p2", {{ x: -40, y: 680, scale: 0.18, rotation: 6, opacity: 0, duration: 0.45, ease: "power3.in" }}, 2.08);\n')
    js += f'  tl.to("#{pre}-m0", {{ opacity: 0, duration: 0.1 }}, 2.5);\n  tl.to("#{pre}-m1", {{ opacity: 1, duration: 0.1 }}, 2.5);\n'
    js += f'  tl.fromTo("#{pre}-maybe", {{ scale: 1 }}, {{ scale: 1.12, duration: 0.12, ease: "power2.out" }}, 2.5);\n  tl.to("#{pre}-maybe", {{ scale: 1, duration: 0.2 }}, 2.62);\n'
    js += f'  tl.to("#{pre}-p3", {{ y: 80, rotation: 0, duration: 0.4, ease: "power3.out" }}, 2.3);\n'
    frame('07-decide', pre, dur, PAPER, css, body, js)


# ── 08 · a dated plan ───────────────────────────────────────────────────────────────────────────
def f08():
    pre, dur = 'f08', 3
    tickets = [('1 FEB', '2027', 1, 'Groningen Talent Grant', 'grant · University of Groningen'),
               ('1 MAR', '2027', 2, 'KU Leuven', 'BSc Informatics'),
               ('1 MAY', '2027', 1, 'University of Groningen', 'BSc Computing Science')]
    body = [f'''      <div class="{pre}-display" style="top:200px;font-size:124px;color:{INK}">
        <span class="{pre}-line" id="{pre}-h1">your plan,</span>
        <span class="{pre}-line" id="{pre}-h2">dated.</span>
      </div>
      <div id="{pre}-week">
        <p class="{pre}-wk">THIS WEEK</p>
        <p class="{pre}-wt">Start first: reference letter</p>
        <p class="{pre}-ws">it depends on someone else</p>
      </div>''']
    for i, (day, year, slot, title, sub) in enumerate(tickets):
        body.append(f'''      <div class="{pre}-ticket" id="{pre}-t{i}" style="top:{780 + i * 205}px">
        <div class="{pre}-stub" style="background:{PASS[slot]}"><b>{day}</b><span>{year}</span></div>
        <div class="{pre}-tb"><b>{title}</b><span>{sub}</span></div>
      </div>''')
    body.append(f'      <span class="{pre}-abs" id="{pre}-demo" style="left:64px;top:1420px;padding:10px 22px;border-radius:999px;background:rgba(17,17,20,0.08);color:rgba(17,17,20,0.7);font-size:24px;font-weight:700;letter-spacing:0.04em">Deadlines from demo data</span>')
    css = f'''
#{pre}-week {{ position: absolute; left: 64px; width: 952px; top: 470px; box-sizing: border-box; padding: 34px 44px; border-radius: 36px; background: {INK}; color: #fff; }}
#{pre}-week p {{ margin: 0; }}
.{pre}-wk {{ font-size: 24px; font-weight: 700; letter-spacing: 0.16em; color: {ACCENT}; }}
.{pre}-wt {{ font-size: 50px; font-weight: 800; letter-spacing: -0.03em; margin-top: 12px !important; }}
.{pre}-ws {{ font-size: 30px; font-weight: 500; color: {MUTED}; margin-top: 8px !important; }}
.{pre}-ticket {{ position: absolute; left: 64px; width: 952px; height: 176px; display: flex; border-radius: 28px; background: #fff; overflow: hidden; box-shadow: 0 10px 26px rgba(17,17,20,0.08); }}
.{pre}-stub {{ flex: none; width: 210px; display: grid; place-content: center; text-align: center; color: #fff; border-right: 4px dashed rgba(255,255,255,0.55); }}
.{pre}-stub b {{ font-size: 50px; font-weight: 800; letter-spacing: -0.02em; }}
.{pre}-stub span {{ font-size: 24px; font-weight: 600; opacity: 0.85; }}
.{pre}-tb {{ display: grid; align-content: center; gap: 8px; padding: 0 36px; color: {INK}; }}
.{pre}-tb b {{ font-size: 42px; font-weight: 700; letter-spacing: -0.02em; }}
.{pre}-tb span {{ font-size: 30px; font-weight: 500; color: #5E5E6A; }}
'''
    js = rise(f'#{pre}-h1', 0.05, 0.45, 36) + rise(f'#{pre}-h2', 0.2, 0.45, 36)
    js += f'  tl.fromTo("#{pre}-week", {{ y: -60, opacity: 0 }}, {{ y: 0, opacity: 1, duration: 0.5, ease: "power3.out" }}, 0.35);\n'
    for i in range(3):
        js += (f'  tl.fromTo("#{pre}-t{i}", {{ x: 1100 }}, {{ x: 0, duration: 0.5, ease: "power3.out" }}, {0.85 + i * 0.5:.2f});\n')
    js += f'  tl.fromTo("#{pre}-demo", {{ scale: 0.7, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.35, ease: "back.out(2)" }}, 2.4);\n'
    frame('08-plan', pre, dur, PAPER, css, '\n'.join(body), js)


# ── 09 · start with your profile ────────────────────────────────────────────────────────────────
def f09():
    pre, dur = 'f09', 5
    promises = [('a source and a date on every fact', PASS[1]), ('three answers, never a score', PASS[2]),
                ('free to start', PASS[4])]
    body = [f'''      <div id="{pre}-logo" class="{pre}-abs" style="left:64px;top:262px;width:520px;height:{520 * LOGO_RATIO:.0f}px;color:{INK}">{LOGO}</div>
      <div class="{pre}-display" style="top:440px;font-size:124px;color:{INK}">
        <span class="{pre}-line" id="{pre}-h1">know what's</span>
        <span class="{pre}-line" id="{pre}-h2">left to pay</span>
      </div>
      <p class="{pre}-abs" id="{pre}-h3" style="left:64px;top:690px;margin:0;font-size:62px;font-weight:800;letter-spacing:-0.04em;color:rgba(17,17,20,0.55)">— before you apply.</p>''']
    for i, (text, col) in enumerate(promises):
        body.append(f'      <div class="{pre}-promise" id="{pre}-pr{i}" style="top:{860 + i * 104}px"><i style="background:{col}"></i>{text}</div>')
    body.append(f'''      <div id="{pre}-btn">start with your profile <span>→</span></div>
      <p class="{pre}-abs" id="{pre}-fine" style="left:64px;width:900px;top:1420px;margin:0;font-size:28px;line-height:1.45;font-weight:500;color:rgba(17,17,20,0.55)">Example figures from demo data. None of this predicts an admission decision — that is the university's.</p>''')
    css = f'''
#{pre}-logo svg {{ display: block; width: 100%; height: 100%; }}
.{pre}-promise {{ position: absolute; left: 64px; width: 952px; display: flex; align-items: center; gap: 22px; padding-top: 22px; border-top: 2px solid rgba(17,17,20,0.14); font-size: 42px; font-weight: 600; letter-spacing: -0.02em; color: {INK}; }}
.{pre}-promise i {{ flex: none; width: 22px; height: 22px; border-radius: 50%; }}
#{pre}-btn {{ position: absolute; left: 64px; top: 1220px; display: flex; align-items: center; gap: 18px; height: 140px; padding: 0 64px; border-radius: 999px; background: {INK}; color: #fff; font-size: 50px; font-weight: 700; letter-spacing: -0.02em; transform-origin: 0% 50%; }}
'''
    js = (f'  tl.fromTo("#{pre}-logo", {{ clipPath: "inset(0% 100% 0% 0%)", x: -24 }}, '
           f'{{ clipPath: "inset(0% 0% 0% 0%)", x: 0, duration: 0.55, ease: "power3.out" }}, 0.05);\n')
    js += rise(f'#{pre}-h1', 0.35, 0.5, 40) + rise(f'#{pre}-h2', 0.55, 0.5, 40) + rise(f'#{pre}-h3', 0.8, 0.45, 24)
    for i in range(3):
        js += rise(f'#{pre}-pr{i}', 1.0 + i * 0.5, 0.45, 20, blur=4)
    js += f'  tl.fromTo("#{pre}-btn", {{ scale: 0.9, opacity: 0 }}, {{ scale: 1, opacity: 1, duration: 0.45, ease: "back.out(1.6)" }}, 2.5);\n'
    js += f'  tl.to("#{pre}-btn", {{ scale: 0.96, duration: 0.1, ease: "power2.out" }}, 3.0);\n  tl.to("#{pre}-btn", {{ scale: 1, duration: 0.25, ease: "power2.out" }}, 3.1);\n'
    js += rise(f'#{pre}-fine', 3.5, 0.5, 12)
    js += f'  tl.to("#{pre}-cam", {{ opacity: 0, duration: 0.4, ease: "power1.in" }}, 4.6);\n'
    frame('09-end', pre, dur, PAPER, css, '\n'.join(body), js)


for f in (f01, f02, f03, f04, f05, f06, f07, f08, f09):
    f()
print('wrote', sorted(p.name for p in OUT.glob('*.html')))
