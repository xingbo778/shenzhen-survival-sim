#!/usr/bin/env python3
"""
AI-powered 8-direction character sprite sheet generator.

Uses Compass API (Gemini) to generate full 8-direction turnaround sheets
from existing character reference frames.

Steps:
  1. Extract 2-3 representative frames per character from source sheets
  2. Upscale 4x and compose into a reference image
  3. Send reference image + prompt to Gemini for 8-direction generation
  4. Post-process: cut grid, remove background, scale to 256x256 cells
  5. Assemble final 2048x256 sprite sheet (8 cells)

Usage:
  export COMPASS_API_KEY=<key>
  python3 generate_char_sprites_ai.py                   # all characters
  python3 generate_char_sprites_ai.py --only startup    # single character
  python3 generate_char_sprites_ai.py --ref-only        # generate refs only
  python3 generate_char_sprites_ai.py --retry startup   # retry failed
"""

import os, sys, json, base64, argparse, time, io
from pathlib import Path

for pkg in ("requests", "PIL"):
    try:
        __import__(pkg)
    except ImportError:
        sys.exit(f"Missing: pip install requests Pillow")

import requests
from PIL import Image, ImageDraw, ImageFont
import numpy as np

# ── config ────────────────────────────────────────────────────────────────────
BASE_URL  = "https://compass.llm.shopee.io/compass-api/v1"
API_KEY   = os.getenv("COMPASS_API_KEY", "")
DEFAULT_MODEL = "gemini-2.5-flash-image"
ACTIVE_MODEL  = DEFAULT_MODEL

SCRIPT_DIR = Path(__file__).parent
CELL_W, CELL_H = 256, 256
UPSCALE = 4
REF_DIR  = SCRIPT_DIR / "_refs"
AI_DIR   = SCRIPT_DIR / "_ai_raw"

CHARACTERS = [
    "waimai", "coder", "uncle", "trader", "office",
    "runner", "startup", "drifter", "dancer", "guard", "reporter",
]

CHAR_DESCRIPTIONS = {
    "waimai":  "a food delivery rider wearing a yellow/blue uniform and helmet, carrying a delivery bag",
    "coder":   "a young male programmer/coder wearing casual clothes (hoodie or t-shirt), with glasses",
    "uncle":   "an older middle-aged man carrying shopping bags, wearing casual/traditional clothes",
    "trader":  "a business person in semi-formal attire holding a coffee cup",
    "office":  "a male office worker in a business suit carrying a briefcase",
    "runner":  "an athletic person in running/sport clothes, jogging pose",
    "startup": "a young male entrepreneur in smart-casual clothes (shirt, jeans), carrying a laptop bag",
    "drifter": "a casual young traveler/backpacker with a backpack and relaxed clothing",
    "dancer":  "a middle-aged woman (大妈) in colorful clothes holding a fan, doing square dance",
    "guard":   "a security guard in dark uniform with a cap",
    "reporter":"a female news reporter in professional attire, holding a microphone",
}

# ── source frame coordinates (from extract_characters.py) ─────────────────────
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

# Which source frames to use as reference for each character
# Format: list of (sheet, row, frame_idx) or (sheet, row, frame_idx, "reporter")
REF_FRAMES = {
    "waimai":  [(1, 0, 0), (1, 0, 1), (1, 0, 2)],       # front-right, back, left
    "coder":   [(1, 0, 4), (1, 0, 6), (1, 0, 7)],       # front, right-profile, back
    "uncle":   [(1, 1, 0), (1, 1, 1), (1, 1, 5)],       # front-right, front, front-direct
    "trader":  [(1, 1, 2), (1, 1, 3)],                    # right, left (only 2 frames)
    "office":  [(1, 2, 0), (1, 2, 2), (1, 2, 3)],       # front, right, back
    "runner":  [(1, 2, 4), (1, 2, 6), (1, 2, 7)],       # front, right, back
    "startup": [(2, 0, 0), (2, 0, 2), (2, 0, 5)],       # front, right-side, back
    "drifter": [(2, 1, 0), (2, 1, 2), (2, 1, 6)],       # front, left, back
    "dancer":  [(2, 2, 1), (2, 2, 2), (2, 2, 4)],       # front, right, back
    "guard":   [(2, 2, 5), (2, 2, 6), (2, 2, 8)],       # front, back, back-right
    "reporter":[(2, 3, 4, "reporter"), (2, 3, 2, "reporter"), (2, 3, 6, "reporter")],
}


# ── image helpers ─────────────────────────────────────────────────────────────

def load_source(name):
    return Image.open(SCRIPT_DIR / name).convert('RGBA')


def crop_auto(img, region):
    cropped = img.crop(region)
    bbox = cropped.getbbox()
    return cropped.crop(bbox) if bbox else cropped


def clean_reporter_region(img, region):
    frame = img.crop(region).copy()
    arr = np.array(frame)
    ri, gi, bi, ai = arr[:,:,0].astype(int), arr[:,:,1].astype(int), arr[:,:,2].astype(int), arr[:,:,3].astype(int)
    green_bg = (gi > ri) & (gi > bi) & (bi < 140) & (ri > 100) & (ri < 175) & (gi > 120) & (gi < 185)
    is_bg = green_bg | (ai < 15) | ((ai < 80) & (gi > ri) & (gi > bi))
    arr[is_bg] = [0, 0, 0, 0]
    cleaned = Image.fromarray(arr)
    bbox = cleaned.getbbox()
    return cleaned.crop(bbox) if bbox else cleaned


def extract_frame(src_img, sheet_num, row, col):
    if sheet_num == 1:
        y0, y1 = S1_ROWS[row]
        x0, x1 = S1_FX[row][col]
    else:
        y0, y1 = S2_ROWS[row]
        x0, x1 = S2_FX[row][col]
    return crop_auto(src_img, (x0, y0, x1, y1))


def extract_reporter_frame(src_img, col):
    y0, y1 = S2_ROWS[3]
    x0, x1 = REPORTER_X[col]
    return clean_reporter_region(src_img, (x0, y0, x1, y1))


def upscale(img, factor=UPSCALE):
    w, h = img.size
    return img.resize((w * factor, h * factor), Image.NEAREST)


def add_white_bg(img):
    """Replace transparency with white background."""
    bg = Image.new('RGBA', img.size, (255, 255, 255, 255))
    bg.paste(img, mask=img)
    return bg.convert('RGB')


# ── Step 1: Generate reference images ─────────────────────────────────────────

def generate_reference_image(char_name, s1, s2):
    """Create an upscaled reference image from 2-3 source frames."""
    refs = REF_FRAMES[char_name]
    frames = []
    for ref_info in refs:
        if len(ref_info) == 4 and ref_info[3] == "reporter":
            frame = extract_reporter_frame(s2, ref_info[2])
        elif ref_info[0] == 1:
            frame = extract_frame(s1, 1, ref_info[1], ref_info[2])
        else:
            frame = extract_frame(s2, 2, ref_info[1], ref_info[2])
        frames.append(frame)

    scaled_frames = [upscale(f) for f in frames]

    max_h = max(f.size[1] for f in scaled_frames)
    total_w = sum(f.size[0] for f in scaled_frames) + 20 * (len(scaled_frames) - 1)

    padding = 40
    canvas = Image.new('RGBA', (total_w + padding * 2, max_h + padding * 2), (255, 255, 255, 255))

    x = padding
    for f in scaled_frames:
        y_off = padding + max_h - f.size[1]
        canvas.paste(f, (x, y_off), f)
        x += f.size[0] + 20

    return canvas


def generate_all_refs():
    """Generate reference images for all characters."""
    REF_DIR.mkdir(exist_ok=True)

    s1 = load_source('_source_sheet1.png')
    s2 = load_source('_source_sheet2.png')

    for char_name in CHARACTERS:
        ref_img = generate_reference_image(char_name, s1, s2)
        out_path = REF_DIR / f"{char_name}_ref.png"
        ref_img.save(str(out_path))
        print(f"  ref: {char_name:10s}  {ref_img.size[0]}x{ref_img.size[1]}  → {out_path.name}")

    print(f"\n{len(CHARACTERS)} reference images saved to {REF_DIR}/")


# ── Step 2: Gemini API call with reference image ──────────────────────────────

def _headers():
    return {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}


def call_gemini_with_image(prompt: str, ref_image: Image.Image, model: str = None) -> bytes:
    """Call Gemini API with a text prompt and an inline reference image."""
    if model is None:
        model = ACTIVE_MODEL
    buf = io.BytesIO()
    ref_image.save(buf, format='PNG')
    img_b64 = base64.b64encode(buf.getvalue()).decode()

    url = f"{BASE_URL}/models/{model}:generateContent"
    body = {
        "contents": [{
            "role": "user",
            "parts": [
                {
                    "inlineData": {
                        "mimeType": "image/png",
                        "data": img_b64,
                    }
                },
                {"text": prompt},
            ],
        }],
        "generationConfig": {
            "responseModalities": ["IMAGE"],
        },
    }

    r = requests.post(url, headers=_headers(), json=body, timeout=120)
    r.raise_for_status()
    data = r.json()

    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                return base64.b64decode(inline["data"])
    raise RuntimeError(f"No image in response: {json.dumps(data)[:400]}")


def build_prompt(char_name: str) -> str:
    desc = CHAR_DESCRIPTIONS.get(char_name, "a pixel art character")
    return (
        f"Generate a pixel art character sprite turnaround sheet.\n"
        f"The character is: {desc}.\n"
        f"The attached reference image shows this character from 2-3 angles.\n"
        f"Your output must look EXACTLY like this character — same colors, proportions, clothing, accessories.\n\n"
        f"Layout: 4 columns × 2 rows grid on a pure white background.\n"
        f"Each cell should be the same size and contain the character centered.\n"
        f"Row 1 (left→right): Front facing, Back facing, Left side, Right side\n"
        f"Row 2 (left→right): Front-left diagonal, Back-left diagonal, Front-right diagonal, Back-right diagonal\n\n"
        f"CRITICAL requirements:\n"
        f"- Pixel art style (SNES/GBA era, ~32x48 pixel character, but rendered at higher resolution)\n"
        f"- Each cell shows the SAME character facing a DIFFERENT direction\n"
        f"- All 8 directions must be clearly distinct from each other\n"
        f"- Consistent proportions, colors, and details across all 8 views\n"
        f"- Character stands on the bottom edge of each cell\n"
        f"- Pure white background (no gradients, no floor shadows)\n"
        f"- No labels, text, or annotations\n"
        f"- The overall image should be roughly 1024×512 pixels"
    )


def generate_character_ai(char_name: str, ref_img: Image.Image) -> Image.Image:
    """Call Gemini to generate 8-direction sheet for a character."""
    prompt = build_prompt(char_name)
    raw_bytes = call_gemini_with_image(prompt, ref_img, ACTIVE_MODEL)
    return Image.open(io.BytesIO(raw_bytes)).convert('RGBA')


# ── Step 3: Post-processing ──────────────────────────────────────────────────

def remove_bg(img: Image.Image, threshold: int = 235) -> Image.Image:
    """Flood-fill from corners to remove white background."""
    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()

    def is_bg(px):
        r, g, b, a = px
        return a > 0 and r >= threshold and g >= threshold and b >= threshold

    visited = set()
    stack = [(0,0), (w-1,0), (0,h-1), (w-1,h-1)]

    while stack:
        x, y = stack.pop()
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        if (x, y) in visited:
            continue
        visited.add((x, y))
        if is_bg(pixels[x, y]):
            pixels[x, y] = (0, 0, 0, 0)
            stack += [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]

    return img


def _find_gaps(alpha_sum, min_gap=5):
    """Find contiguous runs of near-zero in a 1D alpha projection."""
    n = len(alpha_sum)
    thresh = max(alpha_sum) * 0.01
    is_empty = [v <= thresh for v in alpha_sum]
    gaps = []
    start = None
    for i, empty in enumerate(is_empty):
        if empty and start is None:
            start = i
        elif not empty and start is not None:
            if i - start >= min_gap:
                gaps.append((start, i))
            start = None
    if start is not None and n - start >= min_gap:
        gaps.append((start, n))
    return gaps


def _split_by_gaps(size, gaps):
    """Convert gap list into list of (start, end) content ranges."""
    ranges = []
    prev = 0
    for gs, ge in gaps:
        if gs > prev:
            ranges.append((prev, gs))
        prev = ge
    if prev < size:
        ranges.append((prev, size))
    return ranges


def cut_content_aware(img: Image.Image) -> list:
    """Detect individual character cells by finding transparent gaps between them.
    Falls back to uniform grid cutting if gap detection fails."""
    arr = np.array(img)
    alpha = arr[:, :, 3].astype(float)
    w, h = img.size

    col_sum = alpha.sum(axis=0)
    row_sum = alpha.sum(axis=1)

    h_gaps = _find_gaps(row_sum, min_gap=3)
    row_ranges = _split_by_gaps(h, h_gaps)

    cells = []
    for ry0, ry1 in row_ranges:
        row_alpha = alpha[ry0:ry1, :]
        row_col_sum = row_alpha.sum(axis=0)
        v_gaps = _find_gaps(row_col_sum, min_gap=3)
        col_ranges = _split_by_gaps(w, v_gaps)
        for cx0, cx1 in col_ranges:
            cell = img.crop((cx0, ry0, cx1, ry1))
            if cell.getbbox():
                cells.append(cell)

    if len(cells) >= 8:
        return cells[:8]

    # Fallback: uniform grid
    ratio = w / h
    if ratio > 3.5:
        cols, rows = 8, 1
    elif ratio > 1.3:
        cols, rows = 4, 2
    elif ratio > 0.9:
        cols, rows = (2, 4) if h > w * 1.3 else (4, 3)
    else:
        cols, rows = 2, 4

    cw, ch = w // cols, h // rows
    cells = []
    for r in range(rows):
        for c in range(cols):
            cell = img.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch))
            cells.append(cell)
    return cells[:8]


def trim_and_scale_cell(cell: Image.Image) -> Image.Image:
    """Trim transparent border, scale to fill CELL_H, center in CELL_W x CELL_H."""
    bbox = cell.getbbox()
    if not bbox:
        return Image.new('RGBA', (CELL_W, CELL_H), (0, 0, 0, 0))

    trimmed = cell.crop(bbox)
    tw, th = trimmed.size

    scale = CELL_H / th
    nw, nh = max(1, round(tw * scale)), max(1, round(th * scale))

    if nw > CELL_W:
        scale = CELL_W / tw
        nw, nh = max(1, round(tw * scale)), max(1, round(th * scale))

    scaled = trimmed.resize((nw, nh), Image.LANCZOS)
    out = Image.new('RGBA', (CELL_W, CELL_H), (0, 0, 0, 0))
    out.paste(scaled, ((CELL_W - nw) // 2, CELL_H - nh), scaled)
    return out


def assemble_sheet(cells_8: list) -> Image.Image:
    """Assemble 8 processed cells into a 2048x256 sprite sheet."""
    sheet = Image.new('RGBA', (CELL_W * 8, CELL_H), (0, 0, 0, 0))
    for i, cell in enumerate(cells_8):
        sheet.paste(cell, (i * CELL_W, 0), cell)
    return sheet


def process_ai_output(raw_img: Image.Image) -> Image.Image:
    """Full pipeline: remove bg → detect & cut cells → trim/scale → assemble sheet."""
    cleaned = remove_bg(raw_img)
    cells = cut_content_aware(cleaned)
    processed = [trim_and_scale_cell(c) for c in cells]
    return assemble_sheet(processed)


# ── Main pipeline ─────────────────────────────────────────────────────────────

def process_single(char_name: str, s1, s2, force=False):
    """Generate sprite sheet for a single character."""
    final_path = SCRIPT_DIR / f"{char_name}.png"
    ai_path = AI_DIR / f"{char_name}_ai.png"
    ref_path = REF_DIR / f"{char_name}_ref.png"

    # Step 1: Reference image
    if not ref_path.exists() or force:
        ref_img = generate_reference_image(char_name, s1, s2)
        REF_DIR.mkdir(exist_ok=True)
        ref_img.save(str(ref_path))
        print(f"  ref: {char_name:10s}  {ref_img.size[0]}x{ref_img.size[1]}")
    else:
        ref_img = Image.open(str(ref_path)).convert('RGBA')
        print(f"  ref: {char_name:10s}  (cached)")

    # Step 2: Gemini API call
    if not ai_path.exists() or force:
        print(f"  api: {char_name:10s}  calling {ACTIVE_MODEL}...")
        try:
            raw = generate_character_ai(char_name, ref_img)
            AI_DIR.mkdir(exist_ok=True)
            raw.save(str(ai_path))
            print(f"  api: {char_name:10s}  {raw.size[0]}x{raw.size[1]}  OK")
        except Exception as e:
            print(f"  api: {char_name:10s}  FAILED: {e}")
            return False
        time.sleep(2)
    else:
        raw = Image.open(str(ai_path)).convert('RGBA')
        print(f"  api: {char_name:10s}  (cached)")

    # Step 3: Post-process
    sheet = process_ai_output(raw)
    sheet.save(str(final_path))
    print(f"  out: {char_name:10s}  {sheet.size[0]}x{sheet.size[1]}  → {final_path.name}")
    return True


def main():
    parser = argparse.ArgumentParser(description="AI character sprite generator")
    parser.add_argument("--only", help="Process only this character")
    parser.add_argument("--retry", help="Force retry this character (overwrite cache)")
    parser.add_argument("--ref-only", action="store_true", help="Only generate reference images")
    parser.add_argument("--model", default=DEFAULT_MODEL, help=f"Gemini model (default: {DEFAULT_MODEL})")
    args = parser.parse_args()

    global ACTIVE_MODEL
    ACTIVE_MODEL = args.model

    if not API_KEY and not args.ref_only:
        sys.exit("Set COMPASS_API_KEY environment variable")

    s1 = load_source('_source_sheet1.png')
    s2 = load_source('_source_sheet2.png')

    if args.ref_only:
        generate_all_refs()
        return

    chars = CHARACTERS
    if args.only:
        chars = [args.only]
    elif args.retry:
        chars = [args.retry]

    force = args.retry is not None
    ok, fail = 0, 0

    print(f"Processing {len(chars)} characters with model={ACTIVE_MODEL}\n")

    for name in chars:
        if name not in CHAR_DESCRIPTIONS:
            print(f"  SKIP: unknown character '{name}'")
            continue
        success = process_single(name, s1, s2, force=force)
        if success:
            ok += 1
        else:
            fail += 1

    print(f"\nDone: {ok} ok, {fail} failed")
    print(f"Frame order: front, back, left, right, front_left, back_left, front_right, back_right")


if __name__ == '__main__':
    main()
