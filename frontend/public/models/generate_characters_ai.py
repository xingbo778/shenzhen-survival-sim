"""
generate_characters_ai.py
Generate 3D character GLB files via Meshy.ai Image-to-3D API.

Extracts the front-facing frame from each 2D sprite sheet and sends it
to Meshy's image-to-3D endpoint to produce a textured 3D character model.

Usage:
  python3 generate_characters_ai.py
  python3 generate_characters_ai.py --dry-run
  python3 generate_characters_ai.py --only startup
"""

import argparse
import base64
import io
import os
import sys
import time

for pkg in ("requests", "PIL"):
    try:
        __import__(pkg)
    except ImportError:
        sys.exit(f"Missing: pip install requests Pillow")

import requests
from PIL import Image

API_KEY  = os.getenv("MESHY_API_KEY", "msy_H9GSONfl0RE7Xxnywt4FVAyliGnUFJm9FlzF")
BASE_URL = "https://api.meshy.ai"
SPRITES_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "client", "public", "sprites", "characters")
OUT_DIR     = os.path.join(os.path.dirname(__file__), "..", "..", "client", "public", "models", "characters")

CHARACTERS = [
    "waimai", "coder", "uncle", "trader", "office",
    "runner", "startup", "drifter", "dancer", "guard", "reporter",
]

CELL_W, CELL_H = 256, 256


def headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}


def extract_front_frame(name: str) -> str:
    """Extract the front-facing frame (first cell) from a sprite sheet and return as base64 data URI."""
    sheet_path = os.path.join(SPRITES_DIR, f"{name}.png")
    if not os.path.exists(sheet_path):
        raise FileNotFoundError(f"Sprite sheet not found: {sheet_path}")

    sheet = Image.open(sheet_path)
    # Front facing is the first cell (col=0, row=0)
    frame = sheet.crop((0, 0, CELL_W, CELL_H))

    # Upscale 2x for better Meshy results
    frame = frame.resize((CELL_W * 2, CELL_H * 2), Image.LANCZOS)

    buf = io.BytesIO()
    frame.save(buf, format="PNG")
    b64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{b64}"


def create_task(image_data_uri: str, name: str) -> str:
    """Submit an image-to-3D task and return the task_id."""
    body = {
        "image_url": image_data_uri,
        "ai_model": "meshy-5",
        "should_texture": True,
        "enable_pbr": True,
        "topology": "triangle",
        "target_polycount": 10000,
        "should_remesh": True,
    }
    r = requests.post(f"{BASE_URL}/openapi/v1/image-to-3d", headers=headers(), json=body, timeout=60)
    r.raise_for_status()
    return r.json()["result"]


def poll_task(task_id: str, timeout: int = 900) -> dict:
    """Poll until task succeeds or fails."""
    deadline = time.time() + timeout
    interval = 10
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/openapi/v1/image-to-3d/{task_id}", headers=headers(), timeout=30)
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


def generate_one(name: str, dry_run: bool):
    dest = os.path.join(OUT_DIR, f"{name}.glb")
    if os.path.exists(dest):
        print(f"  [{name}] already exists, skip")
        return

    if dry_run:
        print(f"  [{name}] DRY-RUN — would submit image-to-3D")
        return

    print(f"  [{name}] extracting front frame …")
    try:
        data_uri = extract_front_frame(name)
    except FileNotFoundError as e:
        print(f"  [{name}] SKIP — {e}")
        return

    print(f"  [{name}] submitting to Meshy image-to-3D …")
    for attempt in range(3):
        try:
            task_id = create_task(data_uri, name)
            print(f"    task_id={task_id}")
            task = poll_task(task_id)

            glb_url = task.get("model_urls", {}).get("glb")
            if not glb_url:
                raise RuntimeError(f"No GLB URL in response: {task.get('model_urls')}")

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
    parser.add_argument("--only", default=None, help="Generate only this character")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    chars = CHARACTERS
    if args.only:
        chars = [c for c in CHARACTERS if c == args.only]
        if not chars:
            sys.exit(f"Unknown character: {args.only}. Available: {CHARACTERS}")

    print(f"Meshy.ai Image-to-3D — {len(chars)} characters")
    print(f"Sprites: {SPRITES_DIR}")
    print(f"Output:  {OUT_DIR}")
    print(f"Dry run: {args.dry_run}\n")

    for name in chars:
        generate_one(name, args.dry_run)

    print("\nDone.")


if __name__ == "__main__":
    main()
