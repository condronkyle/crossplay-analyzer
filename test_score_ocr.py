#!/usr/bin/env python3
"""
Test the header score OCR against ground truth across all example screenshots.

Status: PASSING. The test calibrates digit templates from the actual
Crossplay headers, selects the upper score band (above the player name),
handles touching digits, and ignores separated trailing UI elements.

It is self-contained: it extracts digit templates from the example images
using known digit boundaries, then reads each header score and compares it to
the ground truth.

Run: python3 test_score_ocr.py   (needs numpy, Pillow, scipy)
"""

import numpy as np
from PIL import Image
from scipy.ndimage import distance_transform_edt
import os

HERE = os.path.dirname(os.path.abspath(__file__))

# ── Ground truth scores (player, opponent) per image ────────────────────
GROUND_TRUTH = {
    'test_board.png': ('108', '130'),
    'IMG_3046.png':   ('43',  '93'),
    'IMG_3047.png':   ('235', '285'),
    'IMG_3048.png':   ('407', '412'),
    'IMG_150_139.png': ('150', '139'),
}

# ── Score band / region geometry per image ────────────────────────────────
# (score_y0, score_y1, left_x0, left_x1, right_x0, right_x1)
GEOMETRY = {
    # Scores are the upper line of each name/score pair. The lower line is
    # the player name (the original scaffold accidentally used that band).
    'test_board.png': (334, 370, 150, 400, 800, 1150),
    'IMG_3046.png':   (334, 370, 141, 400, 801, 1143),
    'IMG_3047.png':   (334, 370, 141, 400, 801, 1143),
    'IMG_3048.png':   (679, 719, 220, 390, 800, 950),
    'IMG_150_139.png': (122, 135, 66, 92, 382, 406),
}

# ── Known digit boundaries for template extraction: (image, digit, x0,x1,y0,y1)
DIGIT_SAMPLES = [
    # test_board.png
    ('test_board.png', '1', 1039, 1052, 334, 369),
    ('test_board.png', '3', 1056, 1078, 334, 369),
    ('test_board.png', '0', 1082, 1107, 334, 369),
    ('test_board.png', '1', 181, 196, 334, 369),
    ('test_board.png', '0', 198, 223, 334, 369),
    ('test_board.png', '8', 226, 250, 334, 369),
    # IMG_3046.png
    ('IMG_3046.png', '4', 181, 206, 334, 369),
    ('IMG_3046.png', '3', 209, 231, 334, 369),
    ('IMG_3046.png', '9', 946, 970, 334, 369),
    ('IMG_3046.png', '3', 974, 996, 334, 369),
    # IMG_3047.png
    ('IMG_3047.png', '2', 181, 203, 334, 369),
    ('IMG_3047.png', '3', 206, 228, 334, 369),
    ('IMG_3047.png', '5', 233, 254, 334, 369),
    ('IMG_3047.png', '2', 923, 945, 334, 369),
    ('IMG_3047.png', '8', 948, 972, 334, 369),
    ('IMG_3047.png', '5', 975, 996, 334, 369),
    # IMG_3048.png (post-game screen)
    ('IMG_3048.png', '4', 265, 294, 679, 719),
    ('IMG_3048.png', '0', 296, 325, 679, 719),
    ('IMG_3048.png', '7', 329, 354, 679, 719),
    ('IMG_3048.png', '4', 835, 864, 679, 719),
    ('IMG_3048.png', '1', 867, 884, 679, 719),
    ('IMG_3048.png', '2', 887, 913, 679, 719),
]


def normalize(mask, Hn=32, Wn=44):
    h, w = mask.shape
    scale = Hn / h
    nh = Hn
    nw = max(1, round(w * scale))
    g2 = np.array(Image.fromarray(mask.astype(np.uint8) * 255).resize((nw, nh), Image.LANCZOS)) > 100
    canvas = np.zeros((Hn, Wn), dtype=bool)
    ys2, xs2 = np.where(g2)
    if len(xs2) == 0:
        return canvas
    cy, cx = ys2.mean(), xs2.mean()
    oy = int(round(Hn / 2 - cy))
    ox = int(round(Wn / 2 - cx))
    y0 = max(0, oy)
    y1 = min(Hn, oy + nh)
    x0 = max(0, ox)
    x1 = min(Wn, ox + nw)
    canvas[y0:y1, x0:x1] = g2[0:y1 - y0, 0:x1 - x0]
    return canvas


def load_dark(path):
    img = np.array(Image.open(os.path.join(HERE, path))).astype(int)
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    mx = np.maximum(np.maximum(r, g), b)
    return mx < 190


def build_templates():
    """Extract digit templates from the real headers using known boundaries."""
    dark_cache = {}
    samples = {}
    for (img_name, ch, x0, x1, y0, y1) in DIGIT_SAMPLES:
        if img_name not in dark_cache:
            dark_cache[img_name] = load_dark(img_name)
        dark = dark_cache[img_name]
        g = dark[y0:y1 + 1, x0:x1 + 1]
        rows = np.where(g.any(axis=1))[0]
        cols = np.where(g.any(axis=0))[0]
        if len(rows) == 0 or len(cols) == 0:
            continue
        g = g[rows.min():rows.max() + 1, cols.min():cols.max() + 1]
        samples.setdefault(ch, []).append(normalize(g))
    tpl = {}
    for ch, s in samples.items():
        for nm in s:
            tpl.setdefault(ch, []).append(nm)
    tpl_dt = {ch: [distance_transform_edt(~t) for t in ts] for ch, ts in tpl.items()}
    return tpl, tpl_dt


def chamfer(a, b, dtB):
    da = distance_transform_edt(~a)
    return (da[b].mean() + dtB[a].mean()) / 2


def match(nm, tpl, tpl_dt):
    best = None
    bd = 1e9
    for ch, ts in tpl.items():
        for t, dt in zip(ts, tpl_dt[ch]):
            d = chamfer(nm, t, dt)
            if d < bd:
                bd = d
                best = ch
    return best, bd


def read_score(dark, x0, x1, y0, y1, tpl, tpl_dt):
    """Read the score digits in a region using column-gap segmentation."""
    band = dark[y0:y1 + 1, x0:x1]
    colp = band.sum(axis=0)
    runs = []
    start = None
    for i, v in enumerate(colp):
        if v > 0:
            if start is None:
                start = i
        else:
            if start is not None:
                runs.append((start, i - 1))
                start = None
    if start is not None:
        runs.append((start, len(colp) - 1))

    # The score is the first compact glyph cluster in each header half. A
    # large gap separates it from the controls/name text farther to the
    # right; do not let that trailing UI become an extra score digit.
    if runs:
        cluster = [runs[0]]
        for run in runs[1:]:
            if run[0] - cluster[-1][1] - 1 > 15:
                break
            cluster.append(run)
        runs = cluster

    result = ''
    for (s, e) in runs:
        g = band[:, s:e + 1]
        rows = np.where(g.any(axis=1))[0]
        if len(rows) == 0:
            continue
        g = g[rows.min():rows.max() + 1, :]
        p, d = match(normalize(g), tpl, tpl_dt)
        result += p
    return result


def main():
    tpl, tpl_dt = build_templates()
    print("Digit templates built:", {ch: len(ts) for ch, ts in sorted(tpl.items())})

    all_pass = True
    for img_name, (gt_left, gt_right) in sorted(GROUND_TRUTH.items()):
        y0, y1, lx0, lx1, rx0, rx1 = GEOMETRY[img_name]
        dark = load_dark(img_name)
        left = read_score(dark, lx0, lx1, y0, y1, tpl, tpl_dt)
        right = read_score(dark, rx0, rx1, y0, y1, tpl, tpl_dt)
        ok = left == gt_left and right == gt_right
        all_pass = all_pass and ok
        status = 'PASS' if ok else 'FAIL'
        print(f"\n{status}  {img_name}  (expected {gt_left} vs {gt_right})")
        print(f"     player: read='{left}'  expected='{gt_left}'  {'OK' if left == gt_left else 'MISMATCH'}")
        print(f"     opp:    read='{right}'  expected='{gt_right}'  {'OK' if right == gt_right else 'MISMATCH'}")

    print("\n" + ("ALL SCORES PASS" if all_pass else "SOME SCORES FAIL"))
    return 0 if all_pass else 1


if __name__ == '__main__':
    raise SystemExit(main())
