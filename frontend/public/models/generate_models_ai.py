"""
generate_models_ai.py
Batch-generate Shenzhen-style 3D building GLB files via Meshy.ai Text-to-3D API.

Usage:
  python3 generate_models_ai.py
  python3 generate_models_ai.py --dry-run          (list specs only)
  python3 generate_models_ai.py --only office_tower (single model)

Output: buildings/{name}.glb
"""

import argparse
import os
import sys
import time
import requests

API_KEY  = os.getenv("MESHY_API_KEY", "msy_H9GSONfl0RE7Xxnywt4FVAyliGnUFJm9FlzF")
BASE_URL = "https://api.meshy.ai"
OUT_DIR_BUILDINGS  = os.path.join(os.path.dirname(__file__), "..", "..", "client", "public", "models", "buildings")
OUT_DIR_FURNITURE  = os.path.join(os.path.dirname(__file__), "..", "..", "client", "public", "models", "furniture")

FURNITURE_NAMES = {"palm_tree", "street_tree", "metro_entrance", "traffic_light", "road_sign", "street_lamp", "bench"}

# ── Model specs ───────────────────────────────────────────────────────────────
# (filename, prompt, negative_prompt)
MODEL_SPECS = [
    # ── Office towers (CBD skyline) ──────────────────────────────────────────
    ("office_tower",
     "Modern glass curtain wall office skyscraper, Shenzhen CBD Futian, "
     "deep blue glass panels, silver metal frame, flat roof with helipad H marking, "
     "antenna mast on top, low-poly isometric 3D game asset, clean topology, "
     "toon shading, no shadows baked in",
     "people, cars, interior, trees, background, landscape"),

    ("office_tower_v1",
     "Eco-friendly glass office tower, Shenzhen CBD, green tinted glass facade, "
     "vertical green wall strip, flat roof with HVAC units, "
     "low-poly isometric 3D game building, cartoon style",
     "people, cars, interior"),

    ("office_tower_v2",
     "Silver curtain wall skyscraper, metallic reflective facade, Shenzhen Futian, "
     "stepped crown at top, glass sky lobby floor band, "
     "low-poly isometric 3D game building",
     "people, cars, interior"),

    # ── CBD buildings ────────────────────────────────────────────────────────
    ("cbd_building",
     "Modern teal-blue CBD highrise building, Shenzhen financial district, "
     "rectangular floor plan, skylight grid on roof, corner HVAC units, "
     "low-poly isometric 3D game asset",
     "people, cars, interior"),

    ("cbd_building_v1",
     "Cool grey steel office block, modern urban building, Shenzhen, "
     "flat glass windows, silver exterior, roof mechanical floor, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    ("cbd_building_v2",
     "Warm gold-tan facade corporate tower, Shenzhen city, "
     "horizontal window bands, bronze cladding, flat roof, "
     "low-poly isometric 3D game building",
     "people, cars"),

    # ── Apartment blocks ─────────────────────────────────────────────────────
    ("apartment_block",
     "8-story beige residential apartment block, Shenzhen urban neighborhood, "
     "uniform grid of windows, balcony railings, water tanks on roof, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    ("apartment_block_v1",
     "Sky blue residential apartment building, Shenzhen suburb, "
     "light blue-white facade, regular window grid, flat roof with laundry poles, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    ("apartment_block_v2",
     "Salmon pink apartment building, Chinese urban residential, "
     "warm pink facade, balconies with green planters, AC units on walls, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    # ── Shop buildings ───────────────────────────────────────────────────────
    ("shop_building",
     "Two-story cream retail shop building, Shenzhen street-level commercial, "
     "colorful shop awnings on ground floor, large display windows, "
     "AC unit cluster on roof, low-poly isometric 3D game asset",
     "people, cars"),

    ("shop_building_v1",
     "Terracotta orange shop building, Chinese urban commercial street, "
     "warm orange-red facade, traditional shop sign banner, tiled awning, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    ("shop_building_v2",
     "White modern minimalist retail building, Shenzhen commercial, "
     "clean white walls, floor-to-ceiling glass storefront, flat roof with sign board, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    # ── Village buildings ────────────────────────────────────────────────────
    ("village_building",
     "Narrow grey urban village apartment, Shenzhen handshake building, "
     "gray plaster exterior, small windows, AC units on every floor, "
     "water tanks on roof, satellite dish, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    ("village_building_v1",
     "Warm orange-clay urban village building, southern China informal housing, "
     "terracotta tile fragments, cluttered rooftop, laundry poles, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    ("village_building_v2",
     "Aged green urban village apartment, weathered building Shenzhen, "
     "mossy green stains on grey facade, old AC units, worn signage, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    # ── Vegetation & street furniture ────────────────────────────────────────
    ("palm_tree",
     "Tall tropical palm tree, Shenzhen city street, slender curved brown trunk, "
     "wide spreading green fronds at top, isolated single tree, "
     "low-poly isometric 3D game asset, no ground plane",
     "people, buildings, cars, background"),

    ("street_tree",
     "Round deciduous city street tree, urban China, "
     "dense round green canopy, short brown trunk, circular concrete tree grate, "
     "low-poly isometric 3D game asset, isolated",
     "people, buildings, cars"),

    ("metro_entrance",
     "Shenzhen Metro subway entrance structure, "
     "dark green canopy roof, red illuminated 地铁 sign, "
     "glass windscreen panels, concrete steps going down, "
     "low-poly isometric 3D game asset",
     "people, cars"),

    ("traffic_light",
     "Modern traffic signal light pole, Chinese city intersection, "
     "tall grey metal pole, horizontal arm with three-light signal head, "
     "red yellow green LED lights, pedestrian crossing button box, "
     "low-poly isometric 3D game asset, isolated, no ground plane",
     "people, buildings, cars, background"),

    ("road_sign",
     "Chinese city road direction sign, blue rectangular sign board, "
     "white text and arrows, mounted on grey metal pole, "
     "low-poly isometric 3D game asset, isolated, no ground plane",
     "people, buildings, cars, background"),

    ("street_lamp",
     "Modern Chinese city street lamp, tall dark grey metal pole, "
     "curved arm at top with warm LED light fixture, "
     "low-poly isometric 3D game asset, isolated, no ground plane",
     "people, buildings, cars, background"),

    ("bench",
     "Chinese city park bench, wooden slat seat and backrest, "
     "black cast iron armrests and legs, simple elegant design, "
     "low-poly isometric 3D game asset, isolated, no ground plane",
     "people, buildings, cars, background"),
]


def headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def create_task(name: str, prompt: str, neg_prompt: str) -> str:
    """Submit a text-to-3D task and return the task_id."""
    body = {
        "mode": "preview",          # preview = faster; use "refine" for HQ
        "prompt": prompt,
        "negative_prompt": neg_prompt,
        "art_style": "realistic",   # "realistic" or "sculpture" — "low-poly" removed
        "should_remesh": True,
        "topology": "triangle",
        "target_polycount": 10000,
        "symmetry_mode": "off",     # was "symmetry"
        "ai_model": "meshy-5",      # "latest", "meshy-6", or "meshy-5"
    }
    r = requests.post(f"{BASE_URL}/openapi/v2/text-to-3d", headers=headers(), json=body, timeout=30)
    r.raise_for_status()
    task_id = r.json()["result"]
    return task_id


def poll_task(task_id: str, timeout: int = 600) -> dict:
    """Poll until task succeeds or fails. Returns the full task dict."""
    deadline = time.time() + timeout
    interval = 10
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/openapi/v2/text-to-3d/{task_id}", headers=headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status", "")
        pct    = data.get("progress", 0)
        print(f"    status={status} progress={pct}%", end="\r", flush=True)
        if status == "SUCCEEDED":
            print()
            return data
        if status in ("FAILED", "EXPIRED"):
            raise RuntimeError(f"Task {task_id} ended with status={status}: {data.get('task_error')}")
        time.sleep(interval)
    raise TimeoutError(f"Task {task_id} did not finish within {timeout}s")


def download_glb(url: str, dest: str):
    """Download the GLB file."""
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)


def generate_one(name: str, prompt: str, neg_prompt: str, out_dir: str, dry_run: bool):
    dest = os.path.join(out_dir, f"{name}.glb")
    if os.path.exists(dest):
        print(f"  [{name}] already exists, skip")
        return

    if dry_run:
        print(f"  [{name}] DRY-RUN — would submit")
        return

    print(f"  [{name}] submitting …")
    for attempt in range(3):
        try:
            task_id = create_task(name, prompt, neg_prompt)
            print(f"    task_id={task_id}")
            task = poll_task(task_id)
            glb_url = task["model_urls"].get("glb") or task["model_urls"].get("fbx")
            if not glb_url:
                raise RuntimeError(f"No GLB URL in response: {task['model_urls']}")
            print(f"    downloading …")
            download_glb(glb_url, dest)
            size_kb = os.path.getsize(dest) // 1024
            print(f"  [{name}] ✓  {size_kb} KB → {dest}")
            return
        except Exception as e:
            print(f"\n    attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(15)
    print(f"  [{name}] ✗  FAILED after 3 attempts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", default=None, help="Generate only this model name")
    args = parser.parse_args()

    os.makedirs(OUT_DIR_BUILDINGS, exist_ok=True)
    os.makedirs(OUT_DIR_FURNITURE, exist_ok=True)

    specs = MODEL_SPECS
    if args.only:
        specs = [s for s in MODEL_SPECS if s[0] == args.only]
        if not specs:
            sys.exit(f"Unknown model: {args.only}")

    print(f"Meshy.ai Text-to-3D — {len(specs)} models")
    print(f"  Buildings → {OUT_DIR_BUILDINGS}")
    print(f"  Furniture → {OUT_DIR_FURNITURE}")
    print(f"Dry run: {args.dry_run}\n")

    for name, prompt, neg_prompt in specs:
        out_dir = OUT_DIR_FURNITURE if name in FURNITURE_NAMES else OUT_DIR_BUILDINGS
        generate_one(name, prompt, neg_prompt, out_dir, args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
