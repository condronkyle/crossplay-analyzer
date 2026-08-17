#!/usr/bin/env python3
"""
Test the grid detection algorithm against ground truth.
Ports the JS detectBoardGrid logic to Python for offline testing.
"""

import sys
import numpy as np
from PIL import Image

# Ground truth for test_board.png (https://i.imgur.com/qworrOn.png)
# Verified against parse_board_cv.py output (96% width prior with python CV)
GROUND_TRUTH = {
    # (row, col): letter  — 0-indexed
    (3, 6): 'V', (3, 7): 'A', (3, 8): 'T', (3, 13): 'W',
    (4, 7): 'M', (4, 8): 'A', (4, 9): 'C', (4, 10): 'H',
    (4, 11): 'I', (4, 12): 'N', (4, 13): 'E', (4, 14): 'S',
    (5, 10): 'E', (5, 14): 'O',
    (6, 10): 'X', (6, 14): 'B',
    (7, 6): 'G', (7, 7): 'O', (7, 8): 'O', (7, 9): 'N',
    (7, 10): 'E', (7, 11): 'Y', (7, 14): 'E',
    (8, 8): 'P', (8, 9): 'U', (8, 10): 'R', (8, 11): 'E', (8, 14): 'R',
    (9, 14): 'I', (10, 14): 'N', (11, 14): 'G',
}
# Total: 31 tiles (Python CV found 31; W at N4 makes 32 — verify)


def rgb_to_hsv(r, g, b):
    """OpenCV convention: H=[0,179], S=[0,255], V=[0,255]."""
    r, g, b = r / 255.0, g / 255.0, b / 255.0
    mx = max(r, g, b)
    mn = min(r, g, b)
    d = mx - mn
    v = round(mx * 255)
    s = round((d / mx) * 255) if mx != 0 else 0
    if d == 0:
        h = 0
    elif mx == r:
        h = ((g - b) / d + (6 if g < b else 0)) * 30
    elif mx == g:
        h = ((b - r) / d + 2) * 30
    else:
        h = ((r - g) / d + 4) * 30
    return round(h), s, v


def is_blue_hsv(h, s, v):
    return 95 <= h <= 135 and s >= 80 and v >= 80


def detect_board_grid(pixels, width, height):
    """Port of JS detectBoardGrid — 96% width prior (matches Python CV reference)."""
    BOARD_WIDTH_FRAC = 0.96
    cell_w = width * BOARD_WIDTH_FRAC / 15
    cell_h = cell_w
    grid_left = (width - 15 * cell_w) / 2

    search_top = int(height * 0.30)
    search_bottom = int(height * 0.70)

    y_profile = np.zeros(search_bottom - search_top, dtype=np.float64)
    for y in range(search_top, search_bottom):
        row_blue = 0
        for x in range(width):
            r, g, b = pixels[y, x, 0], pixels[y, x, 1], pixels[y, x, 2]
            h, s, v = rgb_to_hsv(r, g, b)
            if 95 <= h <= 135 and s >= 80 and v >= 80:
                row_blue += 1
        y_profile[y - search_top] = row_blue

    print(f"  cellW={cell_w:.1f}, gridLeft={grid_left:.1f}")

    tile_row_thresh = width * 0.10
    first_tile_y = -1
    for i in range(len(y_profile)):
        if y_profile[i] > tile_row_thresh:
            first_tile_y = i + search_top
            break

    if first_tile_y < 0:
        print("ERROR: No tile rows found")
        return None

    # Anchor to expectedBoardTop (~29% of height, matching Python CV reference)
    expected_board_top = height * 0.29
    grid_top_min = height * 0.10
    grid_top_max = height * 0.40
    best_grid_top = None
    best_dist = float('inf')

    for offset in range(15):
        grid_top = first_tile_y - offset * cell_h
        if grid_top < grid_top_min or grid_top > grid_top_max:
            continue
        dist = abs(grid_top - expected_board_top)
        if dist < best_dist:
            best_dist = dist
            best_grid_top = grid_top

    if best_grid_top is None:
        best_grid_top = expected_board_top

    h_grid = [max(0, min(height - 1, round(best_grid_top + i * cell_h))) for i in range(16)]
    v_grid = [max(0, min(width - 1, round(grid_left + i * cell_w))) for i in range(16)]

    print(f"  cellW={cell_w:.1f}, gridLeft={grid_left:.1f}, gridTop={best_grid_top:.1f}")
    print(f"  Grid spans {v_grid[0]}-{v_grid[15]} x {h_grid[0]}-{h_grid[15]}")
    print(f"  Board width = {15*cell_w:.0f}px = {15*cell_w/width*100:.1f}% of image")

    return h_grid, v_grid, cell_w, cell_h


def is_tile_cell(pixels, width, x1, y1, x2, y2):
    """Check if a cell contains a blue tile."""
    margin_x = max(2, round((x2 - x1) * 0.08))
    margin_y = max(2, round((y2 - y1) * 0.08))
    sx1, sy1 = x1 + margin_x, y1 + margin_y
    sx2, sy2 = x2 - margin_x, y2 - margin_y
    if sx2 <= sx1 or sy2 <= sy1:
        return False

    cell_w = sx2 - sx1
    cell_h = sy2 - sy1
    blue_count = 0
    total_count = 0

    for y in range(sy1, sy2):
        for x in range(sx1, sx2):
            r, g, b = pixels[y, x, 0], pixels[y, x, 1], pixels[y, x, 2]
            h, s, v = rgb_to_hsv(r, g, b)
            total_count += 1
            if is_blue_hsv(h, s, v):
                blue_count += 1

    blue_ratio = blue_count / total_count if total_count > 0 else 0
    if blue_ratio <= 0.25:
        return False

    # Check blue width span
    dense_col_count = 0
    for c in range(cell_w):
        col_blue = 0
        for y in range(sy1, sy2):
            r, g, b = pixels[y, sx1 + c, 0], pixels[y, sx1 + c, 1], pixels[y, sx1 + c, 2]
            h, s, v = rgb_to_hsv(r, g, b)
            if is_blue_hsv(h, s, v):
                col_blue += 1
        if col_blue > cell_h * 0.10:
            dense_col_count += 1

    return (dense_col_count / cell_w) >= 0.35


def test_grid_detection(image_path):
    """Run grid detection and compare to ground truth."""
    print(f"\n=== Testing: {image_path} ===")
    img = Image.open(image_path)
    pixels = np.array(img)
    height, width = pixels.shape[:2]
    print(f"Image: {width}x{height}")

    result = detect_board_grid(pixels, width, height)
    if result is None:
        print("FAIL: Grid detection returned None")
        return False

    h_grid, v_grid, cell_w, cell_h = result

    # Detect tiles
    print("\n  Detecting tiles...")
    detected = set()
    for row in range(15):
        for col in range(15):
            y1, y2 = h_grid[row], h_grid[row + 1]
            x1, x2 = v_grid[col], v_grid[col + 1]
            if is_tile_cell(pixels, width, x1, y1, x2, y2):
                detected.add((row, col))

    gt_positions = set(GROUND_TRUTH.keys())

    # Compare
    correct = detected & gt_positions
    missed = gt_positions - detected
    extra = detected - gt_positions

    print(f"\n  Results:")
    print(f"    Ground truth: {len(gt_positions)} tiles")
    print(f"    Detected:     {len(detected)} tiles")
    print(f"    Correct:      {len(correct)}/{len(gt_positions)}")

    if missed:
        print(f"    Missed ({len(missed)}):")
        for r, c in sorted(missed):
            label = f"{r+1}{chr(65+c)}"
            print(f"      {label} ({GROUND_TRUTH[(r,c)]})")

    if extra:
        print(f"    Extra ({len(extra)}):")
        for r, c in sorted(extra):
            label = f"{r+1}{chr(65+c)}"
            print(f"      {label}")

    # Show detected positions with labels
    det_labels = sorted([f"{r+1}{chr(65+c)}" for r, c in detected])
    gt_labels = sorted([f"{r+1}{chr(65+c)}" for r, c in gt_positions])
    print(f"\n    Detected: {', '.join(det_labels)}")
    print(f"    Expected: {', '.join(gt_labels)}")

    success = len(correct) == len(gt_positions) and len(extra) == 0
    print(f"\n  {'PASS' if success else 'FAIL'}: {len(correct)}/{len(gt_positions)} correct, {len(extra)} extra")

    # Generate mosaic for visual inspection
    if success or '--mosaic' in sys.argv:
        build_test_mosaic(img, h_grid, v_grid, detected, image_path)

    return success


def build_test_mosaic(img, h_grid, v_grid, detected, image_path):
    """Build a mosaic image matching the JS buildTileMosaic layout."""
    cell_size = 100
    label_height = 28
    padding = 6
    cols_per_row = 8

    tile_positions = sorted(detected)
    n_tiles = len(tile_positions)
    n_rows = (n_tiles + cols_per_row - 1) // cols_per_row

    mosaic_w = cols_per_row * (cell_size + padding) + padding
    mosaic_h = n_rows * (cell_size + padding + label_height) + padding

    mosaic = Image.new('RGB', (mosaic_w, mosaic_h), (0, 0, 0))
    from PIL import ImageDraw, ImageFont
    draw = ImageDraw.Draw(mosaic)

    for idx, (row, col) in enumerate(tile_positions):
        grid_r = idx // cols_per_row
        grid_c = idx % cols_per_row
        dx = grid_c * (cell_size + padding) + padding
        dy = grid_r * (cell_size + padding + label_height) + padding

        label = f"{row + 1}{chr(65 + col)}"

        # Label background + text
        draw.rectangle([dx, dy, dx + cell_size, dy + label_height], fill=(34, 34, 34))
        draw.text((dx + cell_size // 2, dy + 2), label, fill=(255, 255, 0), anchor='mt')

        # Crop tile from source
        y1, y2 = h_grid[row], h_grid[row + 1]
        x1, x2 = v_grid[col], v_grid[col + 1]
        tile_crop = img.crop((x1, y1, x2, y2)).resize((cell_size, cell_size))
        mosaic.paste(tile_crop, (dx, dy + label_height))

        # Superscript mask (matching JS: top-right 35% x 28%)
        mask_x = dx + int(cell_size * 0.65)
        mask_y = dy + label_height
        mask_w = int(cell_size * 0.35)
        mask_h = int(cell_size * 0.28)
        draw.rectangle([mask_x, mask_y, mask_x + mask_w, mask_y + mask_h], fill=(58, 122, 189))

        # Border
        draw.rectangle([dx, dy + label_height, dx + cell_size, dy + label_height + cell_size], outline=(68, 68, 68))

    out_path = image_path.replace('.png', '_mosaic.png')
    mosaic.save(out_path)
    print(f"\n  Mosaic saved: {out_path}")


if __name__ == '__main__':
    image_path = sys.argv[1] if len(sys.argv) > 1 else 'test_board.png'
    success = test_grid_detection(image_path)
    sys.exit(0 if success else 1)
