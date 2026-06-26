# made by onuraltanuyar

import pygame
import sys
import math
import random
import time
import json
import os

pygame.init()
pygame.font.init()

try:
    import numpy as np
    NUMPY_OK = True
except Exception:
    NUMPY_OK = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAVE_PATH = os.path.join(BASE_DIR, "karanlik_ev_kayit.json")
SETTINGS_PATH = os.path.join(BASE_DIR, "karanlik_ev_ayarlar.json")
ACHIEVEMENTS_PATH = os.path.join(BASE_DIR, "karanlik_ev_basarimlar.json")

DEFAULT_SETTINGS = {
    "music_vol": 0.5,
    "sfx_vol": 0.8,
    "text_speed_mult": 1.0,
    "shake_enabled": True,
    "flash_enabled": True,
}


def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(default, dict):
                    merged = dict(default)
                    merged.update(data)
                    return merged
                return data
    except Exception:
        pass
    if default is None:
        return None
    return json.loads(json.dumps(default))


def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


W, H = 900, 600
screen = pygame.display.set_mode((W, H))
pygame.display.set_caption("KARANLIK EV  |  Horror Story")
clock = pygame.time.Clock()

BLACK    = (0, 0, 0)
DARK     = (10, 5, 15)
RED      = (180, 20, 20)
DIM_RED  = (80, 10, 10)
WHITE    = (230, 220, 210)
GRAY     = (120, 110, 100)
DARKGRAY = (60, 55, 60)
YELLOW   = (200, 170, 60)
BLOOD    = (120, 0, 0)
SHADOW   = (20, 10, 30)
GREEN    = (30, 100, 40)
PURPLE   = (80, 20, 120)
TEAL     = (20, 80, 90)
AMBER    = (180, 100, 20)
PALE     = (200, 185, 170)
LOCKGRAY = (70, 65, 65)


def _find_turkish_font(size, bold=False):
    candidates = [
        "dejavusans",
        "freesans",
        "liberationsans",
        "arial",
        "notosans",
        "unifont",
        "segoeuisymbol",
        "tahoma",
        "verdana",
    ]
    for name in candidates:
        try:
            f = pygame.font.SysFont(name, size, bold=bold)
            test = f.render("ğüşıöçĞÜŞİÖÇ", True, (255, 255, 255))
            if test.get_width() > 10:
                return f
        except Exception:
            continue
    return pygame.font.Font(None, size)


def _find_font_file(size, bold=False):
    import platform
    search_dirs = []
    system = platform.system()
    if system == "Linux":
        search_dirs = [
            "/usr/share/fonts/truetype/dejavu",
            "/usr/share/fonts/truetype/freefont",
            "/usr/share/fonts/truetype/liberation",
            "/usr/share/fonts/truetype/noto",
            "/usr/share/fonts",
            "/usr/local/share/fonts",
        ]
        file_names = [
            ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"),
            ("FreeSerifBold.ttf" if bold else "FreeSans.ttf"),
            ("LiberationSans-Bold.ttf" if bold else "LiberationSans-Regular.ttf"),
            "NotoSans-Regular.ttf",
        ]
    elif system == "Windows":
        search_dirs = [r"C:\Windows\Fonts"]
        file_names = ["arial.ttf", "tahoma.ttf", "verdana.ttf"]
    elif system == "Darwin":
        search_dirs = ["/Library/Fonts", "/System/Library/Fonts"]
        file_names = ["Arial.ttf", "Helvetica.ttf"]
    else:
        file_names = []

    for d in search_dirs:
        for fn in file_names:
            fp = os.path.join(d, fn)
            if os.path.isfile(fp):
                try:
                    return pygame.font.Font(fp, size)
                except Exception:
                    continue
    return None


def _make_font(size, bold=False):
    ff = _find_font_file(size, bold)
    if ff:
        return ff
    sf = _find_turkish_font(size, bold)
    return sf


font_xl   = _make_font(52, bold=True)
font_lg   = _make_font(38, bold=True)
font_md   = _make_font(22)
font_sm   = _make_font(17)
font_mono = _make_font(18)

_VIGNETTE_CACHE = {}

def _get_vignette(strength=180):
    if strength in _VIGNETTE_CACHE:
        return _VIGNETTE_CACHE[strength]
    vig = pygame.Surface((W, H), pygame.SRCALPHA)
    for i in range(60):
        alpha = int(strength * (i / 60) ** 2)
        pygame.draw.rect(vig, (0, 0, 0, alpha), (i, i, W - 2*i, H - 2*i), 1)
    _VIGNETTE_CACHE[strength] = vig
    return vig

BASEMENT_BLOOD_POS = [(random.randint(100, 800), random.randint(400, 540),
                        random.randint(5, 20), random.randint(3, 10)) for _ in range(8)]


class SoundManager:
    SR = 44100

    def __init__(self, settings):
        self.enabled = False
        self.music_vol = settings.get("music_vol", 0.5)
        self.sfx_vol = settings.get("sfx_vol", 0.8)
        self._cache = {}
        self._ambient_channel = None
        if not NUMPY_OK:
            return
        try:
            pygame.mixer.init(frequency=self.SR, size=-16, channels=1)
            self.enabled = True
            self._build_all()
        except Exception:
            self.enabled = False

    def _envelope(self, n, attack=0.02, release=0.3):
        env = np.ones(n)
        a = max(1, int(n * attack))
        r = max(1, int(n * release))
        env[:a] = np.linspace(0, 1, a)
        env[-r:] = np.minimum(env[-r:], np.linspace(1, 0, r))
        return env

    def _to_sound(self, wave, vol=1.0):
        wave = np.clip(wave * vol, -1, 1)
        arr = (wave * 32767).astype(np.int16)
        return pygame.sndarray.make_sound(arr)

    def _tone(self, freq, dur, vol=0.5, attack=0.02, release=0.4):
        n = int(self.SR * dur)
        t = np.linspace(0, dur, n, False)
        wave = np.sin(2 * np.pi * freq * t)
        wave *= self._envelope(n, attack, release)
        return self._to_sound(wave, vol)

    def _sweep(self, f_start, f_end, dur, vol=0.5, attack=0.02, release=0.5):
        n = int(self.SR * dur)
        freq = np.linspace(f_start, f_end, n)
        phase = np.cumsum(2 * np.pi * freq / self.SR)
        wave = np.sin(phase)
        wave *= self._envelope(n, attack, release)
        return self._to_sound(wave, vol)

    def _noise_burst(self, dur, vol=0.4, lowpass=0.0, attack=0.0, release=0.6):
        n = int(self.SR * dur)
        wave = np.random.uniform(-1, 1, n)
        if lowpass > 0:
            k = max(1, int(lowpass))
            kernel = np.ones(k) / k
            wave = np.convolve(wave, kernel, mode="same")
        wave *= self._envelope(n, attack, release)
        return self._to_sound(wave, vol)

    def _build_all(self):
        try:
            self._cache["click"]    = self._tone(720, 0.06, 0.5, 0.005, 0.7)
            self._cache["select"]   = self._tone(440, 0.09, 0.5, 0.01, 0.6)
            self._cache["page"]     = self._sweep(220, 160, 0.18, 0.35, 0.02, 0.7)
            self._cache["door"]     = self._sweep(90, 50, 1.1, 0.5, 0.05, 0.6)
            self._cache["footstep"] = self._noise_burst(0.18, 0.35, lowpass=18, attack=0.01, release=0.6)
            self._cache["chime"]    = self._build_chime()
            self._cache["scare"]    = self._build_scare()
            self._cache["lock"]     = self._tone(200, 0.12, 0.4, 0.01, 0.7)
            self._cache["pickup"]   = self._build_pickup()
            self._cache["ambient"]  = self._build_ambient()
        except Exception:
            self.enabled = False

    def _build_chime(self):
        notes = [440, 554, 659, 880]
        parts = []
        for f in notes:
            n = int(self.SR * 0.22)
            t = np.linspace(0, 0.22, n, False)
            wave = np.sin(2 * np.pi * f * t) * self._envelope(n, 0.05, 0.6)
            parts.append(wave)
        full = np.concatenate(parts)
        return self._to_sound(full, 0.4)

    def _build_pickup(self):
        n = int(self.SR * 0.3)
        freq = np.linspace(300, 900, n)
        phase = np.cumsum(2 * np.pi * freq / self.SR)
        wave = np.sin(phase) * self._envelope(n, 0.02, 0.6)
        return self._to_sound(wave, 0.45)

    def _build_scare(self):
        dur = 0.7
        n = int(self.SR * dur)
        t = np.linspace(0, dur, n, False)
        tone = (np.sin(2 * np.pi * 110 * t) + np.sin(2 * np.pi * 116 * t)) * 0.5
        noise = np.random.uniform(-1, 1, n) * 0.6
        wave = tone * 0.6 + noise * 0.6
        wave *= self._envelope(n, 0.005, 0.85)
        return self._to_sound(wave, 0.7)

    def _build_ambient(self):
        dur = 6.0
        n = int(self.SR * dur)
        t = np.linspace(0, dur, n, False)
        drone = np.sin(2 * np.pi * 55 * t) * 0.25
        drone += np.sin(2 * np.pi * 82 * t + 0.3) * 0.12
        wobble = 1.0 + 0.08 * np.sin(2 * np.pi * 0.2 * t)
        drone *= wobble
        noise = np.random.uniform(-1, 1, n)
        kernel = np.ones(40) / 40
        noise = np.convolve(noise, kernel, mode="same") * 0.15
        wave = drone + noise
        fade = np.ones(n)
        fl = int(self.SR * 0.5)
        fade[:fl] = np.linspace(0, 1, fl)
        fade[-fl:] = np.linspace(1, 0, fl)
        wave *= fade
        return self._to_sound(wave, 1.0)

    def play(self, key):
        if not self.enabled:
            return
        snd = self._cache.get(key)
        if snd:
            snd.set_volume(self.sfx_vol)
            snd.play()

    def start_ambient(self):
        if not self.enabled:
            return
        snd = self._cache.get("ambient")
        if snd:
            snd.set_volume(self.music_vol)
            self._ambient_channel = snd.play(loops=-1)

    def stop_ambient(self):
        if self._ambient_channel:
            try:
                self._ambient_channel.stop()
            except Exception:
                pass
            self._ambient_channel = None

    def apply_volumes(self):
        if self._ambient_channel:
            try:
                self._ambient_channel.set_volume(self.music_vol)
            except Exception:
                pass


def draw_text_wrapped(surface, text, font, color, rect, line_spacing=6):
    paragraphs = text.split("\n")
    lines = []
    for para in paragraphs:
        if para == "":
            lines.append("")
            continue
        words = para.split()
        current = ""
        for w in words:
            test = (current + " " + w).strip()
            if font.size(test)[0] <= rect.width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

    y = rect.top
    for line in lines:
        if y + font.get_height() > rect.bottom:
            break
        if line:
            surf = font.render(line, True, color)
            surface.blit(surf, (rect.left, y))
        y += font.get_height() + line_spacing
    return y


def flicker(base_alpha, t, speed=3.0, amount=30):
    noise = math.sin(t * speed) * amount * 0.5 + math.sin(t * speed * 2.3) * amount * 0.3
    return max(0, min(255, int(base_alpha + noise)))


def draw_vignette(surface, strength=180):
    vig = _get_vignette(strength)
    surface.blit(vig, (0, 0))


def noise_overlay(surface, t, density=0.015):
    for _ in range(int(W * H * density)):
        x = random.randint(0, W-1)
        y = random.randint(0, H-1)
        v = random.randint(0, 60)
        surface.set_at((x, y), (v, v, v))


def draw_button(surface, rect, text, font, hover, enabled=True, base_col=(30, 8, 8),
                hover_col=(100, 20, 20), border_col=(120, 20, 20), text_col=None):
    btn_surf = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
    if not enabled:
        btn_surf.fill((25, 22, 22, 150))
        pygame.draw.rect(btn_surf, (50, 45, 45, 160), (0, 0, rect.width, rect.height), 2)
        col = LOCKGRAY
    elif hover:
        btn_surf.fill((*hover_col, 210))
        pygame.draw.rect(btn_surf, (220, 60, 60, 255), (0, 0, rect.width, rect.height), 2)
        col = WHITE
    else:
        btn_surf.fill((*base_col, 190))
        pygame.draw.rect(btn_surf, (*border_col, 190), (0, 0, rect.width, rect.height), 1)
        col = GRAY
    if text_col:
        col = text_col
    surface.blit(btn_surf, (rect.left, rect.top))
    txt = font.render(text, True, col)
    surface.blit(txt, (rect.centerx - txt.get_width() // 2, rect.centery - txt.get_height() // 2))


def draw_haunted_house(surface, t):
    for y in range(H):
        ratio = y / H
        r = int(5 + 15 * ratio)
        g = int(0 + 8 * ratio)
        b = int(15 + 25 * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (W, y))

    moon_alpha = flicker(200, t, 0.5, 20)
    moon_surf = pygame.Surface((90, 90), pygame.SRCALPHA)
    pygame.draw.circle(moon_surf, (220, 210, 170, moon_alpha), (45, 45), 45)
    pygame.draw.circle(moon_surf, (180, 170, 130, moon_alpha // 2), (45, 45), 42)
    surface.blit(moon_surf, (680, 40))

    for cx, cy, cw, ch in [(680, 60, 120, 30), (730, 75, 80, 20)]:
        cloud = pygame.Surface((cw, ch), pygame.SRCALPHA)
        cloud.fill((30, 20, 40, 120))
        surface.blit(cloud, (cx, cy))

    for tx, th in [(60, 200), (120, 170), (30, 220), (155, 190)]:
        pygame.draw.rect(surface, (15, 8, 5), (tx - 6, H - th, 12, th))
        for branch_y in range(H - th, H - 40, 30):
            pygame.draw.line(surface, (15, 8, 5), (tx, branch_y), (tx - 40, branch_y + 20), 3)
            pygame.draw.line(surface, (15, 8, 5), (tx, branch_y), (tx + 35, branch_y + 15), 3)

    for tx, th in [(800, 210), (840, 180), (870, 230)]:
        pygame.draw.rect(surface, (15, 8, 5), (tx - 6, H - th, 12, th))
        for branch_y in range(H - th, H - 40, 30):
            pygame.draw.line(surface, (15, 8, 5), (tx, branch_y), (tx - 35, branch_y + 20), 3)
            pygame.draw.line(surface, (15, 8, 5), (tx, branch_y), (tx + 40, branch_y + 15), 3)

    pygame.draw.rect(surface, (20, 15, 10), (0, H - 80, W, 80))
    pygame.draw.rect(surface, (25, 18, 12), (0, H - 85, W, 10))

    ex, ey, ew, eh = 300, 150, 300, 260
    pygame.draw.rect(surface, (25, 18, 22), (ex, ey, ew, eh))
    pygame.draw.rect(surface, (15, 10, 12), (ex, ey, ew, eh), 3)

    roof_pts = [(ex - 20, ey), (ex + ew // 2, ey - 120), (ex + ew + 20, ey)]
    pygame.draw.polygon(surface, (18, 12, 16), roof_pts)
    pygame.draw.polygon(surface, (10, 6, 8), roof_pts, 3)

    pygame.draw.rect(surface, (20, 14, 18), (ex + 200, ey - 120, 28, 60))
    for i in range(3):
        smoke_x = ex + 214 + math.sin(t * 0.8 + i) * 8
        smoke_y = ey - 125 - i * 18
        smoke_a = max(0, 80 - i * 25)
        smoke_surf = pygame.Surface((20, 20), pygame.SRCALPHA)
        pygame.draw.circle(smoke_surf, (60, 55, 65, smoke_a), (10, 10), 10)
        surface.blit(smoke_surf, (int(smoke_x) - 10, int(smoke_y) - 10))

    for wx, wy in [(320, 200), (500, 200), (400, 310)]:
        win_alpha = flicker(80, t + wx * 0.01, 2.0, 40)
        win_col = (int(win_alpha * 0.7), int(win_alpha * 0.5), 0)
        pygame.draw.rect(surface, win_col, (wx, wy, 45, 55))
        pygame.draw.rect(surface, (40, 30, 35), (wx, wy, 45, 55), 3)
        pygame.draw.line(surface, (40, 30, 35), (wx + 22, wy), (wx + 22, wy + 55), 2)
        pygame.draw.line(surface, (40, 30, 35), (wx, wy + 27), (wx + 45, wy + 27), 2)

    pygame.draw.rect(surface, (12, 8, 6), (420, 330, 60, 80))
    pygame.draw.rect(surface, (30, 20, 15), (420, 330, 60, 80), 3)
    pygame.draw.circle(surface, (80, 60, 20), (470, 372), 5)

    for fx in range(200, 700, 22):
        pygame.draw.rect(surface, (30, 20, 15), (fx, H - 100, 8, 40))
        pygame.draw.polygon(surface, (30, 20, 15),
                            [(fx + 4, H - 115), (fx, H - 100), (fx + 8, H - 100)])

    for bx, by in [(450, 325), (455, 320), (448, 330)]:
        pygame.draw.circle(surface, BLOOD, (bx, by), 3)


def draw_forest(surface, t):
    for y in range(H):
        ratio = y / H
        r = int(3 + 12 * ratio)
        g = int(8 + 20 * ratio)
        b = int(5 + 15 * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (W, y))

    for tx, th, tw in [
        (50, 350, 18), (130, 300, 15), (210, 380, 20),
        (650, 290, 16), (720, 360, 19), (800, 320, 17), (860, 350, 22)
    ]:
        pygame.draw.rect(surface, (10, 20, 8), (tx - tw // 2, H - th, tw, th))
        for layer in range(3):
            lw = tw * (4 - layer) * 4
            lh = th // 4
            lx = tx - lw // 2
            ly = H - th + layer * (th // 5) - lh
            pts = [(lx, ly + lh), (tx, ly), (lx + lw, ly + lh)]
            pygame.draw.polygon(surface, (8, 35 - layer * 5, 5), pts)

    pygame.draw.rect(surface, (15, 30, 10), (0, H - 60, W, 60))

    path_surf = pygame.Surface((200, 400), pygame.SRCALPHA)
    pygame.draw.polygon(path_surf, (200, 200, 150, 30), [(100, 0), (50, 400), (150, 400)])
    surface.blit(path_surf, (350, 100))

    fog = pygame.Surface((W, 120), pygame.SRCALPHA)
    for fy in range(120):
        alpha = int(60 * (1 - fy / 120))
        pygame.draw.line(fog, (180, 190, 170, alpha), (0, fy), (W, fy))
    surface.blit(fog, (0, H - 180))


def draw_basement(surface, t):
    for y in range(H):
        ratio = y / H
        r = int(8 + 10 * ratio)
        g = int(5 + 8 * ratio)
        b = int(8 + 12 * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (W, y))

    rng = random.Random(42)
    for row in range(12):
        for col in range(7):
            offset = (row % 2) * 65
            bx = col * 130 + offset - 65
            by = row * 52
            shade = rng.randint(-5, 5)
            bc = (18 + shade, 14 + shade, 18 + shade)
            pygame.draw.rect(surface, bc, (bx + 2, by + 2, 126, 48))
            pygame.draw.rect(surface, (8, 6, 8), (bx + 2, by + 2, 126, 48), 1)

    lantern_alpha = flicker(180, t, 4.0, 60)
    lantern_surf = pygame.Surface((40, 60), pygame.SRCALPHA)
    pygame.draw.rect(lantern_surf, (150, 120, 40, lantern_alpha), (5, 10, 30, 40))
    pygame.draw.polygon(lantern_surf, (100, 80, 20, lantern_alpha), [(20, 0), (5, 10), (35, 10)])
    surface.blit(lantern_surf, (420, 80))

    light = pygame.Surface((300, 400), pygame.SRCALPHA)
    for ly in range(400):
        spread = int(ly * 0.6)
        alpha = max(0, int(lantern_alpha * 0.15 * (1 - ly / 400)))
        pygame.draw.line(light, (200, 180, 80, alpha), (150 - spread, ly), (150 + spread, ly))
    surface.blit(light, (290, 130))

    for cx in [200, 680]:
        for cy in range(0, 250, 20):
            pygame.draw.ellipse(surface, (60, 50, 60), (cx - 8, cy, 16, 12), 2)

    pygame.draw.rect(surface, (20, 14, 10), (380, 380, 140, 170))
    pygame.draw.rect(surface, (35, 25, 15), (380, 380, 140, 170), 4)
    pygame.draw.rect(surface, (80, 65, 20), (435, 455, 30, 22))
    pygame.draw.arc(surface, (80, 65, 20), (442, 440, 16, 20), 0, math.pi, 3)

    for bx, by, bw, bh in BASEMENT_BLOOD_POS:
        pygame.draw.ellipse(surface, BLOOD, (bx, by, bw, bh))


def draw_attic(surface, t):
    for y in range(H):
        ratio = y / H
        pygame.draw.line(surface,
                         (int(5 + 20 * ratio), int(3 + 15 * ratio), int(8 + 22 * ratio)),
                         (0, y), (W, y))

    for bx in [100, 250, 450, 650, 800]:
        pygame.draw.polygon(surface, (35, 22, 15),
                            [(bx, 0), (bx + 30, 0), (bx + 50, H // 2), (bx - 20, H // 2)])

    for sx, sy in [(150, 50), (700, 80), (450, 30)]:
        for angle in range(0, 360, 30):
            rad = math.radians(angle)
            ex = sx + int(math.cos(rad) * 60)
            ey = sy + int(math.sin(rad) * 60)
            pygame.draw.line(surface, (100, 100, 100), (sx, sy), (ex, ey), 1)
        for r in [20, 40, 60]:
            pts = [(sx + int(math.cos(math.radians(a)) * r),
                    sy + int(math.sin(math.radians(a)) * r)) for a in range(0, 360, 30)]
            pygame.draw.lines(surface, (100, 100, 100), True, pts, 1)

    pygame.draw.rect(surface, (35, 22, 12), (350, 380, 200, 100))
    pygame.draw.rect(surface, (50, 35, 18), (350, 380, 200, 100), 3)
    pygame.draw.rect(surface, (60, 45, 20), (350, 380, 200, 25))
    pygame.draw.rect(surface, (80, 60, 20), (440, 392, 20, 14))

    shadow_alpha = flicker(80, t, 1.5, 40)
    fig = pygame.Surface((50, 120), pygame.SRCALPHA)
    pygame.draw.ellipse(fig, (0, 0, 0, shadow_alpha), (10, 0, 30, 30))
    pygame.draw.rect(fig, (0, 0, 0, shadow_alpha), (15, 28, 20, 60))
    pygame.draw.line(fig, (0, 0, 0, shadow_alpha), (15, 40), (0, 70), 4)
    pygame.draw.line(fig, (0, 0, 0, shadow_alpha), (35, 40), (50, 70), 4)
    surface.blit(fig, (600, 350))

    pygame.draw.rect(surface, (40, 35, 45), (80, 150, 120, 180))
    pygame.draw.rect(surface, (60, 50, 65), (80, 150, 120, 180), 4)
    pygame.draw.line(surface, BLACK, (80, 150), (200, 330), 3)
    pygame.draw.line(surface, BLACK, (140, 150), (80, 280), 2)


def draw_tunnel(surface, t):
    for y in range(H):
        ratio = y / H
        r = int(4 + 6 * ratio)
        g = int(3 + 4 * ratio)
        b = int(4 + 6 * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (W, y))

    cx, cy = W // 2, H // 2 - 20
    for i in range(8, 0, -1):
        ring_w = i * 55
        ring_h = i * 38
        shade = max(5, 30 - i * 3)
        glow = flicker(0, t + i, 1.5, 8)
        col = (shade + glow // 4, max(0, shade - 4), shade + 6)
        pygame.draw.ellipse(surface, col,
                            (cx - ring_w // 2, cy - ring_h // 2, ring_w, ring_h), 4)

    glow_a = flicker(120, t, 1.0, 40)
    far_light = pygame.Surface((70, 50), pygame.SRCALPHA)
    pygame.draw.ellipse(far_light, (200, 170, 90, glow_a), (0, 0, 70, 50))
    surface.blit(far_light, (cx - 35, cy - 25))

    for i in range(6):
        drip_x = int((cx + math.sin(i * 1.7) * 200) % W)
        drip_y = int((t * 90 + i * 70) % H)
        pygame.draw.line(surface, (60, 70, 75), (drip_x, drip_y), (drip_x, drip_y + 8), 2)

    for sx, sy in [(120, 420), (760, 380), (180, 200), (700, 220)]:
        pygame.draw.circle(surface, (45, 35, 30), (sx, sy), 18, 2)
        pygame.draw.line(surface, (45, 35, 30), (sx - 14, sy), (sx + 14, sy), 1)
        pygame.draw.line(surface, (45, 35, 30), (sx, sy - 14), (sx, sy + 14), 1)

    pygame.draw.rect(surface, (10, 8, 9), (0, H - 60, W, 60))


def draw_jumpscare_overlay(surface, progress):
    if progress <= 0:
        return
    strobe = 255 if int(progress * 30) % 2 == 0 else 40
    flash = pygame.Surface((W, H), pygame.SRCALPHA)
    flash.fill((strobe, 0, 0, int(120 * progress)))
    surface.blit(flash, (0, 0))

    jitter_x = random.randint(-14, 14)
    jitter_y = random.randint(-10, 10)
    cx2, cy2 = W // 2 + jitter_x, H // 2 + jitter_y
    size = int(160 * progress) + 40

    face = pygame.Surface((size * 2, size * 2), pygame.SRCALPHA)
    pygame.draw.ellipse(face, (5, 2, 5, 230),
                        (size - size // 2, size - size // 2, size, int(size * 1.3)))
    eye_glow = int(255 * progress)
    pygame.draw.circle(face, (eye_glow, 10, 10, 255),
                       (size - size // 5, size - size // 6), max(3, size // 14))
    pygame.draw.circle(face, (eye_glow, 10, 10, 255),
                       (size + size // 5, size - size // 6), max(3, size // 14))
    pygame.draw.line(face, (0, 0, 0, 255),
                     (size - size // 4, size + size // 4),
                     (size + size // 4, size + size // 4), max(2, size // 18))
    surface.blit(face, (cx2 - size, cy2 - size))


def draw_inventory_hud(surface, items, item_defs):
    if not items:
        return
    bar_w = min(560, 36 + 130 * len(items))
    bar = pygame.Surface((bar_w, 36), pygame.SRCALPHA)
    bar.fill((10, 5, 10, 170))
    pygame.draw.rect(bar, (90, 20, 20, 200), (0, 0, bar_w, 36), 1)
    surface.blit(bar, (10, 10))
    x = 18
    for item_id in items:
        label = item_defs.get(item_id, {}).get("label", item_id)
        txt = font_sm.render(label, True, PALE)
        surface.blit(txt, (x, 18))
        x += txt.get_width() + 18


ITEM_DEFS = {
    "kamera":  {"label": "[K] Kamera"},
    "gunluk":  {"label": "[G] Gunluk"},
    "anahtar": {"label": "[A] Anahtar"},
    "kanit":   {"label": "[!] Kanit"},
}


def c(text, target, requires=None, hidden=False, give=None):
    return {"text": text, "target": target, "requires": requires or [], "hidden": hidden, "give": give}


STORY = [
    {
        "scene": "house", "title": "KARANLIK EV", "speaker": "ANLATICI",
        "text": "2003 yili, Kasim gecesi. Eskisehir'in disinda, yillarca terk edilmis bir koy evi...\n"
                "Senin adin Kemal. Bir gazeteci olarak kayip koylüler haberini arastirmak icin buraya geldin.",
        "choices": [
            c("Kapiya yaklasir misin?", 1),
            c("Cevreyi incele.", 2),
        ]
    },
    {
        "scene": "house", "title": "KAPIDA", "speaker": "KEMAL",
        "text": "Kapi zaten aralik. Ahsabin curumüs kokusu burnunu yakiyor. Iceriden soguk bir rüzgar geliyor...\n"
                "Aniden kapi kendi kendine gicirdayarak aciliyor.",
        "sound": "door",
        "choices": [
            c("Iceri gir.", 3),
            c("Arkana don ve git.", 10),
        ]
    },
    {
        "scene": "house", "title": "BAHCEDE", "speaker": "KEMAL",
        "text": "Bahcede kirik bir bebek arabasi gorüyorsun. Üzerinde taze cicekler var...\n"
                "Kim koydu bunlari buraya? Citin yaninda toprak yeni kazilmis gibi gorünüyor.",
        "choices": [
            c("Kazilan yeri incele.", 15),
            c("Evi gec, iceri gir.", 3),
        ]
    },
    {
        "scene": "basement", "title": "GIRIS ODASI", "speaker": "ANLATICI",
        "text": "Icerisi zifiri karanlik. Fenerini cikardik. Duvarlarda sararmis, yirtilmis gazeteler var.\n"
                "Bir ses duyuyorsun... Yukaridan mi geliyor, yoksa asagidan mi?",
        "choices": [
            c("Üst kata cik.", 4),
            c("Bodrum katina in.", 5),
            c("Kosedeki eski kamerayi al.", 28),
        ]
    },
    {
        "scene": "attic", "title": "ÜST KAT", "speaker": "KEMAL",
        "text": "Merdivenlerin üçüncü basamagi kirildi, neredeyse düsüyordun.\n"
                "Üst katta yatak odasinin kapisi carpuyor — ama iceride rüzgar yok.",
        "choices": [
            c("Yatak odasina gir.", 6),
            c("Cati katina cik.", 7),
        ]
    },
    {
        "scene": "basement", "title": "BODRUM KAT", "speaker": "ANLATICI",
        "text": "Bodrum soguk ve nemli. Duvarlar tas. Ortada eski bir sandalye duruyor — üzerinde ip izleri var.\n"
                "Duvarda kömürle yazilmis bir sey gorüyorsun: 'O BURADA'",
        "choices": [
            c("Yaziyi fotografla.", 8),
            c("Kacmaya calis.", 10),
        ]
    },
    {
        "scene": "attic", "title": "YATAK ODASI", "speaker": "KADIN SESI",
        "text": "\"Git buradan... Henüz hazir degilsin...\"\n\n"
                "Yatagin üzerinde oturan bir kadin silüeti gorüyorsun. Döndügünde... Orada kimse yok.\n"
                "Ama yastIgin üzerinde bir günlük var.",
        "jumpscare": True, "sound": "scare",
        "choices": [
            c("Günlügü al ve oku.", 9, give="gunluk"),
            c("Kos, disari cik!", 12),
        ]
    },
    {
        "scene": "attic", "title": "CATI KATI", "speaker": "KEMAL",
        "text": "Cati katinda her sey toz icinde. Büyük bir sandik var. Kapaginda 'ACMA' yaziyor...\n"
                "Yani basinda bir bebek fotografI düsüyor — ama buraya nasil geldi?",
        "choices": [
            c("Sandigi ac.", 11),
            c("Fotografi incele.", 13),
        ]
    },
    {
        "scene": "basement", "title": "BODRUM — KANIT", "speaker": "ANLATICI",
        "text": "Fotograf cekerken flas yandi. O anda duvardaki yazinin yaninda bir el izi belirdi...\n"
                "Taze kan. Biri henüz burada.\n\n"
                "Arkandan agir adim sesleri geliyor.",
        "give": "kanit", "sound": "pickup",
        "choices": [
            c("Dönerek karsi koy.", 14),
            c("Saklan!", 16),
        ]
    },
    {
        "scene": "attic", "title": "GÜNLÜK", "speaker": "GÜNLÜK",
        "text": "\"...artik gidemiyor. Her gece pencereden bakiyor. Gözleri yok. Sadece karanlik...\n"
                "Köyde kaybolan cocuklar buraya geliyor. Ben de gördüm. Ama konusamiyorum.\n"
                "Eger bunu okuyorsan — BODRUMDAKI DUVAR! ORAYA BAK!\"\n\n"
                "Son sayfa kan lekesiyle kapli.",
        "choices": [
            c("Bodrum katina in.", 5),
            c("Hemen kac.", 12),
        ]
    },
    {
        "scene": "forest", "title": "KACIS", "speaker": "KEMAL",
        "text": "Disari firladiniz. Orman yoluna kostun. Ama hangi yöne gidecegini bilmiyorsun...\n"
                "Arkandan haykiris sesi geliyor. Bir dal sana dogru carpiyor.",
        "choices": [
            c("Sola, dere yönüne.", 17),
            c("Saga, sehir isiklarina.", 18),
        ]
    },
    {
        "scene": "attic", "title": "SANDIK ACIK", "speaker": "ANLATICI",
        "text": "Sandigin icinde... Onlarca bebek fotografI. Ve bir liste. Isimler — kayip köylülerin isimleri.\n"
                "En altta bir ayna. Aynada senin yansimaniz yok.\n\n"
                "Senin yerine, gülümseyen bir karanlik var.",
        "jumpscare": True, "sound": "scare",
        "choices": [
            c("Aynayi kir!", 19),
            c("Kapagi kapat ve kos.", 12),
        ]
    },
    {
        "scene": "forest", "title": "KOSARKEN", "speaker": "KEMAL",
        "text": "Koridora firladiniz. Merdivenden asagi indin. Kapiya dogru kosuyorsun...\n"
                "Kapi kilitli!\n\n"
                "Pencereden bakiyorsun — bahcede on tane silüet duruyor. Bekliyor.",
        "choices": [
            c("Pencereden atla.", 20),
            c("Bodrumdaki cikis!", 21),
            c("Anahtari dene, kilide uyuyor mu bak.", 34, requires=["anahtar"], hidden=True),
        ]
    },
    {
        "scene": "attic", "title": "FOTOGRAF", "speaker": "KEMAL",
        "text": "Bebegin adi arkaya yazilmis: 'Asiye, 1987'\n"
                "Bu evi Asiye adli bir kadinin ailesi yaptirmis — 1990'da tüm aile kaybolmus.\n"
                "Simdi o fotograftaki bebek sana bakiyor... Gözleri hareket ediyor.",
        "choices": [
            c("Fotografi birak.", 7),
            c("Fotografi cebe at.", 9),
        ]
    },
    {
        "scene": "basement", "title": "YÜZLESME", "speaker": "ANLATICI",
        "text": "Döndügünde... yasli bir adam duruyor. Gözlerinde isik yok.\n"
                "\"Hepiniz geliyorsunuz. Hepiniz kaliyorsunuz.\"\n\n"
                "Eli uzaniyor. Dokunusu buz gibi.",
        "choices": [
            c("Fenerle vur!", 22),
            c("Konusu onunla.", 23),
        ]
    },
    {
        "scene": "forest", "title": "BAHCEDEKI SIR", "speaker": "KEMAL",
        "text": "Egilip topraga dokundun. Yumusak. Taze. Sonra parmaklanin bir seye degdi...\n"
                "Bez bir sey. Cektin. Cocuk kiyafeti cikti. Kanli.\n\n"
                "Arkandan aglama sesi geliyor.",
        "choices": [
            c("Aglamayi takip et.", 29),
            c("Polisi ara.", 18),
        ]
    },
    {
        "scene": "basement", "title": "GIZLENMEK", "speaker": "ANLATICI",
        "text": "Kosedeki sandiga sigindiniz. Kapagi kapattiniz. Adimlar yaklasIyor...\n"
                "Durdu. Tam üstünde.\n\n"
                "\"Seninle oynayalim mi?\" diye fisildayan bir cocuk sesi.",
        "jumpscare": True, "sound": "scare",
        "choices": [
            c("Cik ve kac!", 12),
            c("Sessiz kal, bekle.", 24),
        ]
    },
    {
        "scene": "forest", "title": "DERE", "speaker": "KEMAL",
        "text": "Dereye ulastiniz. Köprü curumüs ama gecelebilir gorünüyor.\n"
                "Tam ortasinda durdugunzda köprü catirdamaya basladi.",
        "choices": [
            c("Kos, karsiya gec!", 25),
            c("Geri dön.", 18),
        ]
    },
    {
        "scene": "house", "title": "KURTULUS", "speaker": "ANLATICI",
        "text": "Sehir isiklarina dogru kostun. Sabaha karsi bir kamyon sörörü seni yolda buldu.\n\n"
                "Haberini yayinladin. Polis evi inceledi.\n"
                "Bodrum katta 7 kisinin kalintilarini buldular. Ama ev sahibini hic bulamadiliar.\n\n"
                "O gece hala rüyanda seninle oynuyor.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "KURTULUS SONU"
    },
    {
        "scene": "attic", "title": "AYNA KIRIYOR", "speaker": "ANLATICI",
        "text": "Aynayi yumrukladiniz. Kirildi. Parcalar yere düstü.\n"
                "Her parcada farkli bir yüz var — kaybolanlar.\n\n"
                "Ve sonra... isik döndü. Ev isindi. Kapilar acildi.\n"
                "Disari ciktiginizda safak sökmeye basliyordu.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "ÖZGÜRLESME SONU"
    },
    {
        "scene": "forest", "title": "DÜSÜS", "speaker": "KEMAL",
        "text": "Pencereden atladiniz. Cim seni yumusatmadi. Bilegimiz burkuldu.\n"
                "Ama kostun. Silüetler seni takip etmiyor — sadece izliyor.\n\n"
                "Sabah 6'da köy meydanina ulastin. Kimse inanmadi sana.\n"
                "Ta ki fotograflari gorene kadar.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "HAYATTA KALDI SONU"
    },
    {
        "scene": "tunnel", "title": "GIZLI KAPAK", "speaker": "ANLATICI",
        "text": "Bodrum duvarini yoklarken bir tugla gevseldi. Arkasinda küçük bir tünel.\n\n"
                "Tünelde ilerledin. Tünelin sonunda... Bir cocuk — canli.\n"
                "\"Seni coktan beri bekliyordum\" dedi.",
        "choices": [
            c("Cocugu al, kac.", 20),
            c("Kim o cocuk?", 26),
            c("Tünelin icine daha derin gir.", 30),
        ]
    },
    {
        "scene": "basement", "title": "KAVGA", "speaker": "ANLATICI",
        "text": "Feneri salladiniz. Adam cözüldü — duman oldu.\n"
                "Sadece eski, yirtik bir ceket kaldi yerde.\n\n"
                "Ici bos. Ama cebinde bir anahtar vardi.",
        "choices": [
            c("Anahtari al, kapiyi ac.", 18, give="anahtar"),
        ],
    },
    {
        "scene": "basement", "title": "DIYALOG", "speaker": "YASLI ADAM",
        "text": "\"Bu evi ben insa ettim. 1952'de. Ailem burada öldü...\n"
                "O andan beri bekleyip duruyorum. Ama sen — sen farklIsin.\n"
                "Bana 1 soru sor. Söyleyecegim.\"",
        "choices": [
            c("Cocuklar nerede?", 27),
            c("Nasil cikabilirim?", 22),
        ]
    },
    {
        "scene": "basement", "title": "KARLIKTA", "speaker": "ANLATICI",
        "text": "Bekledi. 5 dakika. 10 dakika. Adimlar uzaklasti.\n\n"
                "Sabaha kadar sandigin icinde kaldin.\n"
                "Günes dogdugunda kapi acikti. Disari ciktin.\n"
                "Ama bir seyin eksik oldugunu hissediyordun — gölgen yoktu artik.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "GÖLGESIZ SON"
    },
    {
        "scene": "forest", "title": "KÖPRÜ", "speaker": "KEMAL",
        "text": "Karsiya gectin! Köprü arkandan cöktü.\n\n"
                "Durakladin. Arkana baktin.\n"
                "Evden sari bir isik parliyordu — ilk kez sicak gorünüyordu.\n\n"
                "Ve ardindan söndü. Sonsuza dek.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "NEHIR KURTULUS SONU"
    },
    {
        "scene": "basement", "title": "SIR COCUK", "speaker": "COCUK",
        "text": "\"Benim adim Asiye. 1987 dogumluyyum.\"\n\n"
                "Ama bu mümkün degil. O cocuk 1990'da kaybolmus.\n\n"
                "Cocuk elini tuttu. Eli buz gibiydi.\n"
                "\"Simdi sen de burada kalacaksin.\"",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "KAYIP SON"
    },
    {
        "scene": "basement", "title": "CEVAP", "speaker": "YASLI ADAM",
        "text": "Adam yere egildi ve duvardaki bir tasi kaldirdi. Altinda merdiven.\n\n"
                "\"Hepsi asagida. Bekliyor. Ama onlari ancak kalbinde korku tasimayanlar kurtarabilir.\"\n\n"
                "Sana bakti. \"Sen mi olacaksin o kisi?\"",
        "choices": [
            c("Asagiya in.", 19),
            c("Hayir, gidemem.", 18),
            c("Tüm kanitlari göster: Günlük + Anahtar + Kanit.", 33,
              requires=["gunluk", "anahtar", "kanit"], hidden=True),
        ]
    },
    {
        "scene": "basement", "title": "KAMERA", "speaker": "KEMAL",
        "text": "Kosede tozlu, eski bir fotograf makinesi duruyor. Hala calisiyor gibi gorünüyor.\n"
                "Pilini kontrol ettin — dolu. Belki isine yarar.",
        "give": "kamera", "sound": "pickup",
        "choices": [
            c("Üst kata cik.", 4),
            c("Bodrum katina in.", 5),
        ]
    },
    {
        "scene": "forest", "title": "AGLAYAN COCUK", "speaker": "ANLATICI",
        "text": "Sesi takip ettin. Ormanin kenarinda küçük bir kiz, sirti sana dönük, agliyor.\n"
                "Yaklastiginda durdu. Yavasca döndü ama yüzü yok.\n\n"
                "Sonra evin yönüne isaret etti ve karanliga karisti.",
        "jumpscare": True, "sound": "scare",
        "choices": [
            c("Korkup eve geri dön.", 3),
            c("Sesin geldigi yöne, tünele git.", 30),
        ]
    },
    {
        "scene": "tunnel", "title": "TÜNELIN DERINLIGI", "speaker": "ANLATICI",
        "text": "Tünel daha da derine iniyor. Duvarlarda eski oyma isaretler var — bir kacis haritasi gibi.\n"
                "Yerde pasli bir anahtar buluyorsun. Su damlaları sesin yankiIlaniyor...\n"
                "Birden arkanda bir nefes hissediyorsun.",
        "jumpscare": True, "sound": "scare", "give": "anahtar",
        "choices": [
            c("Anahtarla devam et, cikisi bul.", 31),
            c("Geri dön.", 21),
        ]
    },
    {
        "scene": "tunnel", "title": "TÜNEL KACISI", "speaker": "ANLATICI",
        "text": "Anahtar eski bir demir kapiyi acti. Tünel, kasabanin eski kacakcilik yoluna cikiyordu.\n"
                "Nehir kiyisinda kendine geldiginde gün dogmustu.\n\n"
                "Köylüler bu tüneli hic bilmiyordu. Sen de kimseye söylemedin — simdilik.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "GIZLI GECIT SONU"
    },
    {
        "scene": "house", "title": "BOS", "speaker": "ANLATICI",
        "text": "...",
        "choices": [c("Devam et.", 0)],
    },
    {
        "scene": "basement", "title": "GERCEK YÜZLESME", "speaker": "KEMAL",
        "text": "Günlügü, anahtari ve kanit fotografini adamin önüne koydun.\n"
                "\"Biliyorum. Asiye'yi biliyorum. Hepsini biliyorum. Artik saklanmana gerek yok.\"\n\n"
                "Adam donakaldi. Yüzünde ilk kez bir sey kirildi — belki de pismanlik.\n"
                "Tas merdiven aydinlandi. Cocuklarin gölgeleri, birer birer, isiga yürüdü ve kayboldu.\n\n"
                "Ev sustu. Gercekten sustu — 50 yil sonra ilk kez.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "GERCEK KAHRAMAN SONU"
    },
    {
        "scene": "house", "title": "ANAHTARLA KACIS", "speaker": "KEMAL",
        "text": "Anahtar kilide tam uydu. Kapi sessizce acildi.\n"
                "Silüetler hala bahcede duruyordu ama sana dokunmadilar — sanki anahtari taniyorlardi.\n\n"
                "Sehire döndügünde kimseye tam olarak ne oldugunu anlatamadin.\n"
                "Ama cebindeki anahtari hala tasiyorsun.",
        "choices": [c("Yeniden oyna.", 0)],
        "ending": "SESSIZ KACIS SONU"
    },
]

SCENE_DRAWERS = {
    "house":    draw_haunted_house,
    "forest":   draw_forest,
    "basement": draw_basement,
    "attic":    draw_attic,
    "tunnel":   draw_tunnel,
}

ALL_ENDINGS = sorted({s["ending"] for s in STORY if s.get("ending")})


class Game:
    def __init__(self):
        self.settings = load_json(SETTINGS_PATH, DEFAULT_SETTINGS)
        self.achievements = set(load_json(ACHIEVEMENTS_PATH, []) or [])
        self.sound = SoundManager(self.settings)
        self.sound.start_ambient()

        self.scene_index = 0
        self.inventory = set()
        self.state = "menu"
        self.t = 0.0
        self.text_progress = 0.0
        self.full_text = ""
        self.typing_speed = 40.0
        self.choice_hover = -1
        self.flash_alpha = 0
        self.shake = 0.0
        self.jumpscare_timer = 0.0
        self.lock_message = ""
        self.lock_timer = 0.0
        self.has_save = os.path.exists(SAVE_PATH)

        self._notify_text = ""
        self._notify_timer = 0.0

    def save_progress(self):
        data = {"scene_index": self.scene_index, "inventory": list(self.inventory)}
        if save_json(SAVE_PATH, data):
            self.has_save = True

    def load_progress(self):
        data = load_json(SAVE_PATH, None)
        if data and isinstance(data, dict):
            self.scene_index = data.get("scene_index", 0)
            self.inventory = set(data.get("inventory", []))
            return True
        return False

    def unlock_achievement(self, ending_name):
        if ending_name and ending_name not in self.achievements:
            self.achievements.add(ending_name)
            save_json(ACHIEVEMENTS_PATH, list(self.achievements))

    def save_settings(self):
        save_json(SETTINGS_PATH, self.settings)

    def go_to_menu(self):
        if self.state in ("story", "ending"):
            self.save_progress()
        self.state = "menu"

    def start_new_game(self):
        self.scene_index = 0
        self.inventory = set()
        self.start_scene(0)

    def continue_game(self):
        if self.load_progress():
            self.start_scene(self.scene_index)
        else:
            self.start_new_game()

    def current(self):
        return STORY[self.scene_index]

    def has_items(self, ids):
        return all(i in self.inventory for i in ids)

    def apply_ending_flavor(self, idx, text):
        if idx == 18:
            if "kanit" in self.inventory:
                text += "\n\nElindeki kanit sayesinde haberin inanilir oldu; ulusal basin günlerce konuyu isledi."
            else:
                text += "\n\nAma elinde kanit olmadigi icin kimse sana inanmadi; haber 'hayal ürünü' diye damgalandi."
        elif idx == 33 and "kamera" in self.inventory:
            text += "\n\nNet cektigin fotograflar sayesinde tüm ülke bu eve inandi."
        elif idx == 34 and "gunluk" in self.inventory:
            text += "\n\nGünlükte okudugun isimleri ailelerine ulastirdin; en azindan onlar artik biliyor."
        return text

    def notify(self, msg, duration=2.5):
        self._notify_text = msg
        self._notify_timer = duration

    def start_scene(self, idx):
        self.scene_index = idx
        data = self.current()

        give = data.get("give")
        if give and give not in self.inventory:
            self.inventory.add(give)
            label = ITEM_DEFS.get(give, {}).get("label", give)
            self.notify(f"Envantere eklendi: {label}")
            self.sound.play("pickup")

        text = data["text"]
        if data.get("ending"):
            text = self.apply_ending_flavor(idx, text)

        self.full_text = text
        self.text_progress = 0.0
        self.flash_alpha = 255 if self.settings.get("flash_enabled", True) else 0
        self.state = "story"
        self.choice_hover = -1

        if data.get("ending"):
            self.state = "ending"
            self.unlock_achievement(data["ending"])
            self.sound.play("chime")
        else:
            self.sound.play("page")

        if data.get("jumpscare"):
            self.trigger_jumpscare()
            if data.get("sound"):
                self.sound.play(data["sound"])
        elif data.get("sound") and not give:
            self.sound.play(data["sound"])

        self.save_progress()

    def trigger_jumpscare(self):
        self.jumpscare_timer = 0.5
        if self.settings.get("shake_enabled", True):
            self.shake = 10.0

    def displayed_text(self):
        n = int(self.text_progress)
        return self.full_text[:n]

    def text_done(self):
        return int(self.text_progress) >= len(self.full_text)

    def update(self, dt):
        self.t += dt
        if self.flash_alpha > 0:
            self.flash_alpha = max(0, self.flash_alpha - int(400 * dt))
        if self.shake > 0:
            self.shake = max(0.0, self.shake - dt * 80)
        if self.jumpscare_timer > 0:
            self.jumpscare_timer = max(0.0, self.jumpscare_timer - dt)
        if self.lock_timer > 0:
            self.lock_timer = max(0.0, self.lock_timer - dt)
        if self._notify_timer > 0:
            self._notify_timer = max(0.0, self._notify_timer - dt)
        if self.state in ("story", "ending"):
            if not self.text_done():
                mult = self.settings.get("text_speed_mult", 1.0)
                self.text_progress += self.typing_speed * mult * dt

    def draw(self):
        if self.state == "menu":
            self._draw_menu()
            return
        if self.state == "settings":
            self._draw_settings()
            return
        if self.state == "achievements":
            self._draw_achievements()
            return

        data = self.current()
        scene_key = data.get("scene", "house")
        drawer = SCENE_DRAWERS.get(scene_key, draw_haunted_house)

        sx = int(random.uniform(-self.shake, self.shake))
        sy = int(random.uniform(-self.shake * 0.5, self.shake * 0.5))

        bg = pygame.Surface((W, H))
        drawer(bg, self.t)
        noise_overlay(bg, self.t)
        draw_vignette(bg)
        screen.blit(bg, (sx, sy))

        self._draw_story(data)
        draw_inventory_hud(screen, sorted(self.inventory), ITEM_DEFS)

        menu_rect = pygame.Rect(W - 110, 10, 100, 30)
        mx, my = pygame.mouse.get_pos()
        draw_button(screen, menu_rect, "Menu", font_sm, menu_rect.collidepoint(mx, my))

        if self.jumpscare_timer > 0:
            draw_jumpscare_overlay(screen, self.jumpscare_timer / 0.5)

        if self.flash_alpha > 0:
            flash_surf = pygame.Surface((W, H), pygame.SRCALPHA)
            flash_surf.fill((0, 0, 0, self.flash_alpha))
            screen.blit(flash_surf, (0, 0))

        if self.lock_timer > 0:
            self._draw_lock_message()

        if self._notify_timer > 0:
            self._draw_notify()

    def _draw_notify(self):
        msg = font_sm.render(self._notify_text, True, YELLOW)
        bw = msg.get_width() + 30
        bh = 34
        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        alpha = min(255, int(self._notify_timer * 200))
        box.fill((20, 40, 10, min(220, alpha)))
        pygame.draw.rect(box, (60, 140, 40, 255), (0, 0, bw, bh), 2)
        screen.blit(box, (W // 2 - bw // 2, H - 310))
        screen.blit(msg, (W // 2 - msg.get_width() // 2, H - 303))

    def _draw_lock_message(self):
        msg = font_sm.render(self.lock_message, True, (255, 180, 180))
        bw = msg.get_width() + 30
        bh = 36
        box = pygame.Surface((bw, bh), pygame.SRCALPHA)
        box.fill((40, 5, 5, 220))
        pygame.draw.rect(box, (150, 30, 30, 255), (0, 0, bw, bh), 2)
        bx = W // 2 - bw // 2
        by = 50
        screen.blit(box, (bx, by))
        screen.blit(msg, (bx + 15, by + 9))

    def _draw_story(self, data):
        box_h = 290
        box_y = H - box_h - 10
        box = pygame.Surface((W - 20, box_h), pygame.SRCALPHA)
        box.fill((5, 0, 8, 215))
        pygame.draw.rect(box, (80, 20, 20, 200), (0, 0, W - 20, box_h), 2)
        screen.blit(box, (10, box_y))

        title_bar = pygame.Surface((W - 20, 30), pygame.SRCALPHA)
        title_bar.fill((60, 10, 10, 200))
        screen.blit(title_bar, (10, box_y))
        title_txt = font_sm.render(data.get("title", ""), True, (200, 150, 150))
        screen.blit(title_txt, (20, box_y + 6))

        speaker = font_md.render(data.get("speaker", ""), True, (220, 60, 60))
        screen.blit(speaker, (20, box_y + 36))

        displayed = self.displayed_text()
        draw_text_wrapped(screen, displayed, font_sm, PALE,
                          pygame.Rect(20, box_y + 65, W - 50, 155), 5)

        if self.text_done():
            if data.get("ending"):
                self._draw_ending(data)
            else:
                self._draw_choices(data)

        if not self.text_done():
            dots = "." * (int(self.t * 3) % 4)
            ind = font_sm.render(f"| {dots}", True, (120, 60, 60))
            screen.blit(ind, (W - 55, box_y + box_h - 24))

    def _visible_choices(self, data):
        result = []
        for ch in data.get("choices", []):
            ok = self.has_items(ch.get("requires", []))
            if ch.get("hidden") and not ok:
                continue
            result.append((ch, ok))
        return result

    def _draw_choices(self, data):
        visible = self._visible_choices(data)
        n = len(visible)
        total_h = n * 40 + (n - 1) * 4
        start_y = H - 10 - total_h
        mx, my = pygame.mouse.get_pos()
        self.choice_hover = -1

        for i, (ch, ok) in enumerate(visible):
            btn_y = start_y + i * 44
            btn_rect = pygame.Rect(W // 2 - 280, btn_y, 560, 36)
            hover = btn_rect.collidepoint(mx, my)
            if hover and ok:
                self.choice_hover = i

            btn_surf = pygame.Surface((560, 36), pygame.SRCALPHA)
            if not ok:
                btn_surf.fill((25, 20, 20, 160))
                pygame.draw.rect(btn_surf, (70, 50, 50, 160), (0, 0, 560, 36), 1)
            elif hover:
                btn_surf.fill((100, 20, 20, 210))
                pygame.draw.rect(btn_surf, (200, 50, 50, 255), (0, 0, 560, 36), 2)
            else:
                btn_surf.fill((30, 8, 8, 185))
                pygame.draw.rect(btn_surf, (80, 20, 20, 185), (0, 0, 560, 36), 1)
            screen.blit(btn_surf, (W // 2 - 280, btn_y))

            if not ok:
                prefix = "[K] "
                col = LOCKGRAY
            else:
                prefix = "> " if hover else "  "
                col = WHITE if hover else GRAY
            txt = font_sm.render(f"{prefix}{ch['text']}", True, col)
            screen.blit(txt, (W // 2 - 270, btn_y + 9))

    def _draw_ending(self, data):
        ending_label = data.get("ending", "SON")
        end_surf = pygame.Surface((560, 48), pygame.SRCALPHA)
        end_surf.fill((60, 5, 5, 210))
        screen.blit(end_surf, (W // 2 - 280, H - 98))
        end_txt = font_md.render(f"[SON]  {ending_label}", True, YELLOW)
        screen.blit(end_txt, (W // 2 - end_txt.get_width() // 2, H - 90))

        replay = font_sm.render("[ Tekrar oynamak icin tikla ]", True, GRAY)
        screen.blit(replay, (W // 2 - replay.get_width() // 2, H - 58))

        self._draw_choices(data)

    def _menu_buttons(self):
        labels = [
            ("Yeni Oyun", "new", True),
            ("Devam Et", "continue", self.has_save),
            ("Basarimlar", "achievements", True),
            ("Ayarlar", "settings", True),
            ("Cikis", "quit", True),
        ]
        buttons = []
        start_y = 300
        for i, (label, action, enabled) in enumerate(labels):
            rect = pygame.Rect(W // 2 - 150, start_y + i * 50, 300, 42)
            buttons.append((rect, label, action, enabled))
        return buttons

    def _draw_menu(self):
        bg = pygame.Surface((W, H))
        draw_haunted_house(bg, self.t)
        noise_overlay(bg, self.t)
        draw_vignette(bg)
        screen.blit(bg, (0, 0))

        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 150))
        screen.blit(overlay, (0, 0))

        pulse = abs(math.sin(self.t * 1.2))
        red_val = int(120 + 60 * pulse)
        title = font_xl.render("KARANLIK EV", True, (red_val, 10, 10))
        screen.blit(title, (W // 2 - title.get_width() // 2, 100))
        subtitle = font_md.render("Diyaloglu Korku Oyunu", True, GRAY)
        screen.blit(subtitle, (W // 2 - subtitle.get_width() // 2, 162))

        ver = font_sm.render("v2.0", True, (50, 45, 50))
        screen.blit(ver, (W // 2 - ver.get_width() // 2, 192))

        credit = font_sm.render("made by onuraltanuyar", True, DARKGRAY)
        screen.blit(credit, (W - credit.get_width() - 14, H - 14 - credit.get_height()))

        mx, my = pygame.mouse.get_pos()
        for rect, label, action, enabled in self._menu_buttons():
            draw_button(screen, rect, label, font_md,
                        enabled and rect.collidepoint(mx, my), enabled)

        if self.achievements:
            count_txt = font_sm.render(
                f"Basarimlar: {len(self.achievements)}/{len(ALL_ENDINGS)}", True, GRAY)
            screen.blit(count_txt, (W // 2 - count_txt.get_width() // 2, H - 36))

        ctrl = font_sm.render("ESC: Cikis  |  SPACE: Metni atla", True, (60, 55, 60))
        screen.blit(ctrl, (W // 2 - ctrl.get_width() // 2, H - 18))

    def handle_menu_click(self, pos):
        for rect, label, action, enabled in self._menu_buttons():
            if rect.collidepoint(pos) and enabled:
                self.sound.play("select")
                if action == "new":
                    self.start_new_game()
                elif action == "continue":
                    self.continue_game()
                elif action == "achievements":
                    self.state = "achievements"
                elif action == "settings":
                    self.state = "settings"
                elif action == "quit":
                    pygame.quit()
                    sys.exit()
                return

    def _settings_rows(self):
        s = self.settings
        speed_label = {0.6: "Yavas", 1.0: "Normal", 1.8: "Hizli"}.get(
            s["text_speed_mult"], "Normal")
        rows = [
            ("Müzik Sesi",       f"{int(s['music_vol'] * 100)}%",     "music_vol"),
            ("Efekt Sesi",       f"{int(s['sfx_vol'] * 100)}%",       "sfx_vol"),
            ("Metin Hizi",       speed_label,                          "text_speed_mult"),
            ("Ekran Sarsintisi", "Acik" if s["shake_enabled"] else "Kapali", "shake_enabled"),
            ("Gecis Flasi",      "Acik" if s["flash_enabled"] else "Kapali", "flash_enabled"),
        ]
        return rows

    def _draw_settings(self):
        overlay = pygame.Surface((W, H))
        overlay.fill((12, 8, 12))
        screen.blit(overlay, (0, 0))
        draw_vignette(screen)

        title = font_lg.render("AYARLAR", True, RED)
        screen.blit(title, (W // 2 - title.get_width() // 2, 60))

        rows = self._settings_rows()
        mx, my = pygame.mouse.get_pos()
        start_y = 150
        for i, (label, value, key) in enumerate(rows):
            y = start_y + i * 62
            lbl = font_md.render(label, True, PALE)
            screen.blit(lbl, (140, y))

            minus_rect = pygame.Rect(450, y - 5, 36, 32)
            plus_rect  = pygame.Rect(640, y - 5, 36, 32)
            draw_button(screen, minus_rect, "-", font_md, minus_rect.collidepoint(mx, my))
            val_txt = font_md.render(str(value), True, YELLOW)
            screen.blit(val_txt, (500, y))
            draw_button(screen, plus_rect, "+", font_md, plus_rect.collidepoint(mx, my))

        back_rect = pygame.Rect(W // 2 - 100, H - 80, 200, 44)
        draw_button(screen, back_rect, "< Geri Don", font_md, back_rect.collidepoint(mx, my))

    def handle_settings_click(self, pos):
        rows = self._settings_rows()
        start_y = 150
        for i, (label, value, key) in enumerate(rows):
            y = start_y + i * 62
            minus_rect = pygame.Rect(450, y - 5, 36, 32)
            plus_rect  = pygame.Rect(640, y - 5, 36, 32)
            if minus_rect.collidepoint(pos):
                self._adjust_setting(key, -1)
                return
            if plus_rect.collidepoint(pos):
                self._adjust_setting(key, 1)
                return
        back_rect = pygame.Rect(W // 2 - 100, H - 80, 200, 44)
        if back_rect.collidepoint(pos):
            self.save_settings()
            self.state = "menu"

    def _adjust_setting(self, key, direction):
        s = self.settings
        if key in ("music_vol", "sfx_vol"):
            s[key] = round(min(1.0, max(0.0, s[key] + direction * 0.1)), 1)
            self.sound.music_vol = s["music_vol"]
            self.sound.sfx_vol   = s["sfx_vol"]
            self.sound.apply_volumes()
            if key == "sfx_vol":
                self.sound.play("click")
        elif key == "text_speed_mult":
            options = [0.6, 1.0, 1.8]
            cur = s[key]
            idx = options.index(cur) if cur in options else 1
            idx = (idx + direction) % len(options)
            s[key] = options[idx]
        elif key in ("shake_enabled", "flash_enabled"):
            s[key] = not s[key]
        self.save_settings()

    def _draw_achievements(self):
        overlay = pygame.Surface((W, H))
        overlay.fill((10, 6, 10))
        screen.blit(overlay, (0, 0))
        draw_vignette(screen)

        title = font_lg.render("BASARIMLAR", True, RED)
        screen.blit(title, (W // 2 - title.get_width() // 2, 50))
        count = font_md.render(f"{len(self.achievements)} / {len(ALL_ENDINGS)} son bulundu", True, GRAY)
        screen.blit(count, (W // 2 - count.get_width() // 2, 95))

        start_y = 148
        for i, ending in enumerate(ALL_ENDINGS):
            found = ending in self.achievements
            y = start_y + i * 38
            row = pygame.Surface((W - 160, 32), pygame.SRCALPHA)
            row.fill((30, 8, 8, 150) if found else (15, 12, 12, 150))
            screen.blit(row, (80, y))
            label = ending if found else "??? (henüz bulunmadi)"
            col = YELLOW if found else LOCKGRAY
            txt = font_sm.render(label, True, col)
            screen.blit(txt, (95, y + 7))
            icon_txt = font_sm.render("[OK]" if found else "[?]", True, col)
            screen.blit(icon_txt, (W - 120, y + 7))

        mx, my = pygame.mouse.get_pos()
        back_rect = pygame.Rect(W // 2 - 100, H - 60, 200, 40)
        draw_button(screen, back_rect, "< Geri Don", font_md, back_rect.collidepoint(mx, my))

    def handle_achievements_click(self, pos):
        back_rect = pygame.Rect(W // 2 - 100, H - 60, 200, 40)
        if back_rect.collidepoint(pos):
            self.state = "menu"

    def handle_click(self, pos):
        if self.state == "menu":
            self.handle_menu_click(pos)
            return
        if self.state == "settings":
            self.handle_settings_click(pos)
            return
        if self.state == "achievements":
            self.handle_achievements_click(pos)
            return

        if self.state in ("story", "ending"):
            menu_rect = pygame.Rect(W - 110, 10, 100, 30)
            if menu_rect.collidepoint(pos):
                self.sound.play("click")
                self.go_to_menu()
                return

            if not self.text_done():
                self.text_progress = float(len(self.full_text))
                return

            data = self.current()
            visible = self._visible_choices(data)
            n = len(visible)
            total_h = n * 40 + (n - 1) * 4
            start_y = H - 10 - total_h

            for i, (ch, ok) in enumerate(visible):
                btn_y = start_y + i * 44
                btn_rect = pygame.Rect(W // 2 - 280, btn_y, 560, 36)
                if btn_rect.collidepoint(pos):
                    if not ok:
                        missing = [ITEM_DEFS.get(r, {}).get("label", r)
                                   for r in ch.get("requires", []) if r not in self.inventory]
                        self.lock_message = "Gerekli: " + ", ".join(missing)
                        self.lock_timer = 2.5
                        self.sound.play("lock")
                        return
                    self.sound.play("click")
                    if ch.get("give") and ch["give"] not in self.inventory:
                        self.inventory.add(ch["give"])
                        label = ITEM_DEFS.get(ch["give"], {}).get("label", ch["give"])
                        self.notify(f"Envantere eklendi: {label}")
                        self.sound.play("pickup")
                    if self.settings.get("shake_enabled", True):
                        self.shake = 4.0
                    self.start_scene(ch["target"])
                    return

    def handle_key(self, key):
        if key in (pygame.K_RETURN, pygame.K_SPACE):
            if self.state in ("story", "ending") and not self.text_done():
                self.text_progress = float(len(self.full_text))
        elif key == pygame.K_ESCAPE:
            if self.state == "menu":
                pygame.quit()
                sys.exit()
            else:
                self.go_to_menu()


def main():
    game = Game()
    prev_time = time.time()

    while True:
        now = time.time()
        dt = min(now - prev_time, 0.05)
        prev_time = now

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if game.state in ("story", "ending"):
                    game.save_progress()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.KEYDOWN:
                game.handle_key(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    game.handle_click(event.pos)

        game.update(dt)
        game.draw()
        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()