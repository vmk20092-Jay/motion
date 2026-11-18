import math, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont

W, H, FPS, DUR = 1080, 1920, 30, 30.0
BEAT = 0.5  # 120 BPM
N = int(FPS * DUR)
import os
FD = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'fonts') + os.sep  # put ChosunNM.ttf here
# 조선일보명조 (single weight) -> weight simulated with stroke, as fraction of size
FONTS = {'black': ('ChosunNM.ttf', 0), 'bold': ('ChosunNM.ttf', 0), 'med': ('ChosunNM.ttf', 0), 'serif': ('ChosunNM.ttf', 0)}
STROKE = {'black': .030, 'bold': .016, 'med': .006, 'serif': .024}
_fc = {}
def F(name, size):
    k = (name, size)
    if k not in _fc: _fc[k] = ImageFont.truetype(FD + FONTS[name][0], size, index=FONTS[name][1])
    return _fc[k]

PAPER = (244, 240, 232); INK = (17, 17, 17); RED = (214, 32, 39); WHITE = (255, 255, 255); GREY = (120, 116, 110)

def clamp(x, a=0., b=1.): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def out_back(x, s=2.2):
    x -= 1; return x * x * ((s + 1) * x + s) + 1
def out_cubic(x): return 1 - (1 - x) ** 3

# ---------- word sprites ----------
_sc = {}
def sprite(text, font, size, color, box=None, track=0):
    k = (text, font, size, color, box, track)
    if k in _sc: return _sc[k]
    f = F(font, size)
    asc, desc = f.getmetrics()
    widths = [f.getlength(c) for c in text]
    tw = sum(widths) + track * (len(text) - 1)
    pad = int(size * 0.28)
    im = Image.new('RGBA', (int(tw + 2 * pad), asc + desc + 2 * pad), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    if box == 'outline':
        d.rounded_rectangle([4, 4, im.width - 5, im.height - 5], radius=int(size * .25), outline=color + (255,), width=max(3, size // 14))
    x = pad
    for c, w in zip(text, widths):
        sw = int(round(size * STROKE[font]))
        d.text((x, pad + asc), c, font=f, fill=color + (255,), anchor='ls', stroke_width=sw, stroke_fill=color + (255,)); x += w + track
    _sc[k] = im
    return im

def put(fr, im, cx, cy, scale=1., rot=0., alpha=1., clipw=1.):
    if alpha <= 0.01 or scale <= 0.01 or clipw <= 0.02: return
    if clipw < 1:
        im = im.crop((0, 0, max(1, int(im.width * clipw)), im.height))
        cx -= (im.width / clipw - im.width) / 2 * scale
    if scale != 1:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel('A').point(lambda v: int(v * alpha)))
    fr.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

# ---------- timeline ----------
# each word: text, t0 (beat-locked), t1 (exit), y, size, font, color, anim, extra
WORDS = []
def w(text, t0, t1, y, size, font='black', color=INK, anim='pop', x=W / 2, **kw):
    WORDS.append(dict(text=text, t0=t0, t1=t1, y=y, size=size, font=font, color=color, anim=anim, x=x, **kw))

# S1  0.0-2.0  the hook (paper)
w('내가 쓴 문장이', 0.0, 2.0, 820, 120)
w('내일 아침', 0.5, 2.0, 980, 130)
w('1면이 된다면?', 1.0, 2.0, 1150, 150, color=RED)
# S2  2.0-3.0  beat gag
w('.', 2.0, 3.0, 940, 220, x=W / 2 - 150); w('.', 2.25, 3.0, 940, 220); w('.', 2.5, 3.0, 940, 220, x=W / 2 + 150)
w('(두근)', 2.5, 3.0, 1180, 110, color=RED, anim='stamp', box='outline')
# S3  3.0-5.5  heritage in numbers
w('1920년 창간', 3.0, 5.5, 650, 100, font='bold')
w('106년', 3.5, 5.5, 830, 260, pulse=True)
w('매일 아침', 4.0, 5.5, 1060, 110, font='bold')
w('새 판', 4.5, 5.5, 1290, 330, color=RED, pulse=True)
# S4  5.5-7.0  build (riser)
w('100년을 써 온 신문사가', 5.5, 7.0, 760, 88, font='bold', anim='type')
w('다음 100년을', 6.0, 7.0, 900, 100, font='bold', anim='type')
w('함께 쓸 사람.', 6.5, 7.0, 1100, 170, color=RED)
# S5  7.0-10.0 DROP: roles slam (black)
for i, (tx, c) in enumerate([('기자', WHITE), ('PD', RED), ('영업', WHITE), ('마케팅', RED), ('IT 기획', WHITE)]):
    w(tx, 7.0 + i * BEAT, 7.0 + (i + 1) * BEAT, 960, 360 if len(tx) < 3 else 280, color=c, anim='slam')
w('당신의 자리,', 9.5, 10.0, 880, 150, color=WHITE)
w('여기에.', 9.5, 10.0, 1060, 170, color=RED, delay=0.12)
# S6  10.0-12.0 what the work is (paper)
w('취재는', 10.0, 12.0, 640, 96, font='bold', color=GREY)
w('현장에서', 10.5, 12.0, 800, 190, bar=True)
w('기획은', 11.0, 12.0, 1040, 96, font='bold', color=GREY)
w('사업으로', 11.5, 12.0, 1200, 190, bar=True)
# S6b 12.0-16.0 things you get to do (paper)
w('여기서 해보는 일', 12.0, 15.0, 520, 80, font='bold', color=GREY)
for i, tx in enumerate(['내 이름 단 기사', '국제 콘퍼런스 기획', '마라톤 대회 운영', '디지털 광고 영업']):
    w(tx, 12.5 + i * BEAT, 15.0, 680 + i * 140, 86, font='black', color=INK, check=True)
w('신문사인데', 15.0, 16.0, 860, 130, color=INK)
w('이것까지 한다고?', 15.5, 16.0, 1040, 150, color=RED)
# S6c 16.0-17.5 (black)
w('쓰고', 16.0, 17.5, 720, 190, color=WHITE)
w('만들고', 16.5, 17.5, 950, 190, color=WHITE)
w('키운다', 17.0, 17.5, 1180, 190, color=RED)
# S6d 17.5-19.0 build 2 (paper, riser)
w('인턴부터,', 17.5, 19.0, 830, 120, font='bold', anim='type')
w('채용연계형으로.', 18.0, 19.0, 1010, 140, color=RED, anim='type')
# S7  19.0-21.0 DROP 2: credibility (black)
w('100년의 힘', 19.0, 21.0, 850, 150, color=WHITE, anim='slam')
w('1등 디지털뉴스', 19.5, 21.0, 1040, 140, color=RED, underline=True)
# S7b 21.0-24.0 reach (paper)
w('신문 · 방송 · 디지털', 21.0, 24.0, 640, 100, font='bold')
w('1000만', 22.0, 24.0, 900, 300, color=RED, pulse=True)
w('오디언스와 함께', 22.5, 24.0, 1130, 120)
w('당신의 기획이 닿는 곳', 23.0, 24.0, 1330, 80, font='bold', color=GREY, anim='type')
# S8  24.0-30.0 brand + call (red)
w('조선일보', 24.0, 30.1, 760, 215, font='serif', color=WHITE, anim='slam', pulse=True)
w('다음 100년을 함께 쓸 사람', 24.5, 30.1, 960, 78, font='bold', color=WHITE, anim='type')
w('기자 · PD · 미디어경영', 25.5, 30.1, 1090, 64, font='bold', color=(255, 225, 225), anim='pop')
w('당신의 1면을 쓰세요.', 26.5, 30.1, 1250, 100, font='black', color=WHITE, anim='pop')
w('chosun.com', 27.5, 30.1, 1420, 66, font='bold', color=WHITE, box='outline', track=2)

BG = [(0, 7.0, PAPER), (7.0, 10.0, INK), (10.0, 16.0, PAPER), (16.0, 17.5, INK), (17.5, 19.0, PAPER), (19.0, 21.0, INK), (21.0, 24.0, PAPER), (24.0, 99, RED)]
CUTS = [2.0, 3.0, 5.5, 7.0, 10.0, 12.0, 16.0, 17.5, 19.0, 21.0, 24.0]
BREAKS = [(5.5, 7.0), (17.5, 19.0)]
HITS = (7.0, 19.0, 24.0)
KICKS = [k * BEAT for k in range(57) if not any(a <= k * BEAT < b for a, b in BREAKS)]

def bg_at(t):
    for a, b, c in BG:
        if a <= t < b: return c
    return BG[-1][2]

def kick_env(t):
    """0..1 envelope of the most recent kick, for pulses / shake"""
    last = max([k for k in KICKS if k <= t], default=-9)
    return math.exp(-(t - last) * 9)

def render(t):
    bgc = bg_at(t)
    fr = Image.new('RGB', (W, H), bgc)
    d = ImageDraw.Draw(fr)
    ink_on = INK if bgc == PAPER else WHITE
    # newspaper rules: thin column lines + masthead bar, gives the "paper" texture
    rule = tuple(int(c * .88) for c in bgc) if bgc != INK else (44, 44, 44)
    for x in (90, W - 90): d.line([(x, 0), (x, H)], fill=rule, width=2)
    d.line([(90, 300), (W - 90, 300)], fill=rule, width=3); d.line([(90, 312), (W - 90, 312)], fill=rule, width=1)
    d.line([(90, 1560), (W - 90, 1560)], fill=rule, width=1)
    # build-up: progress bar during the riser
    for ba, bb in BREAKS:
      if ba <= t < bb:
        p = prog(t, ba, bb)
        d.rectangle([90, 1500, 90 + (W - 180) * p, 1512], fill=RED)
    # shake on drop & brand slam
    sh = 0
    for hit in HITS:
        if hit <= t < hit + .35: sh = 18 * (1 - prog(t, hit, hit + .35)) * math.sin(t * 90)
    ke = kick_env(t)
    # header tag (who's asking) during S1-S2
    if t < 3.0:
        asker = '기자' if t < 0.5 else ('PD' if t < 1.0 else '미디어경영')
        tag = sprite(' ' + asker + ' 지망생이라면 ', 'bold', 64, WHITE)
        tb = Image.new('RGBA', (tag.width, tag.height), RED + (255,)); tb.alpha_composite(tag)
        put(fr, tb, W / 2, 520, scale=1 + .08 * ke)
    for wd in WORDS:
        t0 = wd['t0'] + wd.get('delay', 0)
        if not (t0 <= t < wd['t1']): continue
        dt = t - t0
        im = sprite(wd['text'], wd['font'], wd['size'], wd['color'], wd.get('box'), wd.get('track', 0))
        sc, rot, al, clip = 1., 0., 1., 1.
        a = wd['anim']
        if a == 'pop':
            sc = out_back(prog(dt, 0, .22)); al = prog(dt, 0, .08)
        elif a == 'slam':
            p = prog(dt, 0, .16); sc = 1.9 - .9 * out_cubic(p); al = prog(dt, 0, .06)
        elif a == 'stamp':
            p = prog(dt, 0, .14); sc = 2.4 - 1.4 * out_cubic(p); rot = 8; al = p
        elif a == 'type':
            clip = clamp(dt / .38); al = 1
        if wd.get('pulse') and dt > .2: sc *= 1 + .07 * ke
        # exit: quick squash right before cut
        ex = prog(t, wd['t1'] - .07, wd['t1'])
        if ex > 0 and wd['t1'] < 30: sc *= 1 - .25 * ex; al *= 1 - ex
        cx, cy = wd['x'] + sh, wd['y']
        if wd.get('bar'):
            p = out_cubic(prog(dt, 0, .25))
            bw = (im.width - im.height * .3) * p
            d.rectangle([cx - bw / 2, cy - 10, cx + bw / 2, cy + im.height * .3], fill=(255, 205, 210) if bgc == PAPER else RED)
        if wd.get('check'):
            cxl = 172; p = out_back(prog(dt, 0, .2))
            d.rectangle([cxl - 34 * p, cy - 34 * p, cxl + 34 * p, cy + 34 * p], outline=INK, width=5)
            if dt > .12:
                q = prog(dt, .12, .3)
                pts = [(cxl - 20, cy), (cxl - 5, cy + 18), (cxl + 30, cy - 30)]
                d.line(pts[:2] if q < .4 else pts, fill=RED, width=9)
            cx = 260 + im.width / 2 - im.height * .28
        put(fr, im, cx, cy, sc, rot, al, clip)
        if wd.get('underline'):
            p = out_cubic(prog(dt, .1, .45)); uw = (im.width - im.height * .56) * p
            d.rectangle([cx - uw / 2, cy + im.height * .42, cx + uw / 2, cy + im.height * .42 + 10], fill=WHITE)
    # flash on cuts
    for c in CUTS:
        if c <= t < c + 2 / FPS:
            fr = Image.blend(fr, Image.new('RGB', (W, H), WHITE if bgc != PAPER else INK), .35 if c not in HITS else .7)
    return np.asarray(fr)

if __name__ == '__main__':
    if sys.argv[1] == 'test':
        for tt in map(float, sys.argv[2:]):
            Image.fromarray(render(tt)).save(f'f_{tt:05.2f}.jpg', quality=85)
    else:
        p = subprocess.Popen(['ffmpeg', '-y', '-v', 'error', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                              '-i', '-', '-c:v', 'libx264', '-crf', '17', '-preset', 'veryfast', '-pix_fmt', 'yuv420p', sys.argv[2]],
                             stdin=subprocess.PIPE)
        for k in range(N): p.stdin.write(render(k / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
