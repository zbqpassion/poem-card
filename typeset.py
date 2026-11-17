"""Typeset a quatrain onto a text-free plate in the house layout (KingHwa OldSong, two big
columns, gold source column centred on the left column). The drawing is kept as is; if it
comes within GAP_MIN of the text, the whole drawing is shifted right (its right edge bleeds).

Usage:
  python typeset.py raw.png out.png --lines 绿蚁新醅酒 红泥小火炉 晚来天欲雪 能饮一杯无 \
      --title 问刘十九 --dynasty 唐 --author 白居易
Lines 1-2 form the right column, lines 3-4 the left column. --source overrides the
generated 《title》dynasty·author string.
"""
import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).resolve().parent))
import compose_lib as L

# House layout, measured on a 1086x1448 codex plate; scaled by width for other sizes.
REF_W = 1086
TOP = 96                 # top edge of the big characters
INK_H = 57               # ink height of a big character
STEP = 69.6              # big character pitch
BREAK_EXTRA = 64         # extra space between the two lines of a column
SRC_INK_H = 32.4         # ink height of a source character
SRC_STEP = 40.0          # source character pitch
X_RIGHT, X_LEFT, X_SRC = 296.5, 196.5, 106.5
GAP_MIN = 30             # text right edge to drawing left edge
SHIFT_WARN = 80
BOLD = 0.016             # stroke width as a fraction of font size
INK = np.array([18, 18, 16], np.float32)
GOLD = np.array([182, 143, 68], np.float32)


def glyph(ch, size, bold=BOLD):
    scale, p = 4, 6 * 4
    rot = -90 if ch in "《》〈〉" else 0
    ch = "・" if ch == "·" else ch
    font = ImageFont.truetype(L.FONT_PATH, size * scale)
    sw = max(0, round(size * scale * bold))
    x0, y0, x1, y1 = font.getbbox(ch, stroke_width=sw)
    g = Image.new("L", (x1 - x0 + 2 * p, y1 - y0 + 2 * p), 0)
    ImageDraw.Draw(g).text((p - x0, p - y0), ch, font=font, fill=255, stroke_width=sw, stroke_fill=255)
    if rot:
        g = g.rotate(rot, expand=True, resample=Image.Resampling.BICUBIC)
    g = g.resize((max(1, round(g.width / scale)), max(1, round(g.height / scale))), Image.Resampling.LANCZOS)
    return np.asarray(g)


def size_for(ink_h):
    # font size whose "众" has the requested ink height
    s = ink_h
    for _ in range(4):
        rows = np.where(glyph("众", s).max(axis=1) > 128)[0]
        s = s * ink_h / (rows.max() - rows.min() + 1)
    return int(round(s))


def ink_span(foot, axis=1):
    idx = np.where(foot.max(axis=axis) > 128)[0]
    return int(idx.min()), int(idx.max())


def column(rgb, text, size, cx, ys, color):
    foot = np.zeros(rgb.shape[:2], np.uint8)
    for ch, cy in zip(text, ys):
        foot = np.maximum(foot, L.blit(rgb, glyph(ch, size), cx, cy, color))
    return foot


def big_ys(first_line_len, n, k):
    return [(TOP + INK_H / 2 + i * STEP + (BREAK_EXTRA if i >= first_line_len else 0)) * k for i in range(n)]


def typeset(src, out, lines, source):
    rgb = np.asarray(Image.open(src).convert("RGB")).copy()
    H, W = rgb.shape[:2]
    L.W, L.H = W, H
    k = W / REF_W
    right, left = lines[0] + lines[1], lines[2] + lines[3]
    size, ssize = size_for(INK_H * k), size_for(SRC_INK_H * k)
    ys_r, ys_l = big_ys(len(lines[0]), len(right), k), big_ys(len(lines[2]), len(left), k)

    # keep GAP_MIN between the right column and the drawing on the same rows
    foot = column(np.zeros_like(rgb), right, size, X_RIGHT * k, ys_r, INK)
    text_right = int(np.where(foot.max(axis=0) > 0)[0].max())   # include antialiased fringe
    y0, y1 = ink_span(foot)
    art = (rgb.astype(np.float32) @ np.array([0.299, 0.587, 0.114], np.float32)) < 200
    art_left = int(np.where(art[y0:y1 + 1].any(axis=0))[0].min())
    shift = max(0, text_right + round(GAP_MIN * k) - art_left)
    if shift:
        paper = np.median(rgb[H // 7:H * 6 // 7, 5:60].reshape(-1, 3), axis=0).astype(np.uint8)
        moved = np.empty_like(rgb)
        moved[:, :shift] = paper
        moved[:, shift:] = rgb[:, :-shift]
        rgb = moved
    print(f"text right {text_right}, drawing left {art_left}, drawing shifted right {shift}px")
    if shift > SHIFT_WARN * k:
        print("WARN large shift: check the right edge did not cut the subject")

    column(rgb, right, size, X_RIGHT * k, ys_r, INK)
    left_span = ink_span(column(rgb, left, size, X_LEFT * k, ys_l, INK))
    if max(y1, left_span[1]) > H - TOP * k:
        print("WARN text runs into the bottom margin")

    ys_s = [i * SRC_STEP * k for i in range(len(source))]
    a0, a1 = ink_span(column(np.zeros_like(rgb), source, ssize, X_SRC * k, ys_s, GOLD))
    dy = (left_span[0] + left_span[1]) / 2 - (a0 + a1) / 2
    src_span = ink_span(column(rgb, source, ssize, X_SRC * k, [y + dy for y in ys_s], GOLD))

    Image.fromarray(rgb).save(out)
    print(f"big {size}px, left column y {left_span}; source {ssize}px y {src_span} -> {out}")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src", type=Path, help="text-free plate from codex_gen.py")
    ap.add_argument("out", type=Path)
    ap.add_argument("--lines", nargs=4, required=True, help="four lines, no punctuation")
    ap.add_argument("--title")
    ap.add_argument("--dynasty")
    ap.add_argument("--author")
    ap.add_argument("--source", help="override the source column text")
    a = ap.parse_args()
    if a.source:
        source = a.source
    elif a.title and a.dynasty and a.author:
        source = f"《{a.title}》{a.dynasty}·{a.author}"
    else:
        sys.exit("give --source, or all of --title --dynasty --author")
    typeset(a.src, a.out, a.lines, source)


if __name__ == "__main__":
    main()
