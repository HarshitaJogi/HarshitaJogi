"""
Builds the profile README's images: the marked-up header and one title strip per entry,
each in a light and a dark version (GitHub picks one with <picture>).

Text is shaped with HarfBuzz and written out as outlines, so it looks the same everywhere
and nothing has to load. Run from the repo root:  python3 tools/build.py
Needs: pip install uharfbuzz fonttools
"""

import math
import random
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"
W = 880

THEMES = {
    "light": {"ink": "#1f2328", "muted": "#59636e", "rule": "#d1d9e0", "pen": "#d9372b"},
    "dark": {"ink": "#e6edf3", "muted": "#9198a1", "rule": "#3d444d", "pen": "#ff6b5e"},
}


class Face:
    def __init__(self, file: str, **axes: float):
        face = hb.Face(hb.Blob.from_file_path(str(FONTS / file)))
        self.upem = face.upem
        self.font = hb.Font(face)
        self.font.set_variations(axes)

    def run(self, text: str, size: float):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf, {"kern": True, "liga": True})
        k = size / self.upem
        return buf.glyph_infos, buf.glyph_positions, k

    def width(self, text: str, size: float) -> float:
        _, pos, k = self.run(text, size)
        return sum(p.x_advance for p in pos) * k

    def path(self, text: str, size: float, x: float, y: float, anchor: str = "start") -> str:
        """Outline of `text` with its baseline starting at (x, y)."""
        infos, pos, k = self.run(text, size)
        if anchor != "start":
            w = sum(p.x_advance for p in pos) * k
            x -= w if anchor == "end" else w / 2
        pen = SVGPathPen(None, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        pen_x = x
        for info, p in zip(infos, pos):
            gx, gy = pen_x + p.x_offset * k, y - p.y_offset * k
            self.font.draw_glyph_with_pen(info.codepoint, TransformPen(pen, (k, 0, 0, -k, gx, gy)))
            pen_x += p.x_advance * k
        return pen.getCommands()


DISPLAY = Face("Newsreader.ttf", wght=420, opsz=72)
NAME = Face("Newsreader.ttf", wght=520, opsz=60)
TEXT_ITALIC = Face("Newsreader-Italic.ttf", wght=400, opsz=16)
PEN = Face("Caveat.ttf", wght=620)
XH = 852 / 2000  # Newsreader x-height, in em


def n(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- the red pen


def stroke(rng: random.Random, x0: float, y0: float, x1: float, y1: float, bow: float = 2.0) -> str:
    """One quick, slightly bowed pen line: the kind you make without a ruler."""
    mx, my = (x0 + x1) / 2 + rng.uniform(-3, 3), (y0 + y1) / 2 + rng.uniform(-bow, bow)
    return f"M{n(x0)} {n(y0)}Q{n(mx)} {n(my)} {n(x1)} {n(y1)}"


def loop(rng: random.Random, cx: float, cy: float, rx: float, ry: float) -> str:
    """A hand circle: one pass that overshoots its start, so it never quite closes."""
    pts = []
    turns = 1.12
    steps = 40
    start = -2.6
    for i in range(steps + 1):
        t = start + (i / steps) * turns * math.tau
        wob = 1 + 0.035 * rng.uniform(-1, 1)
        drift = i / steps * 3
        pts.append((cx + rx * wob * math.cos(t) + drift, cy + ry * wob * math.sin(t) - drift * 0.4))
    d = f"M{n(pts[0][0])} {n(pts[0][1])}"
    for (ax, ay), (bx, by) in zip(pts[1::2], pts[2::2]):
        d += f"Q{n(ax)} {n(ay)} {n(bx)} {n(by)}"
    return d


def check(x: float, y: float, s: float = 1.0) -> str:
    return f"M{n(x)} {n(y - 9 * s)}Q{n(x + 4 * s)} {n(y - 4 * s)} {n(x + 7 * s)} {n(y)}Q{n(x + 12 * s)} {n(y - 14 * s)} {n(x + 22 * s)} {n(y - 22 * s)}"


def svg(w: float, h: float, body: str, style: str = "", title: str = "") -> str:
    title = escape(title, {'"': "&quot;"})
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{n(w)}" height="{n(h)}" viewBox="0 0 {n(w)} {n(h)}" role="img"'
        f' aria-label="{title}"><title>{title}</title>'
        + (f"<style>{style}</style>" if style else "")
        + body
        + "</svg>\n"
    )


# ---------------------------------------------------------------- the header

HERO_TITLE = "Harshita Jogi. AI writes the code, corrected by hand to: AI writes the first draft. I make it right."

HERO_STYLE = """
.a{animation:in .6s ease-out .15s both}
.strike{stroke-dasharray:1;animation:draw .32s cubic-bezier(.6,0,.4,1) .95s both}
.wipe{transform-box:fill-box;transform-origin:0 50%;animation:wipe .75s cubic-bezier(.4,0,.3,1) 1.3s both}
.b{animation:in .6s ease-out 2.15s both}
.under{stroke-dasharray:1;animation:draw .38s cubic-bezier(.6,0,.4,1) 2.75s both}
@keyframes in{from{opacity:0;transform:translateY(6px)}}
@keyframes draw{from{stroke-dashoffset:1}}
@keyframes wipe{from{transform:scaleX(0)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def hero(c: dict) -> str:
    rng = random.Random(7)
    L, R = 0, W
    H = 268
    out = []

    # byline
    out.append(f'<path fill="{c["ink"]}" d="{NAME.path("Harshita Jogi", 27, L, 40)}"/>')
    out.append(f'<path fill="{c["muted"]}" d="{TEXT_ITALIC.path("Software engineer, Sunnyvale CA", 16.5, R, 39, "end")}"/>')
    out.append(f'<path d="M{L} 60.5H{R}" stroke="{c["rule"]}" stroke-width="1"/>')

    # line one: the draft, and the pen's correction
    size, y1, y2 = 40, 170, 228
    lead = "AI writes the "
    x_code = L + DISPLAY.width(lead, size)
    w_code = DISPLAY.width("code", size)
    out.append(f'<g class="a"><path fill="{c["ink"]}" d="{DISPLAY.path(lead + "code.", size, L, y1)}"/></g>')
    sy = y1 - XH * size * 0.52
    out.append(
        f'<path class="strike" pathLength="1" d="{stroke(rng, x_code - 5, sy + 2, x_code + w_code + 1, sy - 2)}" stroke="{c["pen"]}" stroke-width="3.6" stroke-linecap="round" fill="none"/>'
    )
    pen_size = 39
    fx = x_code - 14
    fy = y1 - 44
    fw = PEN.width("first draft", pen_size)
    out.append(
        f'<clipPath id="w"><rect class="wipe" x="{n(fx - 6)}" y="{n(fy - 46)}" width="{n(fw + 16)}" height="64"/></clipPath>'
        f'<g clip-path="url(#w)"><path transform="rotate(-3.5 {n(fx)} {n(fy)})" fill="{c["pen"]}" d="{PEN.path("first draft", pen_size, fx, fy)}"/></g>'
    )

    # line two, underlined by the same pen
    lead2 = "I make it "
    x_r = L + DISPLAY.width(lead2, size)
    w_r = DISPLAY.width("right", size)
    out.append(f'<g class="b"><path fill="{c["ink"]}" d="{DISPLAY.path(lead2 + "right.", size, L, y2)}"/></g>')
    uy = y2 + 13
    out.append(
        f'<path class="under" pathLength="1" d="M{n(x_r - 3)} {n(uy + 1)}Q{n(x_r + w_r * 0.55)} {n(uy - 3)} {n(x_r + w_r + 12)} {n(uy - 4)}" stroke="{c["pen"]}" stroke-width="3.4" stroke-linecap="round" fill="none"/>'
    )
    return svg(W, H, "".join(out), HERO_STYLE, HERO_TITLE)


# ---------------------------------------------------------------- the entries


ENTRIES = [
    {
        "id": "nokia",
        "name": "Nokia",
        "meta": "Software Engineer Co-op, Test Automation & AI Tooling · Sunnyvale · May 2026 to now",
        "note": ("check", "human review gates"),
    },
    {
        "id": "bitgig",
        "name": "Bitgig",
        "meta": "Berkeley × DeepMind Hackathon · September 2026",
        "note": ("plain", "experts fix drafts, not footage"),
    },
    {
        "id": "nsi",
        "name": "Network Science Institute",
        "meta": "Research Assistant, NIH-funded BioToolKB · Northeastern · 2025 to 2026",
        "note": ("swap", "60%", "98%"),
    },
    {
        "id": "trybud",
        "name": "TryBud",
        "meta": "Harvard Hack-o-Ween · October 2025",
        "note": ("loop", "2nd place"),
    },
    {
        "id": "msci",
        "name": "MSCI",
        "meta": "Technology Analyst · Mumbai · January 2024 to August 2025",
        "note": ("swap", "Azure", "GCP"),
    },
    {
        "id": "drone",
        "name": "Drone research",
        "meta": "Research Lead, IEEE AESS funded, $25,000 grant · 2023",
        "note": ("plain", "2 IEEE papers, 1 patent filed"),
    },
    {
        "id": "next",
        "name": "Next",
        "meta": "A full-time software engineering role, from 2027",
        "note": ("plain", "your team?"),
    },
]

EH = 84  # air above the rule, then the name; the role and dates are real text in the README


def note(c: dict, kind: tuple, right: float, base: float, rng: random.Random) -> tuple[str, float]:
    """The red margin note, right-aligned at `right`. Returns the markup and its left edge."""
    size = 27
    pen = c["pen"]
    line = f'stroke="{pen}" stroke-linecap="round" stroke-linejoin="round" fill="none"'
    if kind[0] == "plain":
        w = PEN.width(kind[1], size)
        return f'<path fill="{pen}" d="{PEN.path(kind[1], size, right, base, "end")}"/>', right - w
    if kind[0] == "check":
        w = PEN.width(kind[1], size)
        x = right - w
        return (
            f'<path fill="{pen}" d="{PEN.path(kind[1], size, right, base, "end")}"/>'
            f'<path d="{check(x - 32, base - 2, 0.95)}" {line} stroke-width="3"/>'
        ), x - 34
    if kind[0] == "loop":
        w = PEN.width(kind[1], size)
        x = right - w - 6
        return (
            f'<path fill="{pen}" d="{PEN.path(kind[1], size, right - 6, base, "end")}"/>'
            f'<path d="{loop(rng, x + w / 2 - 1, base - 9, w / 2 + 12, 19)}" {line} stroke-width="2.6"/>'
        ), x - 14
    # swap: the old value struck through, the new one circled
    old, new = kind[1], kind[2]
    w_new = PEN.width(new, size)
    w_old = PEN.width(old, size)
    x_new = right - w_new - 8
    x_old = x_new - 26 - w_old
    sy = base - 9
    return (
        f'<path fill="{pen}" d="{PEN.path(old, size, x_old, base)}"/>'
        f'<path d="{stroke(rng, x_old - 4, sy + 3, x_old + w_old + 4, sy - 3, 1.2)}" {line} stroke-width="3"/>'
        f'<path fill="{pen}" d="{PEN.path(new, size, x_new, base)}"/>'
        f'<path d="{loop(rng, x_new + w_new / 2, base - 9, w_new / 2 + 11, 19)}" {line} stroke-width="2.6"/>'
    ), x_old - 6


def entry(c: dict, e: dict) -> str:
    rng = random.Random(e["id"])
    out = [f'<path d="M0 22.5H{W}" stroke="{c["rule"]}" stroke-width="1"/>']
    name_w = NAME.width(e["name"], 28)
    out.append(f'<path fill="{c["ink"]}" d="{NAME.path(e["name"], 28, 0, 70)}"/>')
    base = 68
    mark, left = note(c, e["note"], W - 6, base, rng)
    # tilt the note like a quick margin scribble
    out.append(f'<g transform="rotate(-2.5 {W - 6} {base})">{mark}</g>')
    assert left > name_w + 30, f"{e['id']}: the margin note runs into the name"
    return svg(W, EH, "".join(out), title=f"{e['name']}. {e['meta']}")


def main():
    OUT.mkdir(exist_ok=True)
    for theme, c in THEMES.items():
        (OUT / f"header-{theme}.svg").write_text(hero(c))
        for e in ENTRIES:
            (OUT / f"{e['id']}-{theme}.svg").write_text(entry(c, e))
    sizes = sorted((p.name, p.stat().st_size) for p in OUT.glob("*.svg"))
    for name, size in sizes:
        print(f"{name:24} {size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
