"""
generate_furniture_ai.py
Generate street-furniture GLB files via Meshy.ai Text-to-3D (preview → refine).

Usage:
  python3 generate_furniture_ai.py
  python3 generate_furniture_ai.py --dry-run
  python3 generate_furniture_ai.py --only traffic_light
"""

import argparse
import os
import sys
import time
import requests

API_KEY  = os.getenv("MESHY_API_KEY", "msy_H9GSONfl0RE7Xxnywt4FVAyliGnUFJm9FlzF")
BASE_URL = "https://api.meshy.ai"
OUT_DIR  = os.path.join(os.path.dirname(__file__), "..", "..", "client", "public", "models", "furniture")

FURNITURE_SPECS = [
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

    ("metro_entrance",
     "Shenzhen Metro subway entrance structure, "
     "dark green canopy roof, red illuminated sign, "
     "glass windscreen panels, concrete steps going down, "
     "low-poly isometric 3D game asset",
     "people, cars"),
]


def headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def create_preview(prompt: str, neg_prompt: str) -> str:
    body = {
        "mode": "preview",
        "prompt": prompt,
        "negative_prompt": neg_prompt,
        "ai_model": "meshy-5",
        "topology": "triangle",
        "target_polycount": 10000,
        "should_remesh": True,
    }
    r = requests.post(f"{BASE_URL}/openapi/v2/text-to-3d", headers=headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()["result"]


def create_refine(preview_task_id: str) -> str:
    body = {
        "mode": "refine",
        "preview_task_id": preview_task_id,
        "enable_pbr": True,
    }
    r = requests.post(f"{BASE_URL}/openapi/v2/text-to-3d", headers=headers(), json=body, timeout=30)
    r.raise_for_status()
    return r.json()["result"]


def poll_task(task_id: str, timeout: int = 900) -> dict:
    deadline = time.time() + timeout
    interval = 10
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/openapi/v2/text-to-3d/{task_id}", headers=headers(), timeout=30)
        r.raise_for_status()
        data = r.json()
        status = data.get("status", "")
        pct = data.get("progress", 0)
        print(f"    status={status} progress={pct}%", end="\r", flush=True)
        if status == "SUCCEEDED":
            print()
            return data
        if status in ("FAILED", "EXPIRED", "CANCELED"):
            raise RuntimeError(f"Task {task_id} ended with status={status}: {data.get('task_error')}")
        time.sleep(interval)
    raise TimeoutError(f"Task {task_id} did not finish within {timeout}s")


def download_glb(url: str, dest: str):
    r = requests.get(url, timeout=120, stream=True)
    r.raise_for_status()
    with open(dest, "wb") as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)


def generate_one(name: str, prompt: str, neg_prompt: str, dry_run: bool):
    dest = os.path.join(OUT_DIR, f"{name}.glb")
    if os.path.exists(dest):
        print(f"  [{name}] already exists, skip")
        return

    if dry_run:
        print(f"  [{name}] DRY-RUN — would submit preview + refine")
        return

    print(f"  [{name}] Step 1/2: preview …")
    for attempt in range(3):
        try:
            preview_id = create_preview(prompt, neg_prompt)
            print(f"    preview task_id={preview_id}")
            poll_task(preview_id)

            print(f"  [{name}] Step 2/2: refine …")
            refine_id = create_refine(preview_id)
            print(f"    refine task_id={refine_id}")
            task = poll_task(refine_id)

            glb_url = task.get("model_urls", {}).get("glb")
            if not glb_url:
                raise RuntimeError(f"No GLB URL in refine response: {task.get('model_urls')}")

            print(f"    downloading …")
            download_glb(glb_url, dest)
            size_kb = os.path.getsize(dest) // 1024
            print(f"  [{name}] done  {size_kb} KB -> {dest}")
            return
        except Exception as e:
            print(f"\n    attempt {attempt + 1} failed: {e}")
            if attempt < 2:
                time.sleep(15)
    print(f"  [{name}] FAILED after 3 attempts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", default=None, help="Generate only this model name")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    specs = FURNITURE_SPECS
    if args.only:
        specs = [s for s in FURNITURE_SPECS if s[0] == args.only]
        if not specs:
            sys.exit(f"Unknown model: {args.only}. Available: {[s[0] for s in FURNITURE_SPECS]}")

    print(f"Meshy.ai Text-to-3D (preview → refine) — {len(specs)} furniture models")
    print(f"Output: {OUT_DIR}")
    print(f"Dry run: {args.dry_run}\n")

    for name, prompt, neg_prompt in specs:
        generate_one(name, prompt, neg_prompt, args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
