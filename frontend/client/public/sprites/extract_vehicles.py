"""
Extract individual vehicle and boat sprite sheets.

Strategy: extract RIGHT-facing frames only for each vehicle type.
Left-facing is achieved by flipping at render time (same as characters).
This avoids the complex overlapping layout in the combined sheet.

Each vehicle gets one PNG with N right-facing animation frames in a row.
Boats similarly get 4 right-facing frames.
"""

from PIL import Image
import numpy as np


def crop_trim(img, region):
    cropped = img.crop(region)
    bbox = cropped.getbbox()
    return cropped.crop(bbox) if bbox else cropped


def make_sheet(frames):
    if not frames:
        return None, 0, 0
    max_w = max(f.size[0] for f in frames)
    max_h = max(f.size[1] for f in frames)
    n = len(frames)
    sheet = Image.new('RGBA', (max_w * n, max_h), (0, 0, 0, 0))
    for i, f in enumerate(frames):
        fw, fh = f.size
        sheet.paste(f, (i * max_w + (max_w - fw) // 2, max_h - fh), f)
    return sheet, max_w, max_h


# ── Vehicle definitions (RIGHT-facing only) ──────────────────────
# Precise per-frame bounding boxes: (x0, y0, x1, y1)

VEHICLES = {
    'taxi': [
        (70, 40, 275, 460),
        (414, 40, 619, 460),
        (762, 40, 967, 460),
        (1107, 40, 1312, 460),
    ],
    'huolala': [
        (1393, 40, 1725, 250),
        (1725, 40, 2058, 250),   # this is actually left-facing but in the same row
    ],
    'meituan': [
        (1422, 310, 1655, 610),
        (1777, 310, 2004, 610),
    ],
    'sweeper': [
        (41, 614, 304, 920),
        (384, 614, 648, 920),
        (728, 614, 991, 920),
        (1083, 614, 1336, 920),
    ],
    'shared_bike': [
        (51, 921, 292, 1230),
        (396, 921, 636, 1230),
        (741, 921, 980, 1230),
        (1160, 921, 1266, 1230),
    ],
    'bus': [
        (29, 1300, 1364, 1536),
    ],
}


def extract_vehicles():
    src = Image.open('vehicles/vehicles_sheet.png').convert('RGBA')
    results = {}

    for name, regions in VEHICLES.items():
        frames = [crop_trim(src, r) for r in regions]
        sheet, cw, ch = make_sheet(frames)
        results[name] = {
            'sheet': sheet, 'cell_w': cw, 'cell_h': ch,
            'total': len(frames),
        }

    return results


# ── Boat extraction ──────────────────────────────────────────────

def extract_boats():
    src = Image.open('boats/boats_sheet.png').convert('RGBA')
    w, h = src.size

    # Remove white background
    arr = np.array(src)
    r, g, b, a = arr[:,:,0], arr[:,:,1], arr[:,:,2], arr[:,:,3]
    arr[(r > 230) & (g > 230) & (b > 230)] = [0, 0, 0, 0]
    arr[(r > 210) & (g > 210) & (b > 210) & (a < 200)] = [0, 0, 0, 0]
    cleaned = Image.fromarray(arr)
    alpha = arr[:,:,3]

    # Find rows
    row_sum = alpha.sum(axis=1)
    segs = []
    in_c = False
    cs = 0
    for y in range(h):
        if row_sum[y] > 300 and not in_c:
            cs = y; in_c = True
        elif row_sum[y] <= 300 and in_c:
            if y - cs > 30: segs.append((cs, y))
            in_c = False
    if in_c and h - cs > 30: segs.append((cs, h))

    boat_names = ['fishing_boat', 'cruise', 'speedboat']
    results = {}

    for row_idx, (y0, y1) in enumerate(segs[:3]):
        name = boat_names[row_idx]

        # Find columns, skip text labels (x < 350)
        row_alpha = alpha[y0:y1, 350:]
        col_sum = row_alpha.sum(axis=0).astype(float)
        is_col = col_sum > 100

        col_segs = []
        in_c = False
        cs = 0
        for x in range(len(is_col)):
            if is_col[x] and not in_c:
                cs = x; in_c = True
            elif not is_col[x] and in_c:
                if x - cs > 50:
                    col_segs.append((cs + 350, x + 350))
                in_c = False
        if in_c and len(is_col) - cs > 50:
            col_segs.append((cs + 350, len(is_col) + 350))

        frames = []
        for x0, x1 in col_segs[:4]:
            region = cleaned.crop((x0, y0, x1, y1))
            bbox = region.getbbox()
            if bbox:
                region = region.crop(bbox)
            frames.append(region)

        if not frames:
            continue

        sheet, cw, ch = make_sheet(frames)
        results[name] = {
            'sheet': sheet, 'cell_w': cw, 'cell_h': ch, 'total': len(frames),
        }

    return results


def main():
    print('=== Vehicles (right-facing frames) ===')
    vehicles = extract_vehicles()
    for name, info in vehicles.items():
        info['sheet'].save(f'vehicles/{name}.png')
        print(f'  {name:12s}  cell={info["cell_w"]:4d}x{info["cell_h"]:3d}  '
              f'{info["total"]} frames  → {info["sheet"].size[0]}x{info["sheet"].size[1]}')

    print('\n=== Boats ===')
    boats = extract_boats()
    for name, info in boats.items():
        info['sheet'].save(f'boats/{name}.png')
        print(f'  {name:12s}  cell={info["cell_w"]:4d}x{info["cell_h"]:3d}  '
              f'{info["total"]} frames  → {info["sheet"].size[0]}x{info["sheet"].size[1]}')

    # Metadata for vehicleSystem.ts update
    print('\n=== Sheet metadata ===')
    for name, info in {**vehicles, **boats}.items():
        print(f"  {name}: {{ cellW: {info['cell_w']}, cellH: {info['cell_h']}, frames: {info['total']} }}")


if __name__ == '__main__':
    main()
