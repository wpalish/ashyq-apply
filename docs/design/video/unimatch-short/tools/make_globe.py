"""Night globe for the short: Unimatch's land dots (frontend/src/lib/globe-land.ts),
thinned to the landing's density, projected orthographically around Central Asia,
with great-circle routes from Astana. Writes an SVG plate and the route paths as JSON."""
import base64, json, math, re, sys
from pathlib import Path
SRC = Path(__file__).resolve().parents[5] / 'frontend/src/lib/globe-land.ts'
OUT = sys.argv[1]
b64 = re.search(r"'([A-Za-z0-9+/=]{100,})'", open(SRC).read()).group(1)
raw = base64.b64decode(b64)
vals = [int.from_bytes(raw[i:i+2], 'little', signed=True) for i in range(0, len(raw), 2)]
R_ = math.pi / 180
dots = [(vals[i] / 100 * R_, vals[i+1] / 100 * R_) for i in range(0, len(vals), 2)]
# thin on the sphere (the landing's spacing)
SP = 0.039; cells = {}; kept = []
for lat, lon in dots:
    x, y, z = math.cos(lat)*math.cos(lon), math.cos(lat)*math.sin(lon), math.sin(lat)
    c = (math.floor(x/SP), math.floor(y/SP), math.floor(z/SP)); near = False
    for dx in (-1,0,1):
        for dy in (-1,0,1):
            for dz in (-1,0,1):
                for (a,b,cc) in cells.get((c[0]+dx,c[1]+dy,c[2]+dz), []):
                    if (a-x)**2+(b-y)**2+(cc-z)**2 < SP*SP: near = True; break
                if near: break
            if near: break
        if near: break
    if near: continue
    cells.setdefault(c, []).append((x,y,z)); kept.append((lat, lon))
LAT0, LON0 = 34 * R_, 52 * R_
def proj(lat, lon, lift=0.0):
    r = 1 + lift; dl = lon - LON0
    x = r*math.cos(lat)*math.sin(dl)
    y = r*(math.cos(LAT0)*math.sin(lat) - math.sin(LAT0)*math.cos(lat)*math.cos(dl))
    z = r*(math.sin(LAT0)*math.sin(lat) + math.cos(LAT0)*math.cos(lat)*math.cos(dl))
    return x, y, z
S = 1000  # viewBox 2000 x 2000, centre 1000, radius 1000
shades = ['#3A3A46', '#55556A', '#7A7A90']
rects = {0: [], 1: [], 2: []}
for lat, lon in kept:
    x, y, z = proj(lat, lon)
    if z <= 0.02: continue
    b = 2 if z > 0.55 else 1 if z > 0.25 else 0
    rects[b].append(f'M{S + x*S - 4.5:.1f} {S - y*S - 4.5:.1f}h9v9h-9z')
svg = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2000 2000" width="2000" height="2000">',
       '<defs><radialGradient id="disc" cx="50%" cy="30%" r="70%"><stop offset="0" stop-color="#22222C"/><stop offset="1" stop-color="#101014"/></radialGradient></defs>',
       f'<circle cx="{S}" cy="{S}" r="{S-2}" fill="url(#disc)" stroke="rgba(255,255,255,.10)" stroke-width="3"/>']
for b in (0, 1, 2):
    svg.append(f'<path fill="{shades[b]}" d="{"".join(rects[b])}"/>')
svg.append('</svg>')
open(f'{OUT}/globe-night.svg', 'w').write(''.join(svg))
# routes from Astana (slot = pass colour)
HOME = (51.17, 71.45)
ROUTES = [('Groningen', 53.2, 6.6, 1), ('Leuven', 50.9, 4.7, 2), ('Vienna', 48.2, 16.4, 8),
          ('Tokyo', 35.7, 139.7, 3), ('Singapore', 1.35, 103.8, 7), ('Toronto', 43.7, -79.4, 5)]
def gc(a, b, n=64, arc=0.22):
    la1, lo1, la2, lo2 = a[0]*R_, a[1]*R_, b[0]*R_, b[1]*R_
    v1 = (math.cos(la1)*math.cos(lo1), math.cos(la1)*math.sin(lo1), math.sin(la1))
    v2 = (math.cos(la2)*math.cos(lo2), math.cos(la2)*math.sin(lo2), math.sin(la2))
    d = math.acos(max(-1, min(1, sum(p*q for p, q in zip(v1, v2)))))
    pts = []
    for i in range(n + 1):
        t = i / n
        s1, s2 = math.sin((1-t)*d)/math.sin(d), math.sin(t*d)/math.sin(d)
        v = [s1*p + s2*q for p, q in zip(v1, v2)]
        lat = math.atan2(v[2], math.hypot(v[0], v[1])); lon = math.atan2(v[1], v[0])
        lift = arc * math.sin(math.pi * t) * min(1, d / 1.2)
        pts.append(proj(lat, lon, lift))
    return pts
routes = []
for name, la, lo, slot in ROUTES:
    pts = gc(HOME, (la, lo)); segs = []; pen = False; end = None
    for x, y, z in pts:
        if z < -0.15: pen = False; continue
        X, Y = S + x*S, S - y*S
        segs.append(f'{"L" if pen else "M"}{X:.1f} {Y:.1f}'); pen = True; end = (round(X, 1), round(Y, 1), z > 0)
    routes.append({'city': name, 'slot': slot, 'd': ' '.join(segs), 'end': end})
hx, hy, hz = proj(HOME[0]*R_, HOME[1]*R_)
json.dump({'viewBox': 2000, 'home': [round(S + hx*S, 1), round(S - hy*S, 1)], 'routes': routes},
          open(f'{OUT}/routes.json', 'w'), indent=1)
print('dots', len(kept), 'drawn', sum(len(v) for v in rects.values()), 'home', round(S+hx*S), round(S-hy*S))
