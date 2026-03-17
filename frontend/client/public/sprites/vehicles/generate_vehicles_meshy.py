#!/usr/bin/env python3
"""
Vehicle 3D Model Generator — Meshy AI Image-to-3D
===================================================
Generates low-poly GLB 3D vehicle models from the reference sprite images
in /sprites/vehicles/ using Meshy AI's Image-to-3D API.

Output: models/{name}.glb

Usage:
  export MESHY_API_KEY=msy_xxxxx
  python3 generate_vehicles_meshy.py
  python3 generate_vehicles_meshy.py --only taxi
  python3 generate_vehicles_meshy.py --dry-run
"""

import os, sys, json, base64, argparse, time
from pathlib import Path

try:
    import requests
except ImportError:
    sys.exit("Missing: pip install requests")

API_KEY  = os.getenv("MESHY_API_KEY", "")
BASE_URL = "https://api.meshy.ai/openapi/v1"
SCRIPT_DIR = Path(__file__).parent
OUT_DIR    = SCRIPT_DIR / "models"

VEHICLE_SPECS = {
    "taxi": {
        "image": "taxi.png",
        "texture_prompt": "Shenzhen blue taxi cab, light blue body, white lower trim, yellow TAXI roof sign, pixel art style",
    },
    "bus": {
        "image": "bus.png",
        "texture_prompt": "Shenzhen city bus, white lower body, dark navy upper body, blue windows, gold stripe, pixel art style",
    },
    "meituan": {
        "image": "meituan.png",
        "texture_prompt": "Meituan delivery scooter with rider wearing yellow helmet and blue jacket, yellow delivery box on back, pixel art style",
    },
    "huolala": {
        "image": "huolala.png",
        "texture_prompt": "Huolala cargo truck, white cab, orange cargo body with white stripe, pixel art style",
    },
    "sweeper": {
        "image": "sweeper.png",
        "texture_prompt": "Street sweeper vehicle, white body, yellow-green tank, blue warning light on top, red brushes, pixel art style",
    },
    "shared_bike": {
        "image": "shared_bike.png",
        "texture_prompt": "Yellow shared bicycle with rider wearing yellow helmet, pixel art style",
    },
}

def _headers():
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }


def image_to_base64_uri(path: Path) -> str:
    """Convert a local image file to a data URI."""
    data = path.read_bytes()
    b64 = base64.b64encode(data).decode("ascii")
    suffix = path.suffix.lower().lstrip(".")
    mime = "image/png" if suffix == "png" else "image/jpeg"
    return f"data:{mime};base64,{b64}"


def create_task(name: str, spec: dict) -> str:
    """Submit an Image-to-3D task and return the task ID."""
    img_path = SCRIPT_DIR / spec["image"]
    if not img_path.exists():
        raise FileNotFoundError(f"Image not found: {img_path}")

    data_uri = image_to_base64_uri(img_path)

    body = {
        "image_url": data_uri,
        "model_type": "lowpoly",
        "should_texture": True,
        "texture_prompt": spec.get("texture_prompt", ""),
        "enable_pbr": False,
    }

    r = requests.post(f"{BASE_URL}/image-to-3d", headers=_headers(), json=body, timeout=60)
    r.raise_for_status()
    result = r.json()
    task_id = result.get("result")
    if not task_id:
        raise RuntimeError(f"No task ID in response: {json.dumps(result)[:400]}")
    return task_id


def poll_task(task_id: str, timeout_s: int = 600, poll_interval: int = 10) -> dict:
    """Poll until the task is done. Returns the full task object."""
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
        if status == "FAILED":
            err = task.get("task_error", {}).get("message", "unknown error")
            raise RuntimeError(f"Task failed: {err}")
        if status == "CANCELED":
            raise RuntimeError("Task was canceled")

        time.sleep(poll_interval)

    raise TimeoutError(f"Task {task_id} timed out after {timeout_s}s")


def download_glb(task: dict, dest: Path):
    """Download the GLB model from a completed task."""
    glb_url = task.get("model_urls", {}).get("glb")
    if not glb_url:
        raise RuntimeError("No GLB URL in task result")

    r = requests.get(glb_url, timeout=120)
    r.raise_for_status()
    dest.write_bytes(r.content)
    size_kb = len(r.content) / 1024
    print(f"      Downloaded → {dest.name} ({size_kb:.0f} KB)")


def generate_vehicle(name: str, spec: dict, dry_run: bool):
    """Generate a single vehicle 3D model."""
    dest = OUT_DIR / f"{name}.glb"
    if dest.exists():
        print(f"    [{name}] already exists, skip")
        return

    if dry_run:
        print(f"    [{name}] DRY-RUN (image: {spec['image']})")
        return

    print(f"    [{name}] Submitting task...")
    try:
        task_id = create_task(name, spec)
        print(f"      Task ID: {task_id}")
        print(f"      Polling for completion...")
        task = poll_task(task_id)
        download_glb(task, dest)
        print(f"    [{name}] OK")
    except Exception as e:
        print(f"    [{name}] FAILED: {e}")


def main():
    parser = argparse.ArgumentParser(description="Generate 3D vehicle models via Meshy AI")
    parser.add_argument("--dry-run", action="store_true", help="Print what would be done")
    parser.add_argument("--only", default=None, help="Generate only this vehicle type")
    args = parser.parse_args()

    if not args.dry_run and not API_KEY:
        sys.exit("Set MESHY_API_KEY environment variable (get it from https://www.meshy.ai/settings/api)")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    specs = VEHICLE_SPECS
    if args.only:
        if args.only not in specs:
            sys.exit(f"Unknown vehicle: {args.only}. Available: {', '.join(specs.keys())}")
        specs = {args.only: specs[args.only]}

    print(f"Vehicle 3D Model Generator — {len(specs)} vehicles")
    print(f"Dry run: {args.dry_run}\n")

    for name, spec in specs.items():
        print(f"  [{name}]")
        generate_vehicle(name, spec, args.dry_run)

    print(f"\nDone. Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
