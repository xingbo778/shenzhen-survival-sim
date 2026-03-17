#!/usr/bin/env python3
"""
Step 1: Extract individual vehicle images from vehicles_v2.png
Step 2: Send them to Meshy AI Image-to-3D to generate GLB models

vehicles_v2.png layout (768x576, 6 rows x 4 cols, ~192x96 per cell):
  Row 0: taxi (blue)        — 4 frames
  Row 1: sweeper (red)      — 4 frames
  Row 2: huolala (yellow)   — 4 frames
  Row 3: meituan (scooter)  — 4 frames
  Row 4: shared_bike        — 4 frames
  Row 5: bus (green)        — 4 frames

Usage:
  export MESHY_API_KEY=msy_xxxxx
  python3 extract_and_generate.py               # extract + generate all
  python3 extract_and_generate.py --extract-only # just extract PNGs
  python3 extract_and_generate.py --only taxi    # generate one vehicle
"""

import os, sys, json, base64, argparse, time
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    sys.exit("Missing: pip install Pillow")

try:
    import requests
except ImportError:
    sys.exit("Missing: pip install requests")

SCRIPT_DIR = Path(__file__).parent
SRC_IMAGE  = SCRIPT_DIR.parent.parent / "vehicles_v2.png"
OUT_DIR    = SCRIPT_DIR / "models"

API_KEY  = os.getenv("MESHY_API_KEY", "")
BASE_URL = "https://api.meshy.ai/openapi/v1"

ROWS = {
    0: "taxi",
    1: "sweeper",
    2: "huolala",
    3: "meituan",
    4: "shared_bike",
    5: "bus",
}

TEXTURE_PROMPTS = {
    "taxi":        "Shenzhen blue taxi cab, light blue body with dark blue roof, gray windshield, low-poly cartoon style, clean colors",
    "sweeper":     "Red street sweeper vehicle, dark body, red accents, gray windshield, low-poly cartoon style",
    "huolala":     "Huolala cargo truck, bright yellow body, orange cargo box, low-poly cartoon style",
    "meituan":     "Meituan delivery scooter, yellow helmet rider, orange delivery box, black scooter, low-poly cartoon style",
    "shared_bike": "Shared bicycle with rider, blue bicycle frame, person riding, low-poly cartoon style",
    "bus":         "Shenzhen city bus, dark green body, gray windows, long vehicle, low-poly cartoon style",
}


def extract_vehicles():
    """Extract the first frame of each vehicle row as a standalone PNG."""
    if not SRC_IMAGE.exists():
        sys.exit(f"Source image not found: {SRC_IMAGE}")

    img = Image.open(SRC_IMAGE).convert("RGBA")
    w, h = img.size
    cell_w = w // 4
    cell_h = h // 6

    print(f"Source: {SRC_IMAGE} ({w}x{h}), cell={cell_w}x{cell_h}")

    extracted = {}
    for row_idx, name in ROWS.items():
        x0 = 0
        y0 = row_idx * cell_h
        x1 = x0 + cell_w
        y1 = y0 + cell_h

        frame = img.crop((x0, y0, x1, y1))
        bbox = frame.getbbox()
        if bbox:
            frame = frame.crop(bbox)

        out_path = SCRIPT_DIR / f"{name}.png"
        frame.save(out_path)
        extracted[name] = out_path
        print(f"  Extracted {name}.png ({frame.size[0]}x{frame.size[1]})")

    return extracted


def _headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def image_to_base64_uri(path: Path) -> str:
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    return f"data:image/png;base64,{b64}"


def create_task(name: str, img_path: Path) -> str:
    data_uri = image_to_base64_uri(img_path)
    prompt = TEXTURE_PROMPTS.get(name, "low-poly cartoon vehicle")

    body = {
        "image_url": data_uri,
        "model_type": "lowpoly",
        "should_texture": True,
        "texture_prompt": prompt,
        "enable_pbr": False,
    }

    r = requests.post(f"{BASE_URL}/image-to-3d", headers=_headers(), json=body, timeout=60)
    r.raise_for_status()
    result = r.json()
    task_id = result.get("result")
    if not task_id:
        raise RuntimeError(f"No task ID: {json.dumps(result)[:400]}")
    return task_id


def poll_task(task_id: str, timeout_s: int = 600, poll_interval: int = 15) -> dict:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = requests.get(f"{BASE_URL}/image-to-3d/{task_id}", headers=_headers(), timeout=30)
        r.raise_for_status()
        task = r.json()
        status = task.get("status", "")
        progress = task.get("progress", 0)
        print(f"      status={status}  progress={progress}%")

        if status == "SUCCEEDED":
            return task
        if status in ("FAILED", "CANCELED"):
            err = task.get("task_error", {}).get("message", status)
            raise RuntimeError(f"Task {status}: {err}")

        time.sleep(poll_interval)

    raise TimeoutError(f"Task {task_id} timed out")


def download_glb(task: dict, dest: Path):
    glb_url = task.get("model_urls", {}).get("glb")
    if not glb_url:
        raise RuntimeError("No GLB URL in result")

    r = requests.get(glb_url, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    print(f"      Downloaded → {dest.name} ({len(r.content)/1024:.0f} KB)")


def generate_one(name: str, img_path: Path):
    dest = OUT_DIR / f"{name}.glb"
    if dest.exists():
        print(f"    [{name}] GLB already exists, skip")
        return

    if not img_path.exists():
        print(f"    [{name}] No source PNG, skip")
        return

    print(f"    [{name}] Submitting to Meshy...")
    try:
        task_id = create_task(name, img_path)
        print(f"      Task ID: {task_id}")
        task = poll_task(task_id)
        download_glb(task, dest)
        print(f"    [{name}] OK")
    except Exception as e:
        print(f"    [{name}] FAILED: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--extract-only", action="store_true")
    parser.add_argument("--only", default=None)
    parser.add_argument("--skip-extract", action="store_true")
    args = parser.parse_args()

    if not args.skip_extract:
        print("=== Step 1: Extract vehicle sprites ===\n")
        extract_vehicles()
        print()

    if args.extract_only:
        print("Done (extract only).")
        return

    if not API_KEY:
        sys.exit("Set MESHY_API_KEY env var first")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    names = list(ROWS.values())
    if args.only:
        if args.only not in names:
            sys.exit(f"Unknown: {args.only}. Available: {', '.join(names)}")
        names = [args.only]

    print(f"=== Step 2: Generate 3D models ({len(names)} vehicles) ===\n")
    for name in names:
        img_path = SCRIPT_DIR / f"{name}.png"
        generate_one(name, img_path)

    print(f"\nDone. Models in: {OUT_DIR}")


if __name__ == "__main__":
    main()
