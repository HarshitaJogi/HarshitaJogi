"""
Builds the profile README's one image: a timeline of the work, in four lanes, in a light
and a dark version (GitHub picks one with <picture>).

Text is shaped with HarfBuzz and written out as outlines, so it looks the same everywhere
and nothing has to load. Run from the repo root:  python3 tools/build.py
Needs: pip install uharfbuzz fonttools
"""

from dataclasses import dataclass, field
from pathlib import Path
from xml.sax.saxutils import escape

import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "tools" / "fonts"
OUT = ROOT / "assets"

# today, as a year fraction: where the "now" line sits. Move it when you rebuild.
NOW = 2026 + 9.5 / 12


class Face:
    def __init__(self, file: str, **axes: float):
        face = hb.Face(hb.Blob.from_file_path(str(FONTS / file)))
        self.upem = face.upem
        self.font = hb.Font(face)
        self.font.set_variations(axes)

    def _run(self, text: str, size: float):
        buf = hb.Buffer()
        buf.add_str(text)
        buf.guess_segment_properties()
        hb.shape(self.font, buf, {"kern": True, "liga": True})
        return buf.glyph_infos, buf.glyph_positions, size / self.upem

    def width(self, text: str, size: float) -> float:
        _, pos, k = self._run(text, size)
        return sum(p.x_advance for p in pos) * k

    def text(self, text: str, size: float, x: float, y: float, attrs: str = "", anchor: str = "start") -> str:
        """`text` with its baseline starting at (x, y), as uses of glyphs outlined once in DEFS."""
        infos, pos, k = self._run(text, size)
        if anchor != "start":
            w = self.width(text, size)
            x -= w if anchor == "end" else w / 2
        uses = []
        for info, p in zip(infos, pos):
            key = (id(self), info.codepoint, size)
            if key not in DEFS:
                pen = SVGPathPen(None, ntos=lambda v: f"{v:.2f}".rstrip("0").rstrip("."))
                self.font.draw_glyph_with_pen(info.codepoint, TransformPen(pen, (k, 0, 0, -k, 0, 0)))
                DEFS[key] = (f"g{len(DEFS)}", pen.getCommands())
            gid, d = DEFS[key]
            if d:
                uses.append(f'<use href="#{gid}" x="{n(x + p.x_offset * k)}" y="{n(y - p.y_offset * k)}"/>')
            x += p.x_advance * k
        return f"<g {attrs}>{''.join(uses)}</g>"


DEFS: dict[tuple, tuple[str, str]] = {}


def defs() -> str:
    return "<defs>" + "".join(f'<path id="{gid}" d="{d}"/>' for gid, d in DEFS.values() if d) + "</defs>"


NAME = Face("BricolageGrotesque.ttf", wght=640, wdth=88, opsz=48)
BOLD = Face("Geist.ttf", wght=600)
TEXT = Face("Geist.ttf", wght=420)
NUM = Face("GeistMono.ttf", wght=420)


def n(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- the work


@dataclass
class Item:
    name: str
    line: str
    start: float
    end: float | None = None  # None: a single moment, drawn as a dot
    live: bool = False  # still going: the bar ends in a pulse at "now"
    future: bool = False  # not yet: a dashed outline
    since: str | None = None  # began before the chart does: say when, and fade the bar in


@dataclass
class Lane:
    name: str
    hue: str
    items: list[Item] = field(default_factory=list)


def ym(year: int, month: int) -> float:
    return year + (month - 1) / 12


LANES = [
    Lane("Industry", "blue", [
        Item("MSCI", "Technology analyst, Azure to GCP", ym(2024, 1), ym(2025, 9)),
        Item("Nokia", "SWE co-op, LLM agents", ym(2026, 5), NOW, live=True),
        Item("Full-time", "from 2027", ym(2027, 7), ym(2028, 1), future=True),
    ]),
    Lane("Research", "teal", [
        Item("Drone research", "IEEE grant, 2 papers", ym(2023, 7), ym(2024, 1)),
        Item("Network Science Institute", "GPT-4.1 on 1M+ papers", ym(2025, 7), ym(2026, 8)),
    ]),
    Lane("Hackathons", "coral", [
        Item("TryBud", "2nd at Harvard", ym(2025, 10)),
        Item("Bitgig", "Berkeley × DeepMind", ym(2026, 9)),
    ]),
    Lane("Education", "amber", [
        Item("University of Mumbai", "BE Electronics", ym(2023, 1), ym(2024, 6), since="2020"),
        Item("Northeastern", "MS Computer Science", ym(2025, 9), ym(2027, 6)),
    ]),
]

THEMES = {
    "light": {
        "bg": "#ffffff", "ink": "#1f2328", "muted": "#59636e", "faint": "#d8dee4", "grid": "#eef1f4",
        "blue": "#3b63e0", "teal": "#0f9a84", "coral": "#e5533d", "amber": "#c98a06",
    },
    "dark": {
        "bg": "#0d1117", "ink": "#e6edf3", "muted": "#9198a1", "faint": "#3d444d", "grid": "#1c222a",
        "blue": "#7c9cff", "teal": "#3fd1b5", "coral": "#ff8a75", "amber": "#f2c14e",
    },
}

# ---------------------------------------------------------------- layout

W = 880
X0, X1 = 128, 866  # the plot
Y_FROM, Y_TO = 2023.0, 2028.0
TOP = 112  # first lane
LANE_H = 70
NAME_PX, LINE_PX = 15.5, 13.5


def x_of(t: float) -> float:
    return X0 + (t - Y_FROM) / (Y_TO - Y_FROM) * (X1 - X0)


STYLE = """
.bar{transform-box:fill-box;transform-origin:0 50%;animation:grow .7s cubic-bezier(.3,.7,.2,1) both}
.lab{animation:fade .5s ease-out both}
.pulse{transform-box:fill-box;transform-origin:50% 50%;animation:pulse 2.4s ease-out 1.6s infinite}
@keyframes grow{from{transform:scaleX(0)}}
@keyframes fade{from{opacity:0;transform:translateY(4px)}}
@keyframes pulse{0%{transform:scale(1);opacity:.55}70%,100%{transform:scale(3.2);opacity:0}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}.pulse{display:none}}
"""


def timeline(c: dict) -> str:
    DEFS.clear()
    out: list[str] = []
    halo = f'fill="{c["bg"]}" stroke="{c["bg"]}" stroke-width="5" stroke-linejoin="round"'

    # who
    out.append(NAME.text("Harshita Jogi", 38, 0, 44, f'fill="{c["ink"]}"'))
    out.append(TEXT.text("Software engineer · Sunnyvale, CA", 15, W, 42, f'fill="{c["muted"]}"', "end"))
    out.append(f'<path d="M0 66.5H{W}" stroke="{c["faint"]}" stroke-width="1"/>')

    bottom = TOP + LANE_H * len(LANES)
    # the years, as faint columns
    for year in range(int(Y_FROM), int(Y_TO) + 1):
        x = x_of(year)
        out.append(f'<path d="M{n(x)} {TOP - 18}V{bottom - 6}" stroke="{c["grid"]}" stroke-width="1"/>')
        out.append(NUM.text(str(year), 12, x, bottom + 14, f'fill="{c["muted"]}"', "middle"))

    # now
    xn = x_of(NOW)
    out.append(f'<path d="M{n(xn)} {TOP - 22}V{bottom - 6}" stroke="{c["muted"]}" stroke-width="1" stroke-dasharray="2 4"/>')
    out.append(NUM.text("now", 12, xn, TOP - 28, f'fill="{c["muted"]}"', "middle"))

    delay = 0.2
    for i, lane in enumerate(LANES):
        hue = c[lane.hue]
        y = TOP + i * LANE_H  # top of the lane's labels
        bar_y = y + 38
        out.append(BOLD.text(lane.name, 13, 0, bar_y + 4, f'fill="{hue}"'))
        right_edge = -1.0
        for it in lane.items:
            xs = x_of(it.start)
            label_x = xs
            name_w = BOLD.width(it.name, NAME_PX)
            line_text = it.line if not it.since else f"{it.line}, {it.since} to 2024"
            line_w = TEXT.width(line_text, LINE_PX)
            assert label_x > right_edge + 14, f"{lane.name}: {it.name} runs into the item before it"
            right_edge = label_x + max(name_w, line_w)
            assert right_edge < W, f"{it.name} runs off the right edge"

            ink = c["muted"] if it.future else c["ink"]
            out.append(
                f'<g class="lab" style="animation-delay:{delay + 0.25:.2f}s">'
                # the halo first, then the letters: it keeps the "now" line off the text
                + BOLD.text(it.name, NAME_PX, label_x, y + 12, halo)
                + TEXT.text(line_text, LINE_PX, label_x, y + 29, halo)
                + BOLD.text(it.name, NAME_PX, label_x, y + 12, f'fill="{ink}"')
                + TEXT.text(line_text, LINE_PX, label_x, y + 29, f'fill="{c["muted"]}"')
                + "</g>"
            )
            if it.end is None:  # a moment
                out.append(f'<circle class="lab" style="animation-delay:{delay:.2f}s" cx="{n(xs + 5)}" cy="{bar_y}" r="5" fill="{hue}"/>')
            elif it.future:
                xe = x_of(it.end)
                out.append(
                    f'<rect class="bar" style="animation-delay:{delay:.2f}s" x="{n(xs)}" y="{bar_y - 4}" width="{n(xe - xs)}" height="8" rx="4"'
                    f' fill="none" stroke="{hue}" stroke-width="1.5" stroke-dasharray="4 4"/>'
                )
            else:
                xe = x_of(it.end)
                fill = hue
                if it.since:  # it began off the left edge: fade it in
                    gid = f"fade{i}"
                    out.append(f'<linearGradient id="{gid}" x1="0" x2="1"><stop offset="0" stop-color="{hue}" stop-opacity="0"/><stop offset=".35" stop-color="{hue}"/></linearGradient>')
                    fill = f"url(#{gid})"
                out.append(f'<rect class="bar" style="animation-delay:{delay:.2f}s" x="{n(xs)}" y="{bar_y - 4}" width="{n(xe - xs)}" height="8" rx="4" fill="{fill}"/>')
                if it.live:
                    out.append(f'<circle class="pulse" cx="{n(xe - 4)}" cy="{bar_y}" r="4" fill="{hue}"/>')
                    out.append(f'<circle cx="{n(xe - 4)}" cy="{bar_y}" r="4" fill="{hue}" stroke="{c["bg"]}" stroke-width="2"/>')
            delay += 0.12

    h = bottom + 24
    title = "Harshita Jogi, software engineer in Sunnyvale, CA. Timeline: " + "; ".join(
        f"{lane.name}: " + ", ".join(f"{it.name} ({it.line})" for it in lane.items) for lane in LANES
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{escape(title, {chr(34): "&quot;"})}">'
        f"<title>{escape(title)}</title><style>{STYLE}</style>" + defs() + "".join(out) + "</svg>\n"
    )


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    for theme, c in THEMES.items():
        f = OUT / f"timeline-{theme}.svg"
        f.write_text(timeline(c))
        print(f"{f.name:22} {f.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
