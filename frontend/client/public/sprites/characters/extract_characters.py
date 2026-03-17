"""
Extract individual character sprite sheets from combined source sheets.

Output: 8-frame sprite sheets, single row, 256×256 cells.
  Frame order: front, back, left, right, front_left, back_left, front_right, back_right

Direction mapping strategy:
  - Use the best source frame for each of the 8 directions.
  - Mirror left/right pairs when only one side exists.
  - Each character may use different source frames depending on what's available.
"""

from PIL import Image
import numpy as np

CELL_W = 256
CELL_H = 256


def load_source(name):
    return Image.open(name).convert('RGBA')


def crop_auto(img, region):
    cropped = img.crop(region)
    bbox = cropped.getbbox()
    return cropped.crop(bbox) if bbox else cropped


def mirror(img):
    return img.transpose(Image.FLIP_LEFT_RIGHT)


def clean_bg_pixels(sheet):
    px = sheet.load()
    w, h = sheet.size
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if a < 10:
                px[x, y] = (0, 0, 0, 0)
            elif a < 80 and r > 200 and g > 200 and b > 200:
                px[x, y] = (0, 0, 0, 0)
    return sheet


def clean_reporter_region(img, region):
    frame = img.crop(region).copy()
    arr = np.array(frame)
    ri, gi, bi, ai = arr[:,:,0].astype(int), arr[:,:,1].astype(int), arr[:,:,2].astype(int), arr[:,:,3].astype(int)
    green_bg = (gi > ri) & (gi > bi) & (bi < 140) & (ri > 100) & (ri < 175) & (gi > 120) & (gi < 185)
    is_bg = (
        green_bg
        | (ai < 15)
        | ((ai < 80) & (gi > ri) & (gi > bi))
    )
    arr[is_bg] = [0, 0, 0, 0]
    cleaned = Image.fromarray(arr)
    bbox = cleaned.getbbox()
    return cleaned.crop(bbox) if bbox else cleaned


# ── source coordinates ───────────────────────────────────────────

S1_ROWS = [(41, 462), (561, 979), (1078, 1515)]
S1_FX = [
    [(68,270),(426,618),(734,953),(1106,1324),(1457,1644),(1806,1988),(2136,2327),(2485,2673)],
    [(52,301),(420,607),(756,952),(1097,1291),(1414,1675),(1756,2018),(2122,2350),(2472,2676)],
    [(75,265),(431,607),(759,947),(1098,1295),(1452,1633),(1806,1977),(2135,2321),(2478,2654)],
]
S2_ROWS = [(17, 359), (401, 744), (791, 1134), (1142, 1522)]
S2_FX = [
    [(63,213),(339,487),(614,761),(894,1033),(1439,1582),(1710,1858),(1991,2131),(2262,2402),(2535,2679)],
    [(70,206),(344,482),(592,759),(866,1033),(1163,1328),(1439,1582),(1714,1858),(1991,2132),(2263,2430),(2536,2704)],
    [(59,213),(333,488),(620,767),(889,1041),(1153,1301),(1438,1583),(1709,1858),(1990,2132),(2270,2404),(2549,2682)],
    [],
]
REPORTER_X = [(30,256),(304,522),(552,797),(826,1073),(1123,1368),(1399,1623),(1674,1898),(1951,2175),(2223,2473),(2496,2744)]


def raw_frame(src, row_idx, frame_idx, rows_table, fx_table):
    y0, y1 = rows_table[row_idx]
    x0, x1 = fx_table[row_idx][frame_idx]
    return crop_auto(src, (x0, y0, x1, y1))


def build_sheet(frames_8):
    """Build 8-frame sheet from list of 8 PIL images. Scale so tallest fills CELL_H."""
    max_h = max(f.size[1] for f in frames_8)
    scale = CELL_H / max_h

    cells = []
    for fr in frames_8:
        w, h = fr.size
        nw, nh = max(1, round(w * scale)), max(1, round(h * scale))
        scaled = fr.resize((nw, nh), Image.LANCZOS)
        cell = Image.new('RGBA', (CELL_W, CELL_H), (0, 0, 0, 0))
        cell.paste(scaled, ((CELL_W - nw) // 2, CELL_H - nh), scaled)
        cells.append(cell)

    sheet = Image.new('RGBA', (CELL_W * 8, CELL_H), (0, 0, 0, 0))
    for i, c in enumerate(cells):
        sheet.paste(c, (i * CELL_W, 0), c)
    return sheet


def collect_and_build():
    s1 = load_source('_source_sheet1.png')
    s2 = load_source('_source_sheet2.png')

    def s1f(r, i): return raw_frame(s1, r, i, S1_ROWS, S1_FX)
    def s2f(r, i): return raw_frame(s2, r, i, S2_ROWS, S2_FX)

    # Output frame order: front, back, left, right, front_left, back_left, front_right, back_right

    sheets = {}

    # ── Sheet 1 characters ──────────────────────────────────────
    # Sheet 1 has 2 characters per row, ~4 frames each.
    # Available directions per character are limited (right-side bias).
    # Strategy: front + back use the most frontal/dorsal frames,
    #   left/right use the pure side-walk frames,
    #   front_left/front_right use the 3/4 walk frames (distinct from front),
    #   back_left/back_right use the 3/4 back-walk frames (distinct from back).
    #
    # Sheet 1 Row 0: waimai (frames 0-3) + coder (frames 4-7)
    #
    # Waimai:
    #   f0: front-right 3/4 (facing camera, body angled right, walking)
    #   f1: back (full back view)
    #   f2: left-side walk (profile, face visible left)
    #   f3: back-left 3/4 walk
    wm0, wm1, wm2, wm3 = s1f(0,0), s1f(0,1), s1f(0,2), s1f(0,3)
    sheets['waimai'] = [
        wm0,            # front: 3/4 front-right (best frontal we have)
        wm1,            # back
        wm2,            # left: left-side walk
        mirror(wm2),    # right: mirror of left
        wm2,            # front_left: left-side walk (face visible → good for front_left)
        wm3,            # back_left
        mirror(wm2),    # front_right: mirror of left-walk
        mirror(wm3),    # back_right: mirror of back-left
    ]

    # Coder:
    #   f4: front-right 3/4 (standing)
    #   f5: front-right 3/4 (walking, similar to f4)
    #   f6: right-side walk (profile)
    #   f7: back-right 3/4 walk
    cd4, cd5, cd6, cd7 = s1f(0,4), s1f(0,5), s1f(0,6), s1f(0,7)
    sheets['coder'] = [
        cd4,            # front: 3/4 front (best frontal)
        cd7,            # back: back-right 3/4 (best dorsal)
        mirror(cd6),    # left: mirror of right-side walk
        cd6,            # right: right-side walk
        mirror(cd6),    # front_left: mirror of right walk (face side visible)
        mirror(cd7),    # back_left: mirror of back-right
        cd6,            # front_right: right-side walk
        cd7,            # back_right
    ]

    # Sheet 1 Row 1: uncle (frames 0,1,4,5,6,7) + trader (frames 2,3)
    #
    # Uncle (6 frames — richest set in sheet 1):
    #   f0: front-right 3/4 (bags, angled right, walking)
    #   f1: front (facing camera, slightly right)
    #   f4: front-left 3/4 (bags, angled left, walking)
    #   f5: front (facing camera directly)
    #   f6: back-left 3/4 (walking left)
    #   f7: back-right 3/4 (walking right)
    u0, u1, u4, u5, u6, u7 = s1f(1,0), s1f(1,1), s1f(1,4), s1f(1,5), s1f(1,6), s1f(1,7)
    sheets['uncle'] = [
        u5,             # front: direct front
        mirror(u6),     # back: mirror of back-left ≈ back
        mirror(u0),     # left: mirror of front-right walk (shows left side)
        u0,             # right: front-right walk (shows right side)
        u4,             # front_left: actual front-left 3/4
        u6,             # back_left
        u0,             # front_right: front-right 3/4
        u7,             # back_right
    ]

    # Trader (only 2 frames):
    #   f2: right-side walk (with coffee, profile)
    #   f3: left-side walk (with coffee, profile, face visible)
    t2, t3 = s1f(1,2), s1f(1,3)
    sheets['trader'] = [
        t3,             # front: left-walk (face visible = best frontal)
        mirror(t2),     # back: mirror of right-walk (back of head visible)
        t3,             # left: left-side walk
        t2,             # right: right-side walk
        t3,             # front_left: left walk (face visible)
        mirror(t2),     # back_left: mirror of right walk
        t2,             # front_right: right-side walk
        mirror(t3),     # back_right: mirror of left walk
    ]

    # Sheet 1 Row 2: office (frames 0-3) + runner (frames 4-7)
    #
    # Office:
    #   f0: front-right 3/4 (walking, briefcase)
    #   f1: front-right 3/4 (variant, walking)
    #   f2: right-side walk (profile)
    #   f3: back-right 3/4 walk
    of0, of1, of2, of3 = s1f(2,0), s1f(2,1), s1f(2,2), s1f(2,3)
    sheets['office'] = [
        of0,            # front: front-right 3/4 (best frontal)
        of3,            # back: back-right 3/4 (best dorsal)
        mirror(of2),    # left: mirror of right-side walk
        of2,            # right: right-side walk
        mirror(of2),    # front_left: mirror of right walk
        mirror(of3),    # back_left: mirror of back-right
        of2,            # front_right: right-side walk
        of3,            # back_right
    ]

    # Runner:
    #   f4: front-right 3/4 (running)
    #   f5: front-right 3/4 (running variant)
    #   f6: right-side run (profile)
    #   f7: back-right 3/4 run
    rn4, rn5, rn6, rn7 = s1f(2,4), s1f(2,5), s1f(2,6), s1f(2,7)
    sheets['runner'] = [
        rn4,            # front: front-right 3/4 (best frontal)
        rn7,            # back: back-right 3/4 (best dorsal)
        mirror(rn6),    # left: mirror of right-side run
        rn6,            # right: right-side run
        mirror(rn6),    # front_left: mirror of right run
        mirror(rn7),    # back_left: mirror of back-right
        rn6,            # front_right: right-side run
        rn7,            # back_right
    ]

    # ── Sheet 2 characters ──────────────────────────────────────
    # Sheet 2 Row 0: startup (9 frames)
    #   All source frames are front or RIGHT-side views, no left views exist.
    #   f0: front (near-frontal, slight right)
    #   f1: front (walking, near-frontal)
    #   f2: right side (pure profile, walking)
    #   f3: right side (slightly more back-angled than f2)
    #   f4: front (facing camera)
    #   f5: back (full back)
    #   f6: front (standing, direct)
    #   f7: back-right (walking, back visible + right side)
    #   f8: front-right (walking, face visible + right side)
    #
    # Mapping: right=su2 (pure side), front_right=su8 (face+side),
    #   back_right=su7 (back+side). Left versions = mirrors.
    su = [s2f(0,i) for i in range(9)]
    sheets['startup'] = [
        su[6],          # front: direct front standing
        su[5],          # back: full back
        mirror(su[2]),  # left: mirror of pure right-side
        su[2],          # right: pure right-side walk
        mirror(su[8]),  # front_left: mirror of front-right (face visible)
        mirror(su[7]),  # back_left: mirror of back-right (back visible)
        su[8],          # front_right: face visible + right side
        su[7],          # back_right: back visible + right side
    ]

    # Sheet 2 Row 1: drifter (10 frames — most complete set)
    #   f0: front (standing, facing camera)
    #   f1: front (standing variant)
    #   f2: left-side walk (backpack on right, face on left)
    #   f3: back-left 3/4 walk
    #   f4: back-right 3/4 walk
    #   f5: front (another standing view)
    #   f6: back (full back)
    #   f7: back (variant)
    #   f8: front-left 3/4 walk (face left, body angled left)
    #   f9: front-right 3/4 walk (face right, body angled right)
    dr = [s2f(1,i) for i in range(10)]
    sheets['drifter'] = [
        dr[0],          # front
        dr[6],          # back
        dr[2],          # left: left-side walk
        mirror(dr[2]),  # right: mirror of left
        dr[8],          # front_left: actual front-left walk
        dr[3],          # back_left: actual back-left walk
        dr[9],          # front_right: actual front-right walk
        dr[4],          # back_right: actual back-right walk
    ]

    # Sheet 2 Row 2: dancer (frames 0-4) + guard (frames 5-9)
    #
    # Dancer (大妈 with fan):
    #   f0: front-right 3/4 (fan visible, facing camera-right)
    #   f1: front (facing camera, fan in front)
    #   f2: right-side (walking right, showing right profile/back)
    #   f3: back-right 3/4 (more turned away)
    #   f4: back (full back)
    dn = [s2f(2,i) for i in range(5)]
    sheets['dancer'] = [
        dn[1],          # front: facing camera
        dn[4],          # back: full back
        mirror(dn[2]),  # left: mirror of right-side
        dn[2],          # right: right-side walk
        mirror(dn[0]),  # front_left: mirror of front-right 3/4
        mirror(dn[3]),  # back_left: mirror of back-right
        dn[0],          # front_right: front-right 3/4
        dn[3],          # back_right
    ]

    # Guard (保安):
    #   f5: front (facing camera)
    #   f6: back (full back)
    #   f7: front (slightly different, walking)
    #   f8: back-right 3/4 walk
    #   f9: back-left 3/4 walk
    gd = [s2f(2,i) for i in range(5, 10)]
    sheets['guard'] = [
        gd[0],          # front
        gd[1],          # back
        mirror(gd[3]),  # left: mirror of back-right walk (left profile)
        gd[3],          # right: back-right walk (right profile)
        mirror(gd[3]),  # front_left: mirror of back-right (shows left side)
        gd[4],          # back_left: actual back-left walk
        gd[3],          # front_right: back-right walk (shows right side)
        gd[3],          # back_right
    ]

    # Sheet 2 Row 3: reporter (10 frames)
    y0, y1 = S2_ROWS[3]
    rep_frames = [clean_reporter_region(s2, (x0, y0, x1, y1)) for x0, x1 in REPORTER_X]

    # Reporter:
    #   f0: front-right 3/4
    #   f1: front-right 3/4 (variant)
    #   f2: right-side (profile)
    #   f3: back-right 3/4
    #   f4: front (facing camera)
    #   f5: front (variant)
    #   f6: back
    #   f7: back (variant)
    #   f8: back-left 3/4
    #   f9: front-left 3/4
    sheets['reporter'] = [
        rep_frames[4],          # front
        rep_frames[6],          # back
        mirror(rep_frames[2]),  # left: mirror of right-side
        rep_frames[2],          # right: right-side profile
        rep_frames[9],          # front_left: actual front-left
        rep_frames[8],          # back_left: actual back-left
        rep_frames[0],          # front_right: front-right 3/4
        rep_frames[3],          # back_right
    ]

    return sheets


def main():
    all_sheets = collect_and_build()

    for name, frames_8 in all_sheets.items():
        sheet = build_sheet(frames_8)
        sheet = clean_bg_pixels(sheet)
        sheet.save(f'{name}.png')
        max_h = max(f.size[1] for f in frames_8)
        print(f'  {name:10s}  raw_max_h={max_h:3d}  →  {sheet.size[0]}x{sheet.size[1]}')

    print(f'\n{len(all_sheets)} characters, {CELL_W*8}x{CELL_H} each, zero vertical padding')
    print('Frame order: front, back, left, right, front_left, back_left, front_right, back_right')


if __name__ == '__main__':
    main()
