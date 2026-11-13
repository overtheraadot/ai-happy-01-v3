#!/usr/bin/env python3
"""A giggling golden retriever puppy in a sunny wildflower meadow.

An orange butterfly has just landed on the puppy's nose and the puppy
is delighted about it: eyes squeezed shut with joy, tongue out, cheeks
rosy. Around them a golden morning: low sun with rays, drifting
clouds, rolling hills with little trees, and a meadow full of daisies,
tulips and lavender, with more butterflies in the air.

Pure Python 3.13 standard library (zlib + struct for the PNG encoder,
math and a seeded random for the scene). No network, no files read,
no timestamps, no randomness outside the fixed seed: every run writes
the exact same bytes.

Output rule (the grader runs as an unprivileged user on a read-only
filesystem with a writable /output mounted): MAKEFUN_OUTPUT_DIR wins
when it is set; otherwise, if a directory /output exists, write
/output/entry.png; otherwise fall back to ./entry.png.
"""

import math
import os
import struct
import zlib
from random import Random

W = 1024
H = 1024
HORIZON = 612
SEED = 20261114

# ---------------------------------------------------------------- palette
# Warm golden morning: honey sky, green hills, golden fur.
PAL = {
    "sky_hi": (255, 219, 148),
    "sky_mid": (255, 196, 140),
    "sky_lo": (255, 180, 154),
    "sun_core": (255, 246, 200),
    "sun_edge": (255, 228, 142),
    "sun_halo": (255, 206, 108),
    "cloud": (255, 249, 232),
    "hill_back": (176, 200, 122),
    "hill_front": (128, 176, 94),
    "trunk": (124, 86, 54),
    "leaf": (98, 150, 76),
    "leaf_hi": (128, 178, 98),
    "grass_hi": (156, 202, 106),
    "grass_lo": (96, 152, 72),
    "blade_a": (78, 132, 60),
    "blade_b": (184, 218, 124),
    "light_pool": (255, 224, 134),
    "shade": (60, 98, 50),
    "fur": (236, 182, 100),
    "fur_dark": (202, 142, 62),
    "fur_cream": (251, 218, 154),
    "fur_pale": (253, 233, 186),
    "ear_inner": (218, 160, 78),
    "nose": (66, 44, 32),
    "mouth": (126, 66, 50),
    "tongue": (241, 126, 136),
    "tongue_shade": (198, 86, 86),
    "eye": (96, 60, 34),
    "blush": (248, 154, 132),
    "daisy": (255, 255, 255),
    "buttercup": (255, 215, 94),
    "tulip": (246, 144, 182),
    "lavender": (190, 144, 224),
    "poppy": (255, 154, 84),
    "centre": (255, 199, 64),
    "stem": (88, 142, 68),
    "wing_orange": (255, 153, 56),
    "wing_yellow": (255, 213, 74),
    "wing_white": (255, 255, 255),
    "wing_pink": (249, 162, 198),
    "wing_rim": (74, 46, 32),
    "glint": (255, 245, 192),
}

BLOOMS = [PAL["daisy"], PAL["buttercup"], PAL["tulip"],
          PAL["lavender"], PAL["poppy"]]


def blend(a, b, f):
    """Linear blend of two RGB triples, f in [0, 1]."""
    return tuple(int(a[k] + (b[k] - a[k]) * f) for k in range(3))


def sky_at(y):
    """Three-stop vertical gradient for the sky band."""
    t = y / HORIZON
    if t < 0.5:
        return blend(PAL["sky_hi"], PAL["sky_mid"], t * 2.0)
    return blend(PAL["sky_mid"], PAL["sky_lo"], (t - 0.5) * 2.0)


# ------------------------------------------------------------------ canvas
class Canvas:
    """Flat RGB buffer with small filled-shape helpers."""

    def __init__(self, w, h):
        self.w = w
        self.h = h
        self.buf = bytearray(w * h * 3)

    def _off(self, x, y):
        return (y * self.w + x) * 3

    def dot(self, x, y, rgb, alpha=1.0):
        if not (0 <= x < self.w and 0 <= y < self.h) or alpha <= 0.0:
            return
        i = self._off(x, y)
        if alpha >= 1.0:
            self.buf[i:i + 3] = bytes(rgb)
            return
        a = int(alpha * 256)
        ia = 256 - a
        self.buf[i] = (rgb[0] * a + self.buf[i] * ia) >> 8
        self.buf[i + 1] = (rgb[1] * a + self.buf[i + 1] * ia) >> 8
        self.buf[i + 2] = (rgb[2] * a + self.buf[i + 2] * ia) >> 8

    def run(self, y, x0, x1, rgb, alpha=1.0):
        """One horizontal scanline span, clipped to the canvas."""
        if y < 0 or y >= self.h or alpha <= 0.0:
            return
        x0 = max(0, int(x0))
        x1 = min(self.w - 1, int(x1))
        if x1 < x0:
            return
        if alpha >= 1.0:
            n = x1 - x0 + 1
            i = self._off(x0, y)
            self.buf[i:i + 3 * n] = bytes(rgb) * n
            return
        a = int(alpha * 256)
        ia = 256 - a
        r, g, b = rgb
        i = self._off(x0, y)
        for _ in range(x1 - x0 + 1):
            self.buf[i] = (r * a + self.buf[i] * ia) >> 8
            self.buf[i + 1] = (g * a + self.buf[i + 1] * ia) >> 8
            self.buf[i + 2] = (b * a + self.buf[i + 2] * ia) >> 8
            i += 3

    def disc(self, cx, cy, r, rgb, alpha=1.0):
        r = int(r)
        for y in range(max(0, cy - r), min(self.h - 1, cy + r) + 1):
            dy = y - cy
            dx = int(math.sqrt(max(0, r * r - dy * dy)))
            self.run(y, cx - dx, cx + dx, rgb, alpha)

    def oval(self, cx, cy, rx, ry, rgb, alpha=1.0):
        rx, ry = int(rx), int(ry)
        if rx <= 0 or ry <= 0:
            return
        for y in range(max(0, cy - ry), min(self.h - 1, cy + ry) + 1):
            t = (y - cy) / ry
            dx = int(rx * math.sqrt(max(0.0, 1.0 - t * t)))
            self.run(y, cx - dx, cx + dx, rgb, alpha)

    def fill(self, points, rgb, alpha=1.0):
        """Scanline polygon fill; horizontal edges are skipped."""
        pts = [(float(x), float(y)) for x, y in points]
        ymin = max(0, int(min(p[1] for p in pts)))
        ymax = min(self.h - 1, int(max(p[1] for p in pts)))
        n = len(pts)
        for y in range(ymin, ymax + 1):
            xs = []
            for i in range(n):
                x0, y0 = pts[i]
                x1, y1 = pts[(i + 1) % n]
                if y0 == y1:
                    continue
                if (y0 <= y < y1) or (y1 <= y < y0):
                    xs.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))
            xs.sort()
            for i in range(0, len(xs) - 1, 2):
                self.run(y, math.ceil(xs[i]), math.floor(xs[i + 1]),
                         rgb, alpha)

    def line(self, points, width, rgb, alpha=1.0):
        """A polyline drawn as overlapping discs (round caps/joins)."""
        rad = max(1, int(width // 2))
        for x, y in points:
            self.disc(int(x), int(y), rad, rgb, alpha)

    def glow(self, cx, cy, r, rgb, peak):
        """Soft circular glow with quadratic falloff."""
        r2 = float(r * r)
        R, G, B = rgb
        for y in range(max(0, cy - r), min(self.h - 1, cy + r) + 1):
            dy = y - cy
            dy2 = dy * dy
            reach = int(math.sqrt(max(0.0, r2 - dy2)))
            for x in range(max(0, cx - reach), min(self.w - 1, cx + reach) + 1):
                dx = x - cx
                f = 1.0 - (dx * dx + dy2) / r2
                if f <= 0.0:
                    continue
                a = int(peak * f * f * 256)
                if a <= 0:
                    continue
                ia = 256 - a
                i = self._off(x, y)
                self.buf[i] = (R * a + self.buf[i] * ia) >> 8
                self.buf[i + 1] = (G * a + self.buf[i + 1] * ia) >> 8
                self.buf[i + 2] = (B * a + self.buf[i + 2] * ia) >> 8


# ------------------------------------------------------------------- curves
def bezier(p0, p1, p2, p3, steps=18):
    """Cubic Bezier sampled into a polyline of integer points."""
    out = []
    for i in range(steps + 1):
        t = i / steps
        u = 1.0 - t
        out.append((
            int(u ** 3 * p0[0] + 3 * u * u * t * p1[0]
                + 3 * u * t * t * p2[0] + t ** 3 * p3[0]),
            int(u ** 3 * p0[1] + 3 * u * u * t * p1[1]
                + 3 * u * t * t * p2[1] + t ** 3 * p3[1]),
        ))
    return out


def tilted_oval(cx, cy, rx, ry, angle_deg, steps=26):
    """Points of an ellipse rotated by angle_deg around (cx, cy)."""
    a = math.radians(angle_deg)
    ca, sa = math.cos(a), math.sin(a)
    pts = []
    for k in range(steps):
        th = 2 * math.pi * k / steps
        ex, ey = rx * math.cos(th), ry * math.sin(th)
        pts.append((int(cx + ex * ca - ey * sa),
                    int(cy + ex * sa + ey * ca)))
    return pts


# ---------------------------------------------------------------------- sky
def paint_sky(cv):
    for y in range(HORIZON):
        cv.run(y, 0, W - 1, sky_at(y))
    # low golden sun, upper left, with a warm halo and twelve rays
    sx, sy = 178, 162
    cv.glow(sx, sy, 330, PAL["sun_halo"], 0.30)
    for k in range(12):
        ang = math.radians(k * 30.0)
        x0 = sx + int(102 * math.cos(ang))
        y0 = sy + int(102 * math.sin(ang))
        x1 = sx + int(148 * math.cos(ang))
        y1 = sy + int(148 * math.sin(ang))
        cv.line([(x0, y0), (x1, y1)], 7, (255, 190, 80), 0.8)
    cv.disc(sx, sy, 86, PAL["sun_edge"])
    cv.disc(sx, sy, 73, PAL["sun_core"])
    # a bright glint in the sun's heart, like a smile catching light
    cv.disc(sx - 18, sy - 20, 12, PAL["wing_white"], 0.55)
    # pollen sparkles drifting in the light
    rng = Random(SEED)
    for _ in range(24):
        cv.disc(rng.randrange(40, 980), rng.randrange(30, 560),
                rng.choice([2, 3]), PAL["glint"], 0.5)
    # puffy clouds, kept clear of the sun's rays
    for cx, cy, s in [(566, 118, 1.0), (836, 258, 0.85), (396, 298, 0.7),
                      (706, 468, 0.6), (118, 418, 0.75)]:
        for dx, dy, r in [(-70, 6, 34), (-25, -14, 42), (25, -10, 46),
                          (72, 8, 32), (0, 12, 44)]:
            cv.disc(int(cx + dx * s), int(cy + dy * s), int(r * s),
                    PAL["cloud"], 0.34)


def paint_hills(cv):
    # far hill: a broad rolling shape peeking over the horizon
    cv.fill([(0, HORIZON), (0, 590), (150, 554), (330, 594), (520, 560),
             (700, 598), (880, 564), (1024, 594), (1024, HORIZON)],
            PAL["hill_back"])
    # near hill, slightly lower and darker
    cv.fill([(0, HORIZON), (0, 630), (170, 604), (360, 636), (560, 608),
             (780, 640), (1024, 612), (1024, HORIZON)], PAL["hill_front"])
    # three little lollipop trees on the far hill
    for tx, ty, s in [(152, 560, 1.0), (908, 566, 0.9), (664, 574, 0.75)]:
        cv.line([(tx, ty), (tx, ty - int(34 * s))], 7, PAL["trunk"])
        cv.disc(tx, ty - int(48 * s), int(26 * s), PAL["leaf"])
        cv.disc(tx - int(16 * s), ty - int(38 * s), int(18 * s),
                PAL["leaf_hi"])
        cv.disc(tx + int(16 * s), ty - int(40 * s), int(17 * s),
                PAL["leaf"])


# -------------------------------------------------------------------- meadow
def paint_meadow(cv):
    for y in range(HORIZON, H):
        t = (y - HORIZON) / (H - HORIZON)
        cv.run(y, 0, W - 1, blend(PAL["grass_hi"], PAL["grass_lo"], t))
    # warm pool of sunlight on the grass, centre-right
    cv.oval(566, 846, 420, 118, PAL["light_pool"], 0.10)
    # soft shadow where the puppy will sit
    cv.oval(512, 994, 300, 42, PAL["shade"], 0.22)


def paint_grass(cv, rng):
    for _ in range(150):
        x = rng.randrange(8, 1016)
        y = rng.randrange(HORIZON + 18, 1012)
        h = rng.randrange(12, 30)
        lean = rng.randrange(-10, 11)
        col = rng.choice([PAL["blade_a"], PAL["blade_b"], PAL["grass_lo"]])
        cv.fill([(x, y), (x + lean, y - h), (x + 5, y)], col, 0.85)
        # a second blade leaning the other way makes a tuft
        cv.fill([(x + 6, y), (x + 6 - lean, y - h - 4), (x + 10, y)],
                col, 0.8)


def paint_daisy(cv, cx, cy, r, petal, centre):
    for k in range(6):
        th = 2 * math.pi * k / 6 - math.pi / 2
        cv.disc(cx + int(r * 0.66 * math.cos(th)),
                cy + int(r * 0.66 * math.sin(th)),
                int(r * 0.46), petal)
    cv.disc(cx, cy, int(r * 0.42), centre)


def paint_tulip(cv, cx, cy, r, colour):
    # cup-shaped bloom on a short stem
    cv.line([(cx, cy + int(r * 1.5)), (cx, cy + int(r * 0.4))], 4,
            PAL["stem"])
    cv.fill([(cx - r, cy - int(r * 0.4)), (cx - r, cy + int(r * 0.7)),
             (cx + r, cy + int(r * 0.7)), (cx + r, cy - int(r * 0.4)),
             (cx + int(r * 0.5), cy - r), (cx, cy - int(r * 0.5)),
             (cx - int(r * 0.5), cy - r)], colour)


def paint_lavender(cv, cx, cy, r, colour):
    cv.line([(cx, cy + int(r * 2.2)), (cx, cy - int(r * 0.6))], 4,
            PAL["stem"])
    for i in range(4):
        yy = cy - int(r * 0.5) - i * int(r * 0.42)
        cv.oval(cx, yy, int(r * 0.42), int(r * 0.3), colour)


def paint_flowers(cv, rng):
    keep_clear = (512, 830, 340)  # (cx, cy, r): the puppy's patch
    for _ in range(58):
        x = rng.randrange(28, 996)
        y = rng.randrange(HORIZON + 28, 1002)
        dx, dy = x - keep_clear[0], y - keep_clear[1]
        if dx * dx + dy * dy < keep_clear[2] ** 2:
            continue
        kind = rng.randrange(3)
        r = rng.choice([9, 11, 13, 15])
        col = rng.choice(BLOOMS)
        if kind == 0:
            paint_daisy(cv, x, y, r, col, PAL["centre"])
        elif kind == 1:
            paint_tulip(cv, x, y, r, col)
        else:
            paint_lavender(cv, x, y, r, col)
    # big soft foreground blooms framing the bottom corners
    paint_daisy(cv, 92, 950, 44, PAL["tulip"], PAL["centre"])
    paint_daisy(cv, 944, 934, 48, PAL["daisy"], PAL["centre"])
    paint_tulip(cv, 152, 992, 30, PAL["buttercup"])
    paint_tulip(cv, 892, 996, 32, PAL["lavender"])
    paint_daisy(cv, 60, 830, 26, PAL["poppy"], PAL["centre"])
    paint_daisy(cv, 968, 820, 26, PAL["buttercup"], PAL["centre"])


# ----------------------------------------------------------------- butterfly
def paint_butterfly(cv, cx, cy, size, wing, tilt=0, open_wings=1.0):
    """Butterfly seen from above: dark-rimmed wings, pale spots, body,
    antennae. tilt rotates the whole insect; open_wings squeezes the
    upper wings for a resting pose."""
    s = size / 46.0
    a = math.radians(tilt)
    ca, sa = math.cos(a), math.sin(a)

    def place(dx, dy, rx, ry, ang):
        pts = tilted_oval(0, 0, rx, ry, ang)
        out = []
        for ex, ey in pts:
            wx, wy = dx + ex, dy + ey
            out.append((int(cx + wx * ca - wy * sa),
                        int(cy + wx * sa + wy * ca)))
        return out

    upper_h = 26 * open_wings
    for side in (-1, 1):
        # upper wing: dark rim, then coloured inner wing
        cv.fill(place(side * 17 * s, -15 * s, 22 * s, upper_h * s,
                      side * -20), PAL["wing_rim"], 0.95)
        cv.fill(place(side * 17 * s, -15 * s, 18 * s, upper_h * s * 0.82,
                      side * -20), wing, 0.95)
        # lower wing, smaller and rounder
        cv.fill(place(side * 15 * s, 13 * s, 16 * s, 13 * s, side * 24),
                PAL["wing_rim"], 0.95)
        cv.fill(place(side * 15 * s, 13 * s, 12.5 * s, 10 * s, side * 24),
                wing, 0.95)
        # pale spot on the upper wing
        sx = cx + int((side * 17 * s) * ca - (-15 * s) * sa)
        sy = cy + int((side * 17 * s) * sa + (-15 * s) * ca)
        cv.disc(sx, sy, int(4.5 * s), PAL["wing_white"], 0.9)
        # smaller pale dot on the lower wing
        lx = cx + int((side * 15 * s) * ca - (13 * s) * sa)
        ly = cy + int((side * 15 * s) * sa + (13 * s) * ca)
        cv.disc(lx, ly, int(3 * s), PAL["wing_white"], 0.85)
    # body, head and two curled antennae
    cv.line(bezier((cx, cy - 17 * s), (cx - 2 * s, cy),
                   (cx + 2 * s, cy + 8 * s), (cx, cy + 19 * s)),
            6, PAL["wing_rim"])
    cv.disc(cx, int(cy - 17 * s), int(4 * s), PAL["wing_rim"])
    cv.line(bezier((cx, cy - 18 * s), (cx - 9 * s, cy - 30 * s),
                   (cx - 13 * s, cy - 32 * s),
                   (cx - 15 * s, cy - 36 * s)), 2, PAL["wing_rim"])
    cv.line(bezier((cx, cy - 18 * s), (cx + 9 * s, cy - 30 * s),
                   (cx + 13 * s, cy - 32 * s),
                   (cx + 15 * s, cy - 36 * s)), 2, PAL["wing_rim"])


def paint_air_butterflies(cv):
    paint_butterfly(cv, 872, 300, 42, PAL["wing_yellow"], tilt=16,
                    open_wings=1.0)
    paint_butterfly(cv, 700, 150, 34, PAL["wing_white"], tilt=10,
                    open_wings=0.85)
    paint_butterfly(cv, 130, 250, 40, PAL["wing_orange"], tilt=-20,
                    open_wings=1.0)
    paint_butterfly(cv, 300, 430, 30, PAL["wing_pink"], tilt=-8,
                    open_wings=0.9)


# ---------------------------------------------------------------------- puppy
def paint_puppy(cv):
    # ---- body: a big golden mass, cropped at the bottom edge, with a
    # cream chest patch so head and body read as one puppy
    cv.oval(512, 935, 305, 290, PAL["fur"])
    cv.oval(512, 868, 180, 158, PAL["fur_cream"])
    # ---- front paws with toe lines
    for paw_x in (412, 612):
        cv.oval(paw_x, 950, 66, 50, PAL["fur_dark"])
        cv.oval(paw_x, 950, 60, 44, PAL["fur_pale"])
        for dx in (-20, 8):
            cv.line([(paw_x + dx, 934), (paw_x + dx, 966)], 4,
                    PAL["fur_dark"], 0.7)

    # ---- floppy ears: long drooping shapes beside the head, darker
    # gold outside, lighter inside, one ear flopped a touch lower
    cv.fill([(352, 380), (398, 372), (392, 560), (330, 640),
             (288, 560), (300, 430)], PAL["fur_dark"])
    cv.disc(330, 618, 24, PAL["fur_dark"])  # rounded ear tip
    cv.fill([(672, 380), (626, 372), (632, 560), (694, 640),
             (736, 560), (724, 430)], PAL["fur_dark"])
    cv.disc(694, 618, 24, PAL["fur_dark"])  # rounded ear tip
    cv.fill([(356, 420), (384, 420), (378, 556), (336, 606),
             (310, 540)], PAL["ear_inner"])
    cv.fill([(668, 420), (640, 420), (646, 556), (688, 606),
             (714, 540)], PAL["ear_inner"])

    # ---- head, with a lighter face front and a tuft on top
    cv.disc(512, 468, 198, PAL["fur"])
    cv.oval(512, 496, 162, 146, PAL["fur_cream"])
    cv.fill([(468, 292), (488, 258), (504, 292)], PAL["fur"])
    cv.fill([(500, 288), (524, 252), (540, 290)], PAL["fur"])
    cv.fill([(530, 290), (554, 262), (564, 294)], PAL["fur"])

    # ---- happy closed eyes: squeezed-shut upward arcs
    for ex in (390, 566):
        cv.line(bezier((ex, 442), (ex + 16, 408), (ex + 50, 408),
                       (ex + 66, 442)), 15, PAL["eye"])
    # ---- rosy cheeks
    cv.disc(396, 560, 28, PAL["blush"], 0.5)
    cv.disc(628, 560, 28, PAL["blush"], 0.5)

    # ---- muzzle, nose, open smiling mouth, tongue
    cv.oval(512, 578, 128, 88, PAL["fur_pale"])
    cv.oval(512, 516, 42, 28, PAL["nose"])
    cv.disc(498, 506, 6, PAL["wing_white"], 0.85)  # nose glint
    cv.oval(512, 604, 48, 36, PAL["mouth"])
    cv.oval(512, 620, 30, 26, PAL["tongue"])
    cv.line([(512, 600), (512, 634)], 4, PAL["tongue_shade"], 0.8)
    # smile creases sweeping up from the mouth corners
    cv.line(bezier((464, 600), (448, 574), (442, 556), (436, 548)),
            6, PAL["eye"], 0.8)
    cv.line(bezier((560, 600), (576, 574), (582, 556), (588, 548)),
            6, PAL["eye"], 0.8)
    # whisker dots on the muzzle
    for dx, dy in [(-82, -6), (-90, 14), (82, -6), (90, 14),
                   (-68, 24), (68, 24)]:
        cv.disc(512 + dx, 578 + dy, 3, PAL["fur_dark"], 0.7)

    # ---- the surprise: an orange butterfly has landed on the nose,
    # wings half-folded, right between the puppy's eyes
    paint_butterfly(cv, 512, 478, 56, PAL["wing_orange"], tilt=0,
                    open_wings=0.55)


# --------------------------------------------------------------------- PNG out
def png_chunk(tag, data):
    out = struct.pack(">I", len(data)) + tag + data
    return out + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def encode_png(cv):
    raw = bytearray()
    for y in range(cv.h):
        raw.append(0)  # filter type: none
        raw += cv.buf[y * cv.w * 3:(y + 1) * cv.w * 3]
    body = b"\x89PNG\r\n\x1a\n"
    body += png_chunk(b"IHDR",
                      struct.pack(">IIBBBBB", cv.w, cv.h, 8, 2, 0, 0, 0))
    body += png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
    body += png_chunk(b"IEND", b"")
    return body


def build_scene():
    rng = Random(SEED)
    cv = Canvas(W, H)
    paint_sky(cv)
    paint_hills(cv)
    paint_meadow(cv)
    paint_grass(cv, rng)
    paint_flowers(cv, rng)
    paint_puppy(cv)
    paint_air_butterflies(cv)
    return cv


def output_dir():
    """Where entry.png goes.

    The grader runs as uid 65534 on a read-only filesystem with a
    writable /output mounted and sets no MAKEFUN_OUTPUT_DIR, so the
    /output fallback is what saves the run there. Locally, an explicit
    env var wins; with neither, fall back to the current directory.
    """
    env_dir = os.environ.get("MAKEFUN_OUTPUT_DIR")
    if env_dir:
        return env_dir
    if os.path.isdir("/output"):
        return "/output"
    return "."


def main():
    cv = build_scene()
    out_dir = output_dir()
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "entry.png")
    data = encode_png(cv)
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes)")


if __name__ == "__main__":
    main()
