"""Mount the original music bed at the index root (assemble-index has no audio_meta for it)."""
import sys
p = sys.argv[1] + '/index.html'
s = open(p).read()
tag = ('      <audio id="bgm" src="assets/audio/unimatch-bed.mp3" data-start="0" data-duration="30" '
       'data-track-index="11" data-volume="1"></audio>\n')
if 'id="bgm"' not in s:
    i = s.rindex('    </div>')  # the root's closing tag
    s = s[:i] + tag + s[i:]
open(p, 'w').write(s)
print('bgm mounted')
