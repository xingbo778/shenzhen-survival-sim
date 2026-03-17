#!/usr/bin/env python3
"""
Building Texture Generator — Shenzhen Pixel City
=================================================
Generates facade and roof textures for BoxGeometry buildings
using the Compass Gemini/Imagen API.

Output: buildings/textures/{name}_facade.png  (256×512)
        buildings/textures/{name}_roof.png    (256×256)

Usage:
  export COMPASS_API_KEY=<key>
  python3.11 generate_textures_ai.py
  python3.11 generate_textures_ai.py --only office_tower
  python3.11 generate_textures_ai.py --dry-run
"""

import os, sys, json, base64, argparse, time, io
from pathlib import Path

for pkg in ("requests", "PIL"):
    try:
        __import__(pkg)
    except ImportError:
        sys.exit(f"Missing: pip install requests Pillow")

import requests
from PIL import Image, ImageDraw

BASE_URL = "https://compass.llm.shopee.io/compass-api/v1"
API_KEY  = os.getenv("COMPASS_API_KEY", "")
OUT_DIR  = Path(__file__).parent / "buildings" / "textures"

FACADE_W, FACADE_H = 256, 512
ROOF_W, ROOF_H     = 256, 256

# ── API helpers (from generate_sprites_ai.py) ────────────────────────────────

def _headers():
    return {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

def _call_gemini(prompt: str, model: str) -> bytes:
    url = f"{BASE_URL}/models/{model}:generateContent"
    body = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }
    r = requests.post(url, headers=_headers(), json=body, timeout=90)
    r.raise_for_status()
    data = r.json()
    for cand in data.get("candidates", []):
        for part in cand.get("content", {}).get("parts", []):
            inline = part.get("inlineData") or part.get("inline_data")
            if inline:
                return base64.b64decode(inline["data"])
    raise RuntimeError(f"No image in response: {json.dumps(data)[:400]}")

def _call_imagen(prompt: str, model: str) -> bytes:
    url = f"{BASE_URL}/models/{model}:predict"
    body = {"instances": [{"prompt": prompt}], "parameters": {"sampleCount": 1}}
    r = requests.post(url, headers=_headers(), json=body, timeout=90)
    r.raise_for_status()
    data = r.json()
    for pred in data.get("predictions", []):
        b64 = pred.get("bytesBase64Encoded")
        if b64:
            return base64.b64decode(b64)
    raise RuntimeError(f"No image in Imagen response: {json.dumps(data)[:400]}")

def fetch_image(prompt: str, model: str) -> Image.Image:
    if model.startswith("imagen-"):
        raw = _call_imagen(prompt, model)
    else:
        raw = _call_gemini(prompt, model)
    return Image.open(io.BytesIO(raw)).convert("RGBA")

# ── Texture specs ─────────────────────────────────────────────────────────────

TEXTURE_SPECS = {
    # ── Office towers ────────────────────────────────────────────────────────
    "office_tower": {
        "facade": (
            "Seamless tileable texture of a modern glass curtain wall skyscraper facade. "
            "Deep blue reflective glass panels in a grid pattern, thin silver aluminum mullions, "
            "some panels reflecting sky. Pixel art style, 8-bit aesthetic, clean lines. "
            "The texture must tile seamlessly left-right. Dark background between panels."
        ),
        "roof": (
            "Top-down view of a skyscraper rooftop. Grey concrete surface, "
            "two HVAC units, a helipad H marking in white, antenna mast, "
            "safety railing around edges. Pixel art style, 8-bit aesthetic."
        ),
    },
    "office_tower_v1": {
        "facade": (
            "Seamless tileable texture of an eco-friendly office tower facade. "
            "Green-tinted glass panels, vertical green plant wall strip on one side, "
            "thin dark frames. Pixel art style, 8-bit aesthetic, clean grid pattern."
        ),
        "roof": (
            "Top-down view of a green office rooftop. Rooftop garden patches, "
            "solar panels in rows, grey concrete walkways. Pixel art style."
        ),
    },
    "office_tower_v2": {
        "facade": (
            "Seamless tileable texture of a silver metallic skyscraper facade. "
            "Reflective chrome panels, horizontal window bands, "
            "brushed steel cladding. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a modern skyscraper rooftop. Communication dishes, "
            "glass skylight panels, grey concrete. Pixel art style."
        ),
    },
    "office_tower_v3": {
        "facade": (
            "Seamless tileable texture of a Shenzhen CBD double-skin glass tower facade. "
            "Floor-to-ceiling blue-grey glass curtain wall, ultra-thin white aluminum frame, "
            "subtle horizontal sunshade louvers between every 2 floors. "
            "Some windows show warm interior light. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a luxury office tower rooftop in Shenzhen. "
            "Helicopter landing pad, antenna array, glass skylight strip. Pixel art style."
        ),
    },
    "office_tower_v4": {
        "facade": (
            "Seamless tileable texture of a contemporary Shenzhen high-tech park tower facade. "
            "Dark charcoal grey glass panels with bright LED accent strips between floors, "
            "vertical fin-like aluminum sunshades on alternating bays. "
            "Clean geometric pattern. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a tech park tower rooftop. Solar panel array, "
            "telecom base station, grey concrete. Pixel art style."
        ),
    },
    "office_tower_v5": {
        "facade": (
            "Seamless tileable texture of a Shenzhen Futian super-tall office tower facade. "
            "Diamond-pattern structural glass with visible diagonal bracing in white steel, "
            "blue-tinted reflective glass, parametric facade geometry. "
            "Pixel art style, 8-bit aesthetic, futuristic modern."
        ),
        "roof": (
            "Top-down view of a supertall tower rooftop. Spire base, maintenance crane, "
            "aircraft warning lights, steel grey surface. Pixel art style."
        ),
    },

    # ── CBD buildings ────────────────────────────────────────────────────────
    "cbd_building": {
        "facade": (
            "Seamless tileable texture of a teal-blue corporate highrise facade. "
            "Dark teal glass windows in regular grid, concrete frame between floors, "
            "some lit windows glowing warm yellow. Pixel art style, 8-bit."
        ),
        "roof": (
            "Top-down view of a corporate building rooftop. HVAC units in corners, "
            "grey flat concrete, small maintenance shed. Pixel art style."
        ),
    },
    "cbd_building_v1": {
        "facade": (
            "Seamless tileable texture of a cool grey steel office block facade. "
            "Flat grey glass windows, silver steel frame, horizontal bands. "
            "Pixel art style, 8-bit aesthetic, industrial modern look."
        ),
        "roof": (
            "Top-down view of an office rooftop. Mechanical floor equipment, "
            "grey concrete, pipe runs. Pixel art style."
        ),
    },
    "cbd_building_v2": {
        "facade": (
            "Seamless tileable texture of a warm gold-tan corporate tower facade. "
            "Bronze-tinted windows, tan sandstone cladding between floors, "
            "horizontal window bands. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a building rooftop. Tan concrete, "
            "two air conditioning units, water tank. Pixel art style."
        ),
    },
    "cbd_building_v3": {
        "facade": (
            "Seamless tileable texture of a Shenzhen Futian mixed-use tower facade. "
            "Lower floors: stone-clad podium with large retail windows and metal canopy. "
            "Upper floors: light grey glass curtain wall with slim white mullions. "
            "Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a mixed-use tower rooftop. Grey concrete, "
            "HVAC cluster, water tank, green planter strip. Pixel art style."
        ),
    },
    "cbd_building_v4": {
        "facade": (
            "Seamless tileable texture of a Shenzhen modern corporate headquarters facade. "
            "All-glass unitized curtain wall, champagne gold aluminum frames, "
            "triple-glazed panels reflecting sky. Every 4th floor has a recessed shadow gap. "
            "Pixel art style, 8-bit aesthetic, premium corporate feel."
        ),
        "roof": (
            "Top-down view of corporate HQ rooftop. Rooftop garden with grass, "
            "glass conference room skylight, antenna mast. Pixel art style."
        ),
    },
    "cbd_building_v5": {
        "facade": (
            "Seamless tileable texture of a white minimalist Shenzhen office facade. "
            "White aluminum composite panel cladding, narrow horizontal ribbon windows, "
            "clean modernist grid, subtle shadow lines. "
            "Pixel art style, 8-bit aesthetic, Bauhaus-inspired."
        ),
        "roof": (
            "Top-down view of a minimalist office rooftop. White membrane roof, "
            "recessed mechanical well, clean edges. Pixel art style."
        ),
    },

    # ── Apartment blocks ─────────────────────────────────────────────────────
    "apartment_block": {
        "facade": (
            "Seamless tileable texture of a Chinese residential apartment facade. "
            "Beige plaster walls, regular grid of windows with small balconies, "
            "some with laundry hanging, AC units on walls. Pixel art style, 8-bit."
        ),
        "roof": (
            "Top-down view of apartment rooftop. Water tanks, laundry poles, "
            "satellite dishes, grey concrete. Pixel art style."
        ),
    },
    "apartment_block_v1": {
        "facade": (
            "Seamless tileable texture of a light blue residential apartment facade. "
            "Sky blue-white plaster, regular window grid, small balconies with plants. "
            "Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of apartment rooftop. Clotheslines, water heaters, "
            "light grey concrete. Pixel art style."
        ),
    },
    "apartment_block_v2": {
        "facade": (
            "Seamless tileable texture of a salmon pink apartment facade. "
            "Warm pink plaster walls, windows with green planters on balconies, "
            "AC outdoor units. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of apartment rooftop. Pink-grey concrete, "
            "potted plants, water tanks. Pixel art style."
        ),
    },
    "apartment_block_v3": {
        "facade": (
            "Seamless tileable texture of a modern Shenzhen high-rise residential facade. "
            "Warm grey stone-look cladding, large floor-to-ceiling windows, "
            "glass-railed balconies with occasional green plants, "
            "slim AC units. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a modern residential rooftop. Rooftop garden, "
            "children play area, grey concrete path. Pixel art style."
        ),
    },
    "apartment_block_v4": {
        "facade": (
            "Seamless tileable texture of a Shenzhen affordable housing tower facade. "
            "Yellow-ochre plaster walls, uniform rows of small windows with AC units, "
            "enclosed balconies with frosted glass. Dense grid pattern. "
            "Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of housing tower rooftop. Water tanks, many satellite dishes, "
            "clotheslines, weathered concrete. Pixel art style."
        ),
    },

    # ── Shop buildings ───────────────────────────────────────────────────────
    "shop_building": {
        "facade": (
            "Seamless tileable texture of a Chinese urban shop building facade. "
            "Ground floor: colorful shop awnings (red, blue, green), large display windows. "
            "Upper floor: cream plaster with small windows. Pixel art style, 8-bit."
        ),
        "roof": (
            "Top-down view of a low commercial building rooftop. "
            "AC units cluster, signboard frame, grey concrete. Pixel art style."
        ),
    },
    "shop_building_v1": {
        "facade": (
            "Seamless tileable texture of a terracotta orange shop facade. "
            "Warm orange-red walls, traditional Chinese shop sign banners, "
            "tiled awning over entrance. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a shop rooftop. Terracotta tiles, "
            "small water tank, vent pipes. Pixel art style."
        ),
    },
    "shop_building_v2": {
        "facade": (
            "Seamless tileable texture of a modern minimalist white retail facade. "
            "Clean white walls, floor-to-ceiling glass storefront on ground floor, "
            "simple upper windows. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a modern shop rooftop. White concrete, "
            "sign board mounting, clean surface. Pixel art style."
        ),
    },
    "shop_building_v3": {
        "facade": (
            "Seamless tileable texture of a Shenzhen modern street-level commercial facade. "
            "Ground floor: full-height glass with branded signage and LED lightbox. "
            "Upper floor: grey aluminum panel cladding with narrow windows. "
            "Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a commercial rooftop. Billboard mounting, "
            "small AC units, grey surface. Pixel art style."
        ),
    },

    # ── Village buildings ────────────────────────────────────────────────────
    "village_building": {
        "facade": (
            "Seamless tileable texture of a Shenzhen urban village handshake building facade. "
            "Grey plaster exterior, small cramped windows on every floor, "
            "AC units mounted on walls, exposed pipes, weathered stains. "
            "Pixel art style, 8-bit aesthetic, gritty urban feel."
        ),
        "roof": (
            "Top-down view of an urban village rooftop. Cluttered with water tanks, "
            "satellite dish, laundry poles, exposed wiring. Pixel art style."
        ),
    },
    "village_building_v1": {
        "facade": (
            "Seamless tileable texture of a warm orange-clay urban village building. "
            "Terracotta-tinted plaster, small windows, old AC units, "
            "faded shop signs on ground floor. Pixel art style, 8-bit."
        ),
        "roof": (
            "Top-down view of an old village rooftop. Terracotta fragments, "
            "tangled wires, water barrel. Pixel art style."
        ),
    },
    "village_building_v2": {
        "facade": (
            "Seamless tileable texture of an aged green-stained urban village building. "
            "Grey plaster with green moss stains, worn windows, old AC units, "
            "faded signage. Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a weathered village rooftop. Mossy patches, "
            "broken antenna, old water tank. Pixel art style."
        ),
    },
    "village_building_v3": {
        "facade": (
            "Seamless tileable texture of a Shenzhen urban village 握手楼 handshake building. "
            "Narrow tall building, closely packed small windows with iron bars, "
            "many window-mounted AC units, exposed water pipes running down the wall, "
            "faded paint and plaster, neon shop signs at ground level. "
            "Pixel art style, 8-bit aesthetic, dense urban feel."
        ),
        "roof": (
            "Top-down view of an urban village handshake building rooftop. "
            "Cramped with water tanks, tangled wires, drying racks, corrugated sheets. "
            "Pixel art style."
        ),
    },

    # ── Trees (use facade as bark, roof as canopy top-down) ──────────────────
    "palm_tree": {
        "facade": (
            "Seamless tileable texture of a tropical palm tree trunk. "
            "Brown fibrous bark with horizontal ring patterns. "
            "Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a palm tree canopy. Radiating green fronds "
            "from center, dark shadows between leaves. Pixel art style."
        ),
    },
    "street_tree": {
        "facade": (
            "Seamless tileable texture of a deciduous tree trunk. "
            "Brown rough bark with vertical cracks. "
            "Pixel art style, 8-bit aesthetic."
        ),
        "roof": (
            "Top-down view of a round tree canopy. Dense green foliage, "
            "lighter highlights in center, darker edges. Pixel art style."
        ),
    },

    # ── Metro entrance ───────────────────────────────────────────────────────
    "metro_entrance": {
        "facade": (
            "Seamless tileable texture of a Shenzhen Metro entrance wall. "
            "Dark green panels with red illuminated 地铁 sign, "
            "glass windscreen panels, stainless steel frame. Pixel art style."
        ),
        "roof": (
            "Top-down view of a metro entrance canopy roof. "
            "Dark green metal roof panels, drainage channels. Pixel art style."
        ),
    },
}


def generate_texture(name: str, kind: str, prompt: str, size: tuple, model: str, dry_run: bool):
    """Generate a single texture image."""
    dest = OUT_DIR / f"{name}_{kind}.png"
    if dest.exists():
        print(f"    [{name}_{kind}] already exists, skip")
        return

    if dry_run:
        print(f"    [{name}_{kind}] DRY-RUN")
        return

    full_prompt = (
        f"Generate a {size[0]}x{size[1]} pixel art texture image. "
        f"This is a TEXTURE MAP for a 3D building, not a scene. "
        f"It must fill the entire image with NO background, NO border, NO margin. "
        f"{prompt}"
    )

    for attempt in range(3):
        try:
            img = fetch_image(full_prompt, model)
            img = img.resize(size, Image.LANCZOS)
            img.save(str(dest))
            print(f"    [{name}_{kind}] OK  → {dest.name}")
            return
        except Exception as e:
            print(f"    [{name}_{kind}] attempt {attempt+1} failed: {e}")
            if attempt < 2:
                time.sleep(5)

    print(f"    [{name}_{kind}] FAILED after 3 attempts")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", default=None, help="Generate only this building type")
    parser.add_argument("--model", default="gemini-2.5-flash-image")
    args = parser.parse_args()

    if not args.dry_run and not API_KEY:
        sys.exit("Set COMPASS_API_KEY environment variable")

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    specs = TEXTURE_SPECS
    if args.only:
        if args.only not in specs:
            sys.exit(f"Unknown type: {args.only}. Available: {', '.join(specs.keys())}")
        specs = {args.only: specs[args.only]}

    total = len(specs) * 2
    print(f"Building Texture Generator — {len(specs)} types × 2 = {total} textures")
    print(f"Model: {args.model}  Dry run: {args.dry_run}\n")

    for name, prompts in specs.items():
        print(f"  [{name}]")
        generate_texture(name, "facade", prompts["facade"], (FACADE_W, FACADE_H), args.model, args.dry_run)
        generate_texture(name, "roof",   prompts["roof"],   (ROOF_W, ROOF_H),     args.model, args.dry_run)

    print(f"\nDone. Output: {OUT_DIR}")


if __name__ == "__main__":
    main()
