#!/usr/bin/env python3
"""THE WORLD IN ONE DAY - Tuesday, 24 November 2026.

A standard-library-only program that draws a newspaper front page summing up
the world news of Tuesday 24 November 2026 and writes it to /output/entry.png
(or $MAKEFUN_OUTPUT_DIR/entry.png). Fully deterministic: fixed content, no
clock, no randomness, no network, no third-party code.

Rendering: a hand-authored vector stroke font is drawn into an RGB buffer at
2x supersampling, box-downsampled, and PNG-encoded with zlib.
"""
import os
import struct
import zlib

# --------------------------------------------------------------------------
# Vector stroke font.
# Glyph space: y grows downward. Cap height = 9 units (y 0..9), x-height
# top y=3, baseline y=9, descenders to y=12. Each glyph is
# (advance_width, [stroke, ...]); a stroke is a list of (x, y) points.
# A single-point stroke renders as a dot.
# --------------------------------------------------------------------------
F = {
    'A': (8, [[(0, 9), (3.5, 0), (7, 9)], [(1.6, 6), (5.4, 6)]]),
    'B': (8, [[(0, 0), (0, 9)], [(0, 0), (4, 0), (5.5, 1.5), (5.5, 3.3), (4, 4.5), (0, 4.5)],
              [(4, 4.5), (5.5, 5.6), (5.5, 7.6), (4, 9), (0, 9)]]),
    'C': (8, [[(6.5, 2), (5, 0.5), (3, 0), (1, 1), (0, 3), (0, 6), (1, 8), (3, 9), (5, 8.8), (6.5, 7)]]),
    'D': (8, [[(0, 0), (0, 9)], [(0, 0), (3.5, 0), (6, 1.5), (6.8, 4.5), (6, 7.5), (3.5, 9), (0, 9)]]),
    'E': (7, [[(6, 0), (0, 0), (0, 9), (6, 9)], [(0, 4.5), (4.5, 4.5)]]),
    'F': (7, [[(0, 9), (0, 0), (6, 0)], [(0, 4.5), (4, 4.5)]]),
    'G': (8, [[(6.5, 2), (5, 0.5), (3, 0), (1, 1), (0, 3), (0, 6), (1, 8), (3, 9), (5.5, 9), (7, 7.5), (7, 5), (4.5, 5)]]),
    'H': (8, [[(0, 0), (0, 9)], [(7, 0), (7, 9)], [(0, 4.5), (7, 4.5)]]),
    'I': (3, [[(1, 0), (1, 9)], [(0, 0), (2, 0)], [(0, 9), (2, 9)]]),
    'J': (6, [[(5, 0), (5, 7), (4, 8.5), (2, 9), (0.5, 8), (0, 6.5)]]),
    'K': (8, [[(0, 0), (0, 9)], [(6.5, 0), (0, 5)], [(1.5, 4), (7, 9)]]),
    'L': (7, [[(0, 0), (0, 9), (6, 9)]]),
    'M': (9, [[(0, 9), (0, 0), (4, 6), (8, 0), (8, 9)]]),
    'N': (8, [[(0, 9), (0, 0), (7, 9), (7, 0)]]),
    'O': (8, [[(3.5, 0), (1, 0.8), (0, 3), (0, 6), (1, 8.2), (3.5, 9), (6, 8.2), (7, 6), (7, 3), (6, 0.8), (3.5, 0)]]),
    'P': (8, [[(0, 9), (0, 0), (4.5, 0), (6, 1.5), (6, 3.5), (4.5, 5), (0, 5)]]),
    'Q': (8, [[(3.5, 0), (1, 0.8), (0, 3), (0, 6), (1, 8.2), (3.5, 9), (6, 8.2), (7, 6), (7, 3), (6, 0.8), (3.5, 0)],
              [(4.5, 6.5), (7.5, 9.5)]]),
    'R': (8, [[(0, 9), (0, 0), (4.5, 0), (6, 1.5), (6, 3.5), (4.5, 5), (0, 5)], [(4.5, 5), (7, 9)]]),
    'S': (7, [[(6, 1.5), (4.5, 0.3), (2, 0), (0.8, 1.5), (1, 3.5), (3, 4.5), (5.5, 5.5), (6.2, 7.5), (5, 9), (2.5, 9.3), (0.5, 8)]]),
    'T': (8, [[(0, 0), (7, 0)], [(3.5, 0), (3.5, 9)]]),
    'U': (8, [[(0, 0), (0, 6.5), (1.5, 8.7), (3.5, 9), (5.5, 8.7), (7, 6.5), (7, 0)]]),
    'V': (8, [[(0, 0), (3.5, 9), (7, 0)]]),
    'W': (10, [[(0, 0), (1.8, 9), (4, 3), (5.8, 9), (8, 0)]]),
    'X': (8, [[(0, 0), (7, 9)], [(7, 0), (0, 9)]]),
    'Y': (8, [[(0, 0), (3.5, 4.5), (7, 0)], [(3.5, 4.5), (3.5, 9)]]),
    'Z': (8, [[(0, 0), (7, 0), (0, 9), (7, 9)]]),
    'a': (7, [[(5, 6), (4, 3.5), (2, 3), (0.8, 4.5), (0.8, 7.5), (2, 9), (4, 8.7), (5, 7)], [(5, 3), (5, 9)]]),
    'b': (7, [[(0, 0), (0, 9)], [(0, 6), (1.5, 3.8), (3.5, 3), (5, 4.5), (5.2, 6.5), (4, 8.7), (2, 9), (0, 7.5)]]),
    'c': (6.5, [[(5, 4), (3.5, 3), (1.5, 3.5), (0.7, 6), (1.5, 8.5), (3.5, 9), (5, 8)]]),
    'd': (7, [[(5, 0), (5, 9)], [(5, 6), (3.8, 3.8), (2, 3), (0.8, 4.5), (0.8, 7.5), (2, 9), (3.8, 8.8), (5, 7.5)]]),
    'e': (7, [[(0.8, 6), (5, 6), (4.8, 4.3), (3, 3), (1.2, 4), (0.8, 6.5), (1.5, 8.5), (3.5, 9), (5, 8.2)]]),
    'f': (5, [[(4.5, 1.2), (3, 0), (1.8, 1), (1.8, 9)], [(0.3, 3.5), (3.8, 3.5)]]),
    'g': (7, [[(5, 3), (5, 10.5), (4, 12), (2, 12.2), (0.8, 11)],
               [(5, 6), (3.8, 3.8), (2, 3), (0.8, 4.5), (0.8, 7.5), (2, 9), (3.8, 8.8), (5, 7.5)]]),
    'h': (7, [[(0, 0), (0, 9)], [(0, 5.5), (1.5, 3.8), (3.5, 3.2), (5, 4.5), (5, 9)]]),
    'i': (3, [[(1, 3), (1, 9)], [(1, 0.8)]]),
    'j': (4, [[(3, 3), (3, 10.5), (2, 12), (0.5, 11.8)], [(3, 0.8)]]),
    'k': (7, [[(0, 0), (0, 9)], [(4.5, 3), (0.5, 6.5)], [(1.8, 5.2), (5, 9)]]),
    'l': (3, [[(1, 0), (1, 9)]]),
    'm': (11, [[(0, 3), (0, 9)], [(0, 5), (1.5, 3.5), (3.5, 3.2), (4.5, 4.5), (4.5, 9)],
               [(4.5, 5), (6, 3.5), (8, 3.2), (9, 4.5), (9, 9)]]),
    'n': (7, [[(0, 3), (0, 9)], [(0, 5), (1.5, 3.5), (3.5, 3.2), (5, 4.5), (5, 9)]]),
    'o': (7, [[(2.5, 3), (1, 3.8), (0.5, 6), (1, 8.3), (2.5, 9), (4.5, 9), (5.8, 8.3), (6.3, 6), (5.8, 3.8), (4.5, 3), (2.5, 3)]]),
    'p': (7, [[(0, 3), (0, 12)], [(0, 5.5), (1.5, 3.8), (3.5, 3), (5, 4.5), (5.2, 6.5), (4, 8.7), (2, 9), (0, 7.8)]]),
    'q': (7, [[(5, 3), (5, 12)], [(5, 6), (3.8, 3.8), (2, 3), (0.8, 4.5), (0.8, 7.5), (2, 9), (3.8, 8.8), (5, 7.5)]]),
    'r': (5, [[(0, 3), (0, 9)], [(0, 5), (1.5, 3.5), (3.5, 3.2)]]),
    's': (6, [[(5, 4), (3.5, 3), (1.5, 3.3), (1, 5), (2.5, 6.3), (4.5, 7.3), (4.8, 8.8), (3, 9.2), (1, 8.8), (0.3, 8)]]),
    't': (5, [[(2, 1.5), (2, 8), (3, 9), (4.5, 8.7)], [(0.3, 3.5), (4.5, 3.5)]]),
    'u': (7, [[(0, 3), (0.2, 7), (1.5, 8.8), (3.5, 8.8), (5, 7), (5, 3)], [(5, 7.5), (5, 9)]]),
    'v': (7, [[(0, 3), (3, 9), (6, 3)]]),
    'w': (10, [[(0, 3), (1.5, 9), (3.5, 4.5), (5.5, 9), (8, 3)]]),
    'x': (7, [[(0, 3), (6, 9)], [(6, 3), (0, 9)]]),
    'y': (7, [[(0, 3), (2.8, 7.5)], [(6, 3), (2.8, 7.5), (2.5, 10.5), (1.2, 12), (0.2, 11.3)]]),
    'z': (7, [[(0, 3), (6, 3), (0, 9), (6, 9)]]),
    '0': (8, [[(3.5, 0), (1.5, 0.8), (0.8, 3), (0.8, 6), (1.5, 8.2), (3.5, 9), (5.5, 8.2), (6.2, 6), (6.2, 3), (5.5, 0.8), (3.5, 0)]]),
    '1': (6, [[(1.5, 2), (3.5, 0), (3.5, 9)], [(1.5, 9), (5, 9)]]),
    '2': (8, [[(1, 2), (2.5, 0.3), (5, 0.3), (6.2, 2), (5.5, 4.5), (0.5, 9), (6.5, 9)]]),
    '3': (8, [[(1, 1.5), (3, 0.2), (5.5, 1), (5.8, 3), (4.5, 4.5), (2.5, 4.5)],
              [(4.5, 4.5), (6, 6), (5.5, 8.3), (3, 9.2), (0.8, 8)]]),
    '4': (8, [[(5, 9), (5, 0), (0.5, 6.5), (7, 6.5)]]),
    '5': (8, [[(6, 0), (1.5, 0), (1, 4), (3.5, 3.8), (5.8, 5.5), (5.5, 8), (3, 9.2), (0.8, 8.3)]]),
    '6': (8, [[(5.5, 1.5), (3.5, 0.3), (1.5, 2), (0.8, 5), (1.5, 8), (3.5, 9.2), (5.5, 8.3), (6, 6), (4.8, 4.3), (2.8, 4.2), (1, 5.5)]]),
    '7': (8, [[(0.5, 0), (6.5, 0), (3, 9)]]),
    '8': (8, [[(3.5, 4.5), (1.5, 3.8), (1, 2), (2, 0.5), (4.5, 0.3), (6, 1.5), (5.8, 3.5), (3.5, 4.5)],
              [(3.5, 4.5), (5.5, 5.5), (6, 7.5), (4.5, 9.2), (2, 9), (0.8, 7.3), (1.2, 5.5), (3.5, 4.5)]]),
    '9': (8, [[(1, 7.5), (3, 9), (5.5, 7.5), (6.2, 4), (5.5, 1.5), (3.5, 0.2), (1.5, 1.2), (1, 3.5), (2.5, 5), (5, 4.8), (6, 3.5)]]),
    '.': (3, [[(1, 8.8)]]),
    ',': (3, [[(1.2, 8.6), (0.7, 11)]]),
    ':': (3, [[(1, 3.2)], [(1, 8.6)]]),
    ';': (3, [[(1, 3.2)], [(1.2, 8.6), (0.7, 11)]]),
    "'": (3, [[(1, 0), (0.7, 2.2)]]),
    '"': (5, [[(1, 0), (0.7, 2.2)], [(3.6, 0), (3.3, 2.2)]]),
    '-': (5, [[(0.5, 5.5), (4, 5.5)]]),
    '!': (3, [[(1, 0), (1, 6.3)], [(1, 8.8)]]),
    '?': (7, [[(1, 2), (2.5, 0.3), (5, 0.5), (5.8, 2.5), (4.5, 4.5), (3, 5.5), (3, 7)], [(3, 8.8)]]),
    '(': (5, [[(4, 0), (2.2, 2.5), (1.5, 5), (2.2, 7.5), (4, 10)]]),
    ')': (5, [[(1, 0), (2.8, 2.5), (3.5, 5), (2.8, 7.5), (1, 10)]]),
    '/': (6, [[(5, 0), (0.5, 10)]]),
    '+': (7, [[(3, 2), (3, 8)], [(0.5, 5), (5.5, 5)]]),
    '=': (7, [[(0.5, 3.5), (6, 3.5)], [(0.5, 6.5), (6, 6.5)]]),
    '$': (7, [[(6, 1.5), (4.5, 0.3), (2, 0), (0.8, 1.5), (1, 3.5), (3, 4.5), (5.5, 5.5), (6.2, 7.5), (5, 9), (2.5, 9.3), (0.5, 8)],
              [(3.2, 0), (3.2, 9.6)]]),
    '%': (10, [[(8.5, 0), (1.5, 9.5)],
               [(2, 0.5), (0.8, 1.5), (0.8, 3), (2, 4), (3.2, 3), (3.2, 1.5), (2, 0.5)],
               [(7.5, 5.8), (6.3, 6.8), (6.3, 8.3), (7.5, 9.3), (8.7, 8.3), (8.7, 6.8), (7.5, 5.8)]]),
    '&': (8, [[(6.5, 8.8), (4.5, 5.5), (2.8, 3.2), (3, 1.2), (4.8, 0.6), (5.4, 2.6), (3.2, 6), (1, 8.2), (2.6, 9.3), (5.2, 8.8), (6.5, 9.3)]]),
    '\u00b7': (4, [[(1.8, 5.2)]]),   # middle dot
    '\u2013': (6, [[(0.5, 5.5), (5, 5.5)]]),   # en dash
    '\u2014': (9, [[(0.5, 5.5), (8, 5.5)]]),   # em dash
    '\u00dc': (8, [[(0, 0), (0, 6.5), (1.5, 8.7), (3.5, 9), (5.5, 8.7), (7, 6.5), (7, 0)], [(1.8, -1.6)], [(5.2, -1.6)]]),
    '\u00fc': (7, [[(0, 3), (0.2, 7), (1.5, 8.8), (3.5, 8.8), (5, 7), (5, 3)], [(5, 7.5), (5, 9)], [(1.5, 1.1)], [(4, 1.1)]]),
}
SPACE_ADV = 3.6

# --------------------------------------------------------------------------
# Canvas: RGB buffer at SS x supersampling, box-downsampled at the end.
# All public drawing coordinates are in final-image pixels.
# --------------------------------------------------------------------------
W, H, SS = 1024, 1024, 2
BW, BH = W * SS, H * SS
buf = bytearray(BW * BH * 3)


def _set(x, y, rgb):
    if 0 <= x < BW and 0 <= y < BH:
        i = (y * BW + x) * 3
        buf[i] = rgb[0]
        buf[i + 1] = rgb[1]
        buf[i + 2] = rgb[2]


def fill_rect(x, y, w, h, rgb):
    """Filled rectangle in final-image coordinates."""
    x0, y0 = int(round(x * SS)), int(round(y * SS))
    x1, y1 = int(round((x + w) * SS)), int(round((y + h) * SS))
    x0, y0 = max(0, x0), max(0, y0)
    x1, y1 = min(BW, x1), min(BH, y1)
    if x1 <= x0 or y1 <= y0:
        return
    row = bytes(rgb) * (x1 - x0)
    n = (x1 - x0) * 3
    for yy in range(y0, y1):
        i = (yy * BW + x0) * 3
        buf[i:i + n] = row


def _stamp(cx, cy, r, rgb):
    """Filled circle stamp in buffer coordinates."""
    r2 = r * r
    x0, x1 = int(cx - r - 1), int(cx + r + 1)
    y0, y1 = int(cy - r - 1), int(cy + r + 1)
    for yy in range(y0, y1 + 1):
        dy = yy + 0.5 - cy
        for xx in range(x0, x1 + 1):
            dx = xx + 0.5 - cx
            if dx * dx + dy * dy <= r2:
                _set(xx, yy, rgb)


def line(xa, ya, xb, yb, thick, rgb):
    """Thick round-capped line in final-image coordinates."""
    ax, ay, bx, by = xa * SS, ya * SS, xb * SS, yb * SS
    r = thick * SS / 2.0
    dx, dy = bx - ax, by - ay
    dist = (dx * dx + dy * dy) ** 0.5
    steps = max(1, int(dist / max(1.0, r * 0.6)))
    for i in range(steps + 1):
        t = i / steps
        _stamp(ax + dx * t, ay + dy * t, r, rgb)


def polyline(points, thick, rgb, close=False):
    pts = list(points)
    if close and pts:
        pts.append(pts[0])
    for a, b in zip(pts, pts[1:]):
        line(a[0], a[1], b[0], b[1], thick, rgb)


def circle(cx, cy, r, thick, rgb):
    import math
    n = max(24, int(2 * math.pi * r / 3))
    pts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n))
           for i in range(n + 1)]
    polyline(pts, thick, rgb)


def dot(cx, cy, r, rgb):
    _stamp(cx * SS, cy * SS, r * SS, rgb)


# --------------------------------------------------------------------------
# Text
# --------------------------------------------------------------------------
def _n(s):
    """Normalise characters the font does not carry (Turkish dotted I)."""
    return s.replace('\u0130', 'I').replace('\u0131', 'i')


def text_width(s, size, tracking=0.0):
    """Width in px of string s at cap-height `size` px."""
    s = _n(s)
    u = size / 9.0
    w = 0.0
    for ch in s:
        if ch == ' ':
            w += SPACE_ADV * u
        elif ch in F:
            w += F[ch][0] * u
        else:
            w += SPACE_ADV * u
        w += tracking
    return w - (tracking if s else 0.0)


def draw_text(x, y, s, size, rgb, thick=None, tracking=0.0, bold=False):
    """Draw s with its cap-height top at y; x is the left edge.
    Returns the x just past the last glyph."""
    s = _n(s)
    u = size / 9.0
    if thick is None:
        thick = size * (0.16 if bold else 0.125)
    cx = x
    for ch in s:
        if ch == ' ':
            cx += SPACE_ADV * u + tracking
            continue
        g = F.get(ch)
        if g is None:
            cx += SPACE_ADV * u + tracking
            continue
        adv, strokes = g
        for stroke in strokes:
            pts = [(cx + px * u, y + py * u) for (px, py) in stroke]
            if len(pts) == 1:
                dot(pts[0][0], pts[0][1], thick * 0.62, rgb)
            else:
                polyline(pts, thick, rgb)
        cx += adv * u + tracking
    return cx


def draw_text_centered(cx, y, s, size, rgb, thick=None, tracking=0.0, bold=False):
    w = text_width(s, size, tracking)
    return draw_text(cx - w / 2.0, y, s, size, rgb, thick, tracking, bold)


def draw_text_right(xr, y, s, size, rgb, thick=None, tracking=0.0, bold=False):
    w = text_width(s, size, tracking)
    return draw_text(xr - w, y, s, size, rgb, thick, tracking, bold)


def wrap(s, size, max_w, tracking=0.0):
    """Greedy word wrap; returns list of lines."""
    words = s.split()
    lines, cur = [], ''
    for wd in words:
        trial = wd if not cur else cur + ' ' + wd
        if text_width(trial, size, tracking) <= max_w or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


# --------------------------------------------------------------------------
# PNG output
# --------------------------------------------------------------------------
def downsample():
    out = bytearray(W * H * 3)
    for y in range(H):
        for x in range(W):
            r = g = b = 0
            for dy in range(SS):
                base = ((y * SS + dy) * BW + x * SS) * 3
                for dx in range(SS):
                    i = base + dx * 3
                    r += buf[i]
                    g += buf[i + 1]
                    b += buf[i + 2]
            n = SS * SS
            o = (y * W + x) * 3
            out[o] = (r + n // 2) // n
            out[o + 1] = (g + n // 2) // n
            out[o + 2] = (b + n // 2) // n
    return bytes(out)


def png_bytes(rgb):
    def chunk(tag, data):
        c = struct.pack('>I', len(data)) + tag + data
        return c + struct.pack('>I', zlib.crc32(tag + data) & 0xffffffff)
    raw = bytearray()
    stride = W * 3
    for y in range(H):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    ihdr = struct.pack('>IIBBBBB', W, H, 8, 2, 0, 0, 0)
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', ihdr) +
            chunk(b'IDAT', zlib.compress(bytes(raw), 9)) + chunk(b'IEND', b''))

# --------------------------------------------------------------------------
# Content: the verified news of Tuesday 24 November 2026.
# --------------------------------------------------------------------------
INK = (20, 22, 26)
PAPER = (247, 242, 230)
CARD = (255, 253, 246)
FAINT = (120, 112, 96)
LINEC = (198, 190, 166)
RED = (179, 53, 43)
BODY = (46, 48, 52)

LEAD_HEAD = "FACTORY FIRE: 28 WORKERS STILL MISSING"
LEAD_SUM = ("Police open a negligence probe into the Cikande candy-factory "
            "blaze in Banten: 26 body bags recovered, 16 victims identified.")

# (tag, colour, headline, summary)
PANELS = [
    ("RUSSIA", (163, 44, 36),
     "LEAKED DATA: 700,000 RUSSIAN WAR DEAD",
     "Meduza counts 490,000 registered military deaths; with the missing, "
     "the toll tops 700,000."),
    ("UKRAINE", (178, 84, 40),
     "STRIKES KILL 11, CUT POWER TO 353,000",
     "Rescuers pull a boy of 7 and a woman of 79 alive from the rubble "
     "in Dymer."),
    ("CLIMATE", (46, 110, 54),
     "COP31 COLLAPSE SPARKS BLAME AND REFORM CALLS",
     "Calls grow for Australia's Bowen to quit as Pacific nations "
     "voice despair."),
    ("EUROPE", (64, 84, 140),
     "EU PROPOSES 22ND RUSSIA SANCTIONS PACKAGE",
     "Some 60 banks face a SWIFT ban; 70-plus shadow-fleet ships "
     "are targeted."),
    ("MIDDLE EAST", (146, 94, 32),
     "IRAN VOWS REPLY AS US SANCTIONS NETWORKS",
     "Tehran pledges 'every means' against the US blockade; two dozen "
     "money houses are hit."),
    ("MARKETS", (30, 110, 106),
     "BITCOIN'S WORST NOVEMBER SINCE 2018",
     "Bitcoin slides toward $60,000 as spot ETFs shed $4.14B and fear "
     "turns extreme."),
    ("UNITED STATES", (31, 58, 95),
     "FIRST GEN Z WOMAN ELECTED TO CONGRESS",
     "Melat Kiros, 29, a Denver Democrat, is also the first Black woman "
     "to represent Colorado."),
    ("MEXICO", (122, 62, 110),
     "MEXICO TO TRY 'EL CHAPO ISIDRO' AT HOME",
     "Mexico's top prosecutor defies a US extradition bid for the "
     "captured cartel boss."),
    ("COLOMBIA", (150, 40, 80),
     "CAR BOMB ROCKS COLOMBIA GOVERNOR'S OFFICE",
     "The Villavicencio blast injures 12 and wrecks buildings; the "
     "president blames drug gangs."),
    ("EBOLA", (140, 70, 20),
     "CONGO EBOLA DEATHS PASS 5,600",
     "WHO counts 5,678 deaths in Congo's outbreak; Kenya, its last "
     "patient home, counts down to Ebola-free."),
]


def rect_outline(x, y, w, h, t, rgb):
    fill_rect(x, y, w, t, rgb)
    fill_rect(x, y + h - t, w, t, rgb)
    fill_rect(x, y, t, h, rgb)
    fill_rect(x + w - t, y, t, h, rgb)


def draw_globe(cx, cy, r):
    import math
    circle(cx, cy, r, 2.4, INK)
    # equator + parallels (squashed ellipses)
    for frac, off in ((1.0, 0.0), (0.86, -0.5), (0.86, 0.5), (0.5, -0.86), (0.5, 0.86)):
        rx, ry = r * frac, r * frac * 0.30
        pts = [(cx + rx * math.sin(2 * math.pi * i / 48),
                cy + off * r + ry * math.cos(2 * math.pi * i / 48)) for i in range(49)]
        polyline(pts, 1.1, (90, 96, 104))
    # meridians (vertical ellipses)
    for frac in (0.35, 0.7, 1.0):
        rx = r * frac
        pts = [(cx + rx * math.sin(2 * math.pi * i / 48),
                cy + r * math.cos(2 * math.pi * i / 48)) for i in range(49)]
        polyline(pts, 1.1, (90, 96, 104))
    line(cx, cy - r, cx, cy + r, 1.1, (90, 96, 104))
    # marker: Cikande, Banten, Indonesia (east, just below the equator)
    dot(cx + 40, cy + 32, 6.5, RED)
    circle(cx + 40, cy + 32, 12, 2.0, RED)


def compose():
    fill_rect(0, 0, W, H, PAPER)
    rect_outline(12, 12, W - 24, H - 24, 2.4, INK)
    rect_outline(19, 19, W - 38, H - 38, 0.9, INK)
    MX = 40  # content margin

    # --- masthead ---
    draw_text(MX, 32, "THE DAILY SUMMARY", 11.5, FAINT, tracking=2.2, bold=True)
    draw_text_right(W - MX, 32, "ONE PAGE · ALL THE NEWS", 11.5, FAINT, tracking=2.2, bold=True)
    draw_text_centered(W / 2, 50, "THE WORLD IN ONE DAY", 46, INK, tracking=1.0, bold=True)
    fill_rect(MX, 106, W - 2 * MX, 3.2, RED)
    fill_rect(MX, 112, W - 2 * MX, 1.2, INK)

    # --- date bar ---
    fill_rect(MX, 122, W - 2 * MX, 34, INK)
    draw_text(MX + 14, 133, "LATE FINAL EDITION", 12, (214, 206, 188), tracking=1.6, bold=True)
    draw_text_right(W - MX - 14, 133, "EST. 2026", 12, (214, 206, 188), tracking=1.6, bold=True)
    draw_text_centered(W / 2, 130, "TUESDAY, 24 NOVEMBER 2026", 18, (250, 247, 238), tracking=1.2, bold=True)

    # --- lead story ---
    draw_text(MX, 172, "LEAD STORY — INDONESIA", 14, RED, tracking=2.4, bold=True)
    ly = 192
    for ln in wrap(LEAD_HEAD, 36, 612, 0.2):
        draw_text(MX, ly, ln, 36, INK, tracking=0.2, bold=True)
        ly += 45
    sy = ly + 10
    for ln in wrap(LEAD_SUM, 16.5, 612):
        draw_text(MX, sy, ln, 16.5, BODY)
        sy += 22.5
    draw_globe(830, 268, 92)
    draw_text_centered(830, 374, "SEARCH GOES ON IN BANTEN", 11.5, RED, tracking=1.6, bold=True)
    fill_rect(MX, 390, W - 2 * MX, 1.2, INK)

    # --- section strip ---
    draw_text_centered(W / 2, 402, "TEN MORE STORIES FROM AROUND THE WORLD", 13, INK, tracking=2.6, bold=True)

    # --- panel grid: 2 columns x 5 rows ---
    gx, gy = MX, 424
    gw, gh, gapx, gapy = 466, 108, 12, 6
    for i, (tag, col, head, summ) in enumerate(PANELS):
        px = gx + (i % 2) * (gw + gapx)
        py = gy + (i // 2) * (gh + gapy)
        fill_rect(px, py, gw, gh, CARD)
        rect_outline(px, py, gw, gh, 1.1, LINEC)
        fill_rect(px, py, 5, gh, col)
        tx = px + 15
        tw = gw - 27
        draw_text(tx, py + 9, tag, 11, col, tracking=1.8, bold=True)
        hy = py + 26
        for ln in wrap(head, 17, tw, 0.1):
            draw_text(tx, hy, ln, 17, INK, tracking=0.1, bold=True)
            hy += 21.5
        yy = hy + 3
        for ln in wrap(summ, 13.5, tw):
            draw_text(tx, yy, ln, 13.5, BODY)
            yy += 17.5

    # --- footer ---
    draw_text_centered(W / 2, 992, "11 STORIES · FIVE CONTINENTS · ONE DAY — TUESDAY, 24 NOVEMBER 2026",
                       10, FAINT, tracking=1.6, bold=True)


def main():
    compose()
    data = png_bytes(downsample())
    outdir = os.environ.get('MAKEFUN_OUTPUT_DIR', '/output')
    os.makedirs(outdir, exist_ok=True)
    path = os.path.join(outdir, 'entry.png')
    with open(path, 'wb') as fh:
        fh.write(data)
    print('wrote', path, len(data), 'bytes')


if __name__ == '__main__':
    main()
