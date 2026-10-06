"""Source vs ours, beat by beat: the same moments of the two 30 s films side by side."""
import subprocess, sys
from PIL import Image, ImageDraw, ImageFont
src, ours, out = sys.argv[1:4]
FF = 'ffmpeg'
beats = [  # (label, source t, ours t)
    ('hook', 2.9, 2.8), ('brand', 4.9, 4.8), ('feature 1', 8.9, 8.9), ('feature 2', 13.9, 14.9),
    ('feature 3', 17.4, 21.4), ('dark beat', 21.9, 18.8), ('proof', 23.6, 24.8), ('end card', 29.0, 29.0)]
f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 22)
def grab(path, t, w, h):
    tmp = f'/tmp/cmp_{abs(hash((path, t)))}.png'
    subprocess.run([FF, '-loglevel', 'error', '-y', '-ss', str(t), '-i', path, '-frames:v', '1', tmp], check=True)
    im = Image.open(tmp).convert('RGB'); im.thumbnail((w, h)); return im
W, H = 300, 534
o = Image.new('RGB', (len(beats) * (W + 12) + 12, 60 + 170 + 12 + H + 40), '#D9D7D2')
d = ImageDraw.Draw(o)
d.text((12, 14), 'Исходник (16:9) сверху · наш Unimatch (9:16) снизу — те же биты', fill='#111114', font=f)
for i, (lab, ts, to) in enumerate(beats):
    x = 12 + i * (W + 12)
    a = grab(src, ts, W, 170); o.paste(a, (x, 60))
    b = grab(ours, to, W, H); o.paste(b, (x, 60 + 170 + 12))
    d.text((x, 60 + 170 + 12 + H + 8), f'{lab} · {to:.1f}s', fill='#111114', font=f)
o.save(out, quality=88)
print(out, o.size)
