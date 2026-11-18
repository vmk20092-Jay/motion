import math, random, sys, subprocess
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H, FPS, DUR = 1080, 1920, 30, 10.0
N = int(FPS * DUR)
FD = '/usr/share/fonts/opentype/noto/'
def font(name, size): return ImageFont.truetype(FD + name, size, index=1)

SERIF_B = 'NotoSerifCJK-Bold.ttc'
SERIF_L = 'NotoSerifCJK-Light.ttc'
SERIF_XL = 'NotoSerifCJK-ExtraLight.ttc'
SANS_L = 'NotoSansCJK-Light.ttc'

CREAM = (243, 230, 210)
AMBER = (232, 150, 62)
RUST = (196, 88, 44)
PALE = (196, 210, 222)
DIM = (196, 166, 132)

# ---------- easing ----------
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def prog(t, a, b): return clamp((t - a) / (b - a))
def out_cubic(x): return 1 - (1 - x) ** 3
def in_cubic(x): return x ** 3
def out_back(x, s=1.6):
    x -= 1
    return x * x * ((s + 1) * x + s) + 1
def in_out(x): return 3 * x * x - 2 * x ** 3
def out_elastic(x):
    if x <= 0: return 0
    if x >= 1: return 1
    return 2 ** (-10 * x) * math.sin((x * 10 - 0.75) * (2 * math.pi) / 3) + 1

# ---------- glyph sprites ----------
_cache = {}
def sprite(ch, fname, size, color, glow=0):
    key = (ch, fname, size, color, glow)
    if key in _cache: return _cache[key]
    f = font(fname, size)
    asc, desc = f.getmetrics()
    adv = f.getlength(ch)
    p = int(size * 0.35) + glow * 3
    w, h = int(adv + 2 * p), int(asc + desc + 2 * p)
    im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.text((p, p + asc), ch, font=f, fill=color + (255,), anchor='ls')
    if glow:
        g = im.copy().filter(ImageFilter.GaussianBlur(glow))
        ga = np.array(g).astype(np.float32)
        ga[..., 3] *= 1.6
        g = Image.fromarray(np.clip(ga, 0, 255).astype(np.uint8))
        g.alpha_composite(im)
        im = g
    _cache[key] = (im, adv)
    return _cache[key]

def layout(text, fname, size, tracking=0):
    """returns list of (char, center_x_offset) relative to line start, total width"""
    f = font(fname, size)
    out, x = [], 0
    for ch in text:
        a = f.getlength(ch)
        out.append((ch, x + a / 2))
        x += a + tracking
    return out, x - tracking

def put(frame, im, cx, cy, rot=0, scale=1.0, alpha=1.0, sx=1.0):
    if alpha <= 0.003: return
    if scale != 1.0 or sx != 1.0:
        nw = max(1, int(im.width * scale * abs(sx))); nh = max(1, int(im.height * scale))
        im = im.resize((nw, nh), Image.BICUBIC)
    if rot:
        im = im.rotate(rot, resample=Image.BICUBIC, expand=True)
    if alpha < 1:
        a = im.getchannel('A').point(lambda v: int(v * alpha))
        im = im.copy(); im.putalpha(a)
    frame.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

# ---------- background ----------
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
def background(t):
    # warm dusk gradient with a slowly drifting low sun glow
    base = np.zeros((H, W, 3), np.float32)
    top = np.array([22, 14, 11], np.float32); bot = np.array([52, 26, 14], np.float32)
    v = (yy / H)[..., None]
    base[:] = top * (1 - v) + bot * v
    gx = W * (0.30 + 0.25 * t / DUR); gy = H * 1.05
    r = np.sqrt((xx - gx) ** 2 + ((yy - gy) * 1.4) ** 2)
    glow = np.exp(-(r / 900) ** 2)[..., None]
    base += glow * np.array([120, 58, 18], np.float32) * (0.85 + 0.15 * math.sin(t * 1.3))
    return base

rng = np.random.default_rng(7)
GRAIN = [rng.normal(0, 7, (H, W, 1)).astype(np.float32) for _ in range(6)]
vig = (1 - 0.55 * (((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)).clip(0.25, 1)[..., None]

# ---------- leaves ----------
def leaf_img(size, color, blur):
    s = size * 2
    im = Image.new('RGBA', (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    pts = []
    for i in range(41):
        a = i / 40 * 2 * math.pi
        rr = s * 0.42 * (abs(math.sin(a / 2)) ** 0.9)
        pts.append((s / 2 + rr * math.sin(a) * 0.85, s / 2 - rr * math.cos(a)))
    d.polygon(pts, fill=color + (235,))
    dark = tuple(int(c * 0.7) for c in color)
    d.line([(s / 2, s * 0.12), (s / 2, s * 0.98)], fill=dark + (255,), width=max(1, size // 18))
    if blur: im = im.filter(ImageFilter.GaussianBlur(blur))
    return im

random.seed(11)
LCOL = [(196, 88, 44), (214, 128, 50), (170, 62, 36), (226, 168, 72), (140, 70, 38)]
LEAVES = []
for i in range(30):
    depth = random.random()  # 0 far, 1 near
    size = int(18 + depth * 46)
    blur = 3 if depth < 0.3 else (0 if depth < 0.85 else 4)
    LEAVES.append(dict(
        img=leaf_img(size, random.choice(LCOL), blur),
        x0=random.uniform(-100, W + 100), y0=random.uniform(-H, H),
        vy=40 + depth * 90, vx=-25 - depth * 30, sway=random.uniform(30, 90),
        sw=random.uniform(0.6, 1.4), ph=random.uniform(0, 6.28),
        rs=random.uniform(-90, 90), flip=random.uniform(1.0, 2.6),
        alpha=0.35 + depth * 0.55, depth=depth))

def draw_leaves(frame, t, front):
    for L in LEAVES:
        if (L['depth'] > 0.8) != front: continue
        wind = 0
        if 4.5 < t < 5.6: wind = 260 * math.sin(prog(t, 4.5, 5.6) * math.pi)  # gust with scene B exit
        y = (L['y0'] + L['vy'] * t) % (H + 300) - 150
        x = (L['x0'] + L['vx'] * t + L['sway'] * math.sin(t * L['sw'] + L['ph']) + wind * (0.5 + L['depth'])) % (W + 300) - 150
        rot = L['rs'] * t + 30 * math.sin(t * L['sw'] + L['ph'])
        sx = math.cos(t * L['flip'] + L['ph'])
        sx = sx if abs(sx) > 0.12 else 0.12
        put(frame, L['img'], x, y, rot=rot, sx=sx, alpha=L['alpha'])

# ---------- scenes ----------
def scene_a(fr, t):  # 0 - 2.7  "11월" falls like leaves
    if t > 2.8: return
    size = 300
    chars, tw = layout('11월', SERIF_B, size, tracking=-10)
    x0 = W / 2 - tw / 2; cy = H / 2 - 60
    for i, (ch, ox) in enumerate(chars):
        st = 0.15 + i * 0.22
        p = prog(t, st, st + 1.0)
        e = out_back(p, 1.2)
        y = cy - (1 - e) * 620
        x = x0 + ox + (1 - p) * 120 * math.sin(p * 9 + i)
        rot = (1 - e) * (60 - i * 50)
        col = AMBER if ch == '월' else CREAM
        # exit: drift upward & dissolve
        q = prog(t, 2.15 + i * 0.07, 2.7 + i * 0.07)
        y -= in_cubic(q) * 90; rot += q * 12 * (i - 1)
        a = min(prog(t, st, st + 0.35), 1 - q)
        im, _ = sprite(ch, SERIF_B, size, col, glow=10 if ch == '월' else 0)
        put(fr, im, x, y, rot=rot, alpha=a)
    # NOVEMBER tracking out
    p = out_cubic(prog(t, 0.9, 2.4))
    q = prog(t, 2.2, 2.7)
    tr = 10 + 46 * p
    chars, tw = layout('NOVEMBER', SANS_L, 34, tracking=tr)
    for ch, ox in chars:
        im, _ = sprite(ch, SANS_L, 34, DIM)
        put(fr, im, W / 2 - tw / 2 + ox, cy + 230, alpha=prog(t, 0.9, 1.4) * (1 - q))

def word_line(fr, t, text, fname, size, x, y, start, color, glow=0, exit_t=None, exit_fn=None, tracking=0):
    chars, tw = layout(text, fname, size, tracking)
    for i, (ch, ox) in enumerate(chars):
        st = start + i * 0.045
        p = prog(t, st, st + 0.55)
        e = out_cubic(p)
        cx = x + ox; cy = y + (1 - e) * 70
        sc = 1 + (1 - e) * 0.35
        a = prog(t, st, st + 0.3)
        rot = 0
        if exit_t is not None and t > exit_t:
            cx, cy, rot, a2 = exit_fn(t - exit_t, i, len(chars), cx, cy)
            a *= a2
        im, _ = sprite(ch, fname, size, color, glow)
        put(fr, im, cx, cy, rot=rot, scale=sc, alpha=a)
    return tw

def wind_exit(dt, i, n, cx, cy):
    d = clamp((dt - (n - i) * 0.03) / 0.7)
    e = in_cubic(d)
    return cx + e * 900, cy - e * 120 + math.sin(d * 6 + i) * 30 * d, e * 140, 1 - d

def fall_exit(dt, i, n, cx, cy):
    random.seed(i * 31 + n)
    d = clamp((dt - random.uniform(0, 0.25)) / 0.75)
    e = in_cubic(d)
    return cx + math.sin(d * 5 + i) * 60 * d, cy + e * 760, e * random.uniform(-160, 160), 1 - d ** 2

def scene_b(fr, t):  # 2.6 - 5.4  wind gets colder
    if not (2.5 < t < 5.6): return
    lx = 120
    word_line(fr, t, '바람이', SERIF_L, 110, lx, 760, 2.65, CREAM, exit_t=4.55, exit_fn=wind_exit)
    word_line(fr, t, '조금', SERIF_L, 110, lx, 910, 2.95, CREAM, exit_t=4.6, exit_fn=wind_exit)
    word_line(fr, t, '차가워지고', SERIF_B, 152, lx, 1090, 3.25, PALE, exit_t=4.65, exit_fn=wind_exit)
    # thin rule that sweeps in
    p = out_cubic(prog(t, 3.0, 4.0)); q = in_cubic(prog(t, 4.6, 5.2))
    d = ImageDraw.Draw(fr)
    x1 = lx + (W - 2 * lx) * p
    if p > 0: d.line([(lx + (W - 2 * lx) * q, 1200), (x1, 1200)], fill=(150, 120, 95), width=2)

def scene_c(fr, t):  # 5.2 - 7.9  heart gets warmer
    if not (5.1 < t < 8.1): return
    rx = W - 120
    def right(text, fname, size, y, st, col, glow=0):
        _, tw = layout(text, fname, size)
        word_line(fr, t, text, fname, size, rx - tw, y, st, col, glow, exit_t=7.25, exit_fn=fall_exit)
    right('마음은', SERIF_L, 110, 760, 5.3, CREAM)
    right('조금 더', SERIF_L, 110, 910, 5.6, CREAM)
    # warm word: glow breathes
    right('따뜻해지는', SERIF_B, 152, 1090, 5.9, AMBER, glow=14)

def scene_d(fr, t):  # 7.8 - 10
    if t < 7.7: return
    chars, tw = layout('가을, 그 끝자락에서', SERIF_L, 78, tracking=4)
    x0 = W / 2 - tw / 2; cy = H / 2 - 30
    fade = 1 - prog(t, 9.4, 9.95)
    for i, (ch, ox) in enumerate(chars):
        st = 7.85 + i * 0.06
        p = prog(t, st, st + 0.9)
        e = out_cubic(p)
        a = prog(t, st, st + 0.5) * fade
        col = AMBER if ch in '가을' else CREAM
        im, _ = sprite(ch, SERIF_L, 78, col, glow=8 if ch in '가을' else 0)
        put(fr, im, x0 + ox, cy - (1 - e) * 40, rot=(1 - e) * -8, alpha=a)
    p = out_cubic(prog(t, 8.5, 9.3))
    d = ImageDraw.Draw(fr)
    if p > 0 and fade > 0:
        c = tuple(int(v * fade) for v in (150, 120, 95))
        d.line([(W / 2 - 160 * p, cy + 95), (W / 2 + 160 * p, cy + 95)], fill=c, width=2)
    chars, tw = layout('2026 · 11', SANS_L, 30, tracking=14)
    for ch, ox in chars:
        im, _ = sprite(ch, SANS_L, 30, DIM)
        put(fr, im, W / 2 - tw / 2 + ox, cy + 145, alpha=prog(t, 8.8, 9.3) * fade)

def render(t):
    bg = background(t)
    fr = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8), 'RGB')
    draw_leaves(fr, t, front=False)
    scene_a(fr, t); scene_b(fr, t); scene_c(fr, t); scene_d(fr, t)
    draw_leaves(fr, t, front=True)
    a = np.asarray(fr).astype(np.float32) * vig + GRAIN[int(t * FPS) % 6]
    fin = 1 - prog(t, 9.6, 10.0)  # fade to black
    st = prog(t, 0, 0.3)
    return np.clip(a * fin * st, 0, 255).astype(np.uint8)

if __name__ == '__main__':
    if sys.argv[1] == 'test':
        for tt in map(float, sys.argv[2:]):
            Image.fromarray(render(tt)).save(f'test_{tt:.1f}.jpg', quality=88)
    else:
        out = sys.argv[2]
        p = subprocess.Popen(['ffmpeg', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                              '-i', '-', '-c:v', 'libx264', '-crf', '18', '-preset', 'veryfast', '-pix_fmt', 'yuv420p',
                              '-movflags', '+faststart', out], stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
        for k in range(N):
            p.stdin.write(render(k / FPS).tobytes())
        p.stdin.close(); sys.exit(p.wait())
