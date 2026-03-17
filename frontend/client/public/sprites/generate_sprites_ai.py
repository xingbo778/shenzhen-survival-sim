#!/usr/bin/env python3
"""
Hybrid Sprite Generator — Shenzhen Pixel City (Futian CBD style)
================================================================
Strategy:
  • Ground TILES  → PIL procedural drawing (seamless, deterministic, perfect)
  • Scene OBJECTS → Gemini/Imagen AI generation + auto background-removal

Why hybrid?
  - Tiles must be seamlessly tileable; AI tends to draw "scene images" not tiles.
  - Objects (buildings, trees) are isolated sprites; AI produces richer detail.

API: Shopee Compass Gemini proxy  https://compass.llm.shopee.io/compass-api/v1

Usage:
  export COMPASS_API_KEY=<key>
  python3.11 generate_sprites_ai.py                       # full run
  python3.11 generate_sprites_ai.py --tiles-only          # rebuild tiles (no API)
  python3.11 generate_sprites_ai.py --objects-only        # AI objects only
  python3.11 generate_sprites_ai.py --model gemini-3-pro-image-preview
  python3.11 generate_sprites_ai.py --dry-run             # no API calls
"""

import os, sys, json, base64, argparse, time, io, math
from pathlib import Path

# ── third-party ──────────────────────────────────────────────────────────────
for pkg in ("requests", "PIL"):
    try:
        __import__(pkg)
    except ImportError:
        sys.exit(f"Missing: pip install requests Pillow")

import requests
from PIL import Image, ImageDraw, ImageFilter

# ── paths ─────────────────────────────────────────────────────────────────────
BASE_URL  = "https://compass.llm.shopee.io/compass-api/v1"
API_KEY   = os.getenv("COMPASS_API_KEY", "")
SHEET_DIR = Path(__file__).parent

T = 64  # tile size

# ══════════════════════════════════════════════════════════════════════════════
#  PALETTE  (Futian CBD reference)
# ══════════════════════════════════════════════════════════════════════════════
C_ROAD='#2A2A32'; C_ROAD_DARK='#1E1E26'; C_ROAD_GRAIN='#323238'
C_YELLOW='#E8C832'; C_YELLOW_DARK='#C4A828'; C_WHITE_LINE='#D8D8CC'
C_SIDE='#9898A0'; C_SIDE_LIGHT='#ACACB4'; C_SIDE_DARK='#74747C'
C_KERB='#C0C0C8'; C_KERB_DARK='#5A5A62'
C_PLAZA='#C8C4B4'; C_PLAZA_LIGHT='#DEDACC'; C_PLAZA_DARK='#A8A498'; C_PLAZA_SHADOW='#8E8A7A'
C_GRASS='#2A5C22'; C_GRASS_MID='#347028'; C_GRASS_LIGHT='#3E7C30'; C_GRASS_DARK='#1E4418'
C_WATER='#1E4878'; C_WATER_MID='#2A5E92'; C_WATER_LIGHT='#3A78AA'; C_WATER_FOAM='#5A98C0'
C_CONCRETE='#62626A'; C_CONCRETE_L='#74747C'; C_CONCRETE_D='#4A4A52'
C_WOOD='#7A5828'; C_WOOD_LIGHT='#9A7040'; C_WOOD_DARK='#5A3E18'
C_HEDGE='#1E4A14'; C_HEDGE_MID='#2A5E1E'; C_HEDGE_LIGHT='#3A7228'
C_ALLEY='#2E2E28'; C_ALLEY_DARK='#222218'; C_ALLEY_GRAIN='#383830'
C_BLDG_BASE='#12121A'

# ── helpers ───────────────────────────────────────────────────────────────────
def rnd(col, row, s=0):
    v=(col*374761393+row*668265263+s*1234567)&0xFFFFFFFF
    v=((v^(v>>13))*1274126177)&0xFFFFFFFF
    return ((v^(v>>16))&0xFFFFFFFF)/4294967296

def c(hex_color, a=255):
    s=hex_color.lstrip('#')
    return (int(s[0:2],16),int(s[2:4],16),int(s[4:6],16),a)

def lerp_c(c1,c2,t):
    return tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(3))+(255,)

def new(color=None):
    base=c(color) if color else (0,0,0,0)
    img=Image.new('RGBA',(T,T),base)
    return img,ImageDraw.Draw(img)

# ══════════════════════════════════════════════════════════════════════════════
#  TILE DRAWERS  (100% PIL — guaranteed seamless)
# ══════════════════════════════════════════════════════════════════════════════
def tile_road_h():
    img,d=new(C_ROAD)
    for i in range(50): d.point((int(rnd(i,1)*T),int(rnd(1,i)*T)),fill=c(C_ROAD_GRAIN))
    d.rectangle([0,T//2-4,T-1,T//2+3],fill=c('#2E2E36'))
    d.rectangle([0,2,T-1,4],fill=c(C_YELLOW))
    d.rectangle([0,T-5,T-1,T-3],fill=c(C_YELLOW))
    dash_w,gap=10,7; cy=T//2-1; x=0
    while x<T:
        d.rectangle([x,cy,min(x+dash_w-1,T-1),cy+2],fill=c(C_YELLOW)); x+=dash_w+gap
    d.rectangle([0,0,T-1,1],fill=c(C_WHITE_LINE))
    d.rectangle([0,T-2,T-1,T-1],fill=c(C_WHITE_LINE))
    cx0=int(rnd(7,3)*T); d.line([(cx0,8),(cx0+4,22)],fill=c(C_ROAD_DARK),width=1)
    return img

def tile_road_v(): return tile_road_h().rotate(90,expand=False)

def tile_road_cross():
    img,d=new(C_ROAD)
    for i in range(40): d.point((int(rnd(i,2)*T),int(rnd(2,i)*T)),fill=c(C_ROAD_GRAIN))
    SW,SG=6,4
    for (band_y,band_h) in [(0,T//5),(T-T//5,T//5)]:
        x=T*2//10
        while x<T*8//10:
            d.rectangle([x,band_y,x+SW-1,band_y+band_h-1],fill=c(C_YELLOW)); x+=SW+SG
    for (band_x,band_w) in [(0,T//5),(T-T//5,T//5)]:
        y=T*2//10
        while y<T*8//10:
            d.rectangle([band_x,y,band_x+band_w-1,y+SW-1],fill=c(C_YELLOW)); y+=SW+SG
    d.rectangle([0,T//5-2,T-1,T//5+1],fill=c(C_YELLOW))
    d.rectangle([0,T*4//5-2,T-1,T*4//5+1],fill=c(C_YELLOW))
    d.rectangle([T//5-2,0,T//5+1,T-1],fill=c(C_YELLOW))
    d.rectangle([T*4//5-2,0,T*4//5+1,T-1],fill=c(C_YELLOW))
    return img

def tile_sidewalk():
    img,d=new(C_SIDE); TW,TH=T//2,T//3
    for row in range(4):
        for col in range(3):
            ox=(TW//2) if (row%2==1) else 0
            x0=ox+col*TW; y0=row*TH; x1=x0+TW-1; y1=y0+TH-1
            if x0>=T: continue
            x1=min(x1,T-1)
            shade_t=rnd(col*3+row,row*2+col)*0.08
            face=lerp_c(c(C_SIDE),c(C_SIDE_LIGHT),shade_t)
            d.rectangle([x0,y0,x1,y1],fill=face)
            d.rectangle([x0,y0,x1,y0+1],fill=c(C_SIDE_LIGHT))
            d.rectangle([x0,y0,x0+1,y1],fill=c(C_SIDE_LIGHT))
            d.rectangle([x0,y1-1,x1,y1],fill=c(C_SIDE_DARK))
            d.rectangle([x1-1,y0,x1,y1],fill=c(C_SIDE_DARK))
    for row in range(4):
        y=row*TH
        if 0<y<T: d.rectangle([0,y,T-1,y],fill=c(C_SIDE_DARK))
    return img

def tile_sidewalk_edge():
    img,d=new(C_KERB)
    d.rectangle([0,0,T-1,T//4],fill=c(C_KERB))
    d.rectangle([0,0,T-1,2],fill=c('#E0E0E8'))
    d.rectangle([0,T//4,T-1,T-1],fill=c(C_KERB_DARK))
    for y in range(T//4,T,T//8): d.rectangle([0,y,T-1,y],fill=c(C_SIDE_DARK))
    return img

def tile_grass():
    img,d=new(C_GRASS)
    for i in range(80):
        x=int(rnd(i,3)*T); y=int(rnd(3,i)*T)
        col=lerp_c(c(C_GRASS_DARK),c(C_GRASS_MID),rnd(i*2,3+i))
        d.point((x,y),fill=col)
    for i in range(28):
        bx=int(rnd(i*3,7)*(T-4))+2; by=int(rnd(7,i*3)*(T-4))+2
        tip=lerp_c(c(C_GRASS),c(C_GRASS_LIGHT),rnd(i,i+5))
        d.line([(bx-1,by+3),(bx,by)],fill=tip,width=1)
        d.line([(bx+1,by+3),(bx,by)],fill=tip,width=1)
    for i in range(6):
        px=int(rnd(i*9,11)*(T-6))+3; py=int(rnd(11,i*9)*(T-6))+3
        d.rectangle([px,py,px+3,py+2],fill=c(C_GRASS_DARK))
    return img

def tile_grass_lush():
    img=tile_grass(); d=ImageDraw.Draw(img)
    for i in range(15):
        bx=int(rnd(i*5,13)*(T-4))+2; by=int(rnd(13,i*5)*(T-4))+2
        d.line([(bx,by+4),(bx-1,by)],fill=c(C_GRASS_LIGHT),width=1)
        d.line([(bx,by+4),(bx+1,by)],fill=c(C_GRASS_LIGHT),width=1)
    for i in range(4):
        fx=int(rnd(i*11,17)*(T-4))+2; fy=int(rnd(17,i*11)*(T-4))+2
        d.ellipse([fx-2,fy-2,fx+2,fy+2],fill=c('#F0E040'))
        d.point((fx,fy),fill=c('#FFF080'))
    return img

def tile_water():
    img,d=new(C_WATER)
    for row in range(T):
        col=lerp_c(c(C_WATER),c(C_WATER_MID),row/T)
        d.line([(0,row),(T-1,row)],fill=col)
    for wy in range(0,T,10):
        for wx in range(0,T,9):
            wave_y=wy+int(math.sin(wx*0.5)*2)
            if 0<=wave_y<T: d.rectangle([wx,wave_y,wx+5,wave_y],fill=c(C_WATER_LIGHT))
    for i in range(8):
        sx=int(rnd(i*7,5)*T); sy=int(rnd(5,i*7)*T)
        d.rectangle([sx,sy,sx+3,sy],fill=c(C_WATER_FOAM,200))
    d.rectangle([0,T-3,T-1,T-1],fill=c(C_WATER))
    return img

def tile_water_edge():
    img=tile_water(); d=ImageDraw.Draw(img)
    for y in range(8): d.rectangle([0,y,T-1,y],fill=c(C_WATER_LIGHT,180-y*20))
    for i in range(10):
        x=int(rnd(i*4,9)*(T-4))+2
        d.ellipse([x-2,1,x+2,4],fill=c(C_WATER_FOAM,160))
    return img

def tile_concrete():
    img,d=new(C_CONCRETE)
    d.rectangle([T//2-1,0,T//2+1,T-1],fill=c(C_CONCRETE_D))
    d.rectangle([0,T//2-1,T-1,T//2+1],fill=c(C_CONCRETE_D))
    for i in range(25): d.point((int(rnd(i,6)*T),int(rnd(6,i)*T)),fill=c(C_CONCRETE_D))
    for (qx,qy) in ((2,2),(T//2+2,2),(2,T//2+2),(T//2+2,T//2+2)):
        d.rectangle([qx,qy,qx+T//2-6,qy+2],fill=c(C_CONCRETE_L))
        d.rectangle([qx,qy,qx+2,qy+T//2-6],fill=c(C_CONCRETE_L))
    d.rectangle([0,T-3,T-1,T-1],fill=c(C_CONCRETE_D))
    return img

def tile_tile_plaza():
    img,d=new(C_PLAZA); HT=T//2
    for (tx,ty) in ((0,0),(HT,0),(0,HT),(HT,HT)):
        for ry in range(HT):
            row_c=lerp_c(c(C_PLAZA_LIGHT),c(C_PLAZA),ry/HT*0.15)
            d.rectangle([tx+1,ty+ry,tx+HT-2,ty+ry],fill=row_c)
        d.rectangle([tx,ty,tx+HT-1,ty+1],fill=c(C_PLAZA_LIGHT))
        d.rectangle([tx,ty,tx+1,ty+HT-1],fill=c(C_PLAZA_LIGHT))
        d.rectangle([tx,ty+HT-2,tx+HT-1,ty+HT-1],fill=c(C_PLAZA_SHADOW))
        d.rectangle([tx+HT-2,ty,tx+HT-1,ty+HT-1],fill=c(C_PLAZA_SHADOW))
        vx=int(rnd(tx,ty)*HT//2)+tx+4; vy=ty+4
        d.line([(vx,vy),(vx+6,vy+10)],fill=c(C_PLAZA_DARK,100),width=1)
    d.rectangle([0,HT-1,T-1,HT+1],fill=c(C_PLAZA_DARK))
    d.rectangle([HT-1,0,HT+1,T-1],fill=c(C_PLAZA_DARK))
    return img

def tile_building():
    img,d=new(C_BLDG_BASE)
    for i in range(20): d.point((int(rnd(i,8)*T),int(rnd(8,i)*T)),fill=c('#1A1A22'))
    return img

def tile_park_path():
    img,d=new(C_WOOD); PH=T//5
    for idx in range(5):
        y0=idx*PH
        shade=lerp_c(c(C_WOOD_DARK),c(C_WOOD_LIGHT),rnd(idx,2)*0.6+0.2)
        d.rectangle([0,y0,T-1,y0+PH-2],fill=shade)
        d.rectangle([0,y0,T-1,y0+1],fill=c(C_WOOD_LIGHT))
        for gi in range(2):
            gx=int(rnd(idx*3+gi,4)*(T-4))+2
            d.line([(gx,y0+2),(gx+int(rnd(gi,idx)*10),y0+PH-3)],fill=c(C_WOOD_DARK),width=1)
        d.rectangle([0,y0+PH-2,T-1,y0+PH-1],fill=c(C_WOOD_DARK))
    return img

def tile_fence_green():
    img,d=new(C_HEDGE)
    for i in range(70):
        x=int(rnd(i*3,9)*(T-2))+1; y=int(rnd(9,i*3)*(T-2))+1
        d.point((x,y),fill=lerp_c(c(C_HEDGE),c(C_HEDGE_MID),rnd(i,i+4)))
    for i in range(9):
        bx=int(rnd(i*6,11)*(T-12))+6; by=int(rnd(11,i*6)*(T-12))+6
        r=int(rnd(i,i+7)*4)+4
        d.ellipse([bx-r,by-r,bx+r,by+r],fill=c(C_HEDGE_MID,200))
        d.point((bx-1,by-1),fill=c(C_HEDGE_LIGHT))
    d.rectangle([0,T-4,T-1,T-1],fill=c(C_HEDGE,180))
    return img

def tile_alley():
    img,d=new(C_ALLEY)
    for i in range(40): d.point((int(rnd(i*4,13)*T),int(rnd(13,i*4)*T)),fill=c(C_ALLEY_GRAIN))
    d.rectangle([0,0,3,T-1],fill=c(C_ALLEY_DARK))
    d.rectangle([T-4,0,T-1,T-1],fill=c(C_ALLEY_DARK))
    cx=T//2+int(rnd(5,3)*6)-3
    d.line([(cx,4),(cx+2,T-5)],fill=c(C_ALLEY_DARK),width=1)
    d.ellipse([T//4,T//2,T*3//4,T*3//4],fill=c('#263040',160))
    d.ellipse([T//4+3,T//2+3,T*3//4-3,T*3//4-3],fill=c('#384858',100))
    return img

TILE_ORDER = [
    'road_h','road_v','road_cross','sidewalk','sidewalk_edge',
    'grass','grass_lush','water','water_edge','concrete',
    'tile_plaza','building','park_path','fence_green','alley',
]
TILE_DRAWERS = {
    'road_h':tile_road_h,'road_v':tile_road_v,'road_cross':tile_road_cross,
    'sidewalk':tile_sidewalk,'sidewalk_edge':tile_sidewalk_edge,
    'grass':tile_grass,'grass_lush':tile_grass_lush,
    'water':tile_water,'water_edge':tile_water_edge,'concrete':tile_concrete,
    'tile_plaza':tile_tile_plaza,'building':tile_building,
    'park_path':tile_park_path,'fence_green':tile_fence_green,'alley':tile_alley,
}

def build_tile_sheet():
    """Build the tile sheet entirely from PIL — no API calls needed."""
    print("\n=== Building tile sheet (PIL) ===")
    n = len(TILE_ORDER)
    sheet = Image.new('RGBA', (n * T, T))
    for i, name in enumerate(TILE_ORDER):
        sheet.paste(TILE_DRAWERS[name](), (i * T, 0))
        print(f"  [{name}] done")
    index = {name: i for i, name in enumerate(TILE_ORDER)}
    out_dir = SHEET_DIR / "tiles"
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet.save(out_dir / "tiles_sheet.png")
    with open(out_dir / "tiles_index.json", "w") as f:
        json.dump({"tileSize": T, "tiles": index}, f, indent=2)
    print(f"  → tiles_sheet.png  ({n*T}×{T})  tiles_index.json  ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  AI OBJECT GENERATION
# ══════════════════════════════════════════════════════════════════════════════

# Sprite specs: (key, w, h, detailed_prompt)
OBJECT_SPECS = [
    # ── Buildings: generated by PIL (_draw_building_topdown), desc not used ──
    # Each type has 3 color variants (v0=default key, v1, v2).
    # Sizes: W × (rH + wall + shad) — must match SPECS in _draw_building_topdown.

    ("village_building",    80, 62, ""),  # gray plaster
    ("village_building_v1", 80, 62, ""),  # warm orange-clay
    ("village_building_v2", 80, 62, ""),  # aged green

    ("office_tower",        64, 76, ""),  # deep blue glass
    ("office_tower_v1",     64, 76, ""),  # green glass (eco)
    ("office_tower_v2",     64, 76, ""),  # silver-white curtain

    ("cbd_building",        88, 74, ""),  # teal-blue
    ("cbd_building_v1",     88, 74, ""),  # cool gray steel
    ("cbd_building_v2",     88, 74, ""),  # warm tan-brown

    ("shop_building",       72, 56, ""),  # cream
    ("shop_building_v1",    72, 56, ""),  # terracotta orange
    ("shop_building_v2",    72, 56, ""),  # white modern

    ("apartment_block",     88, 70, ""),  # beige/tan
    ("apartment_block_v1",  88, 70, ""),  # sky blue residential
    ("apartment_block_v2",  88, 70, ""),  # salmon pink

    # ── Vegetation: top-down canopy view ──

    ("street_tree", 56, 56,
     "Top-down bird's-eye pixel art of a round deciduous city street tree CANOPY from directly above. "
     "Dense circular green crown filling most of the canvas, concentric lighter/darker green rings, "
     "tiny brown center where trunk meets canopy. Pure white background."),

    ("palm_tree", 48, 48,
     "Top-down bird's-eye pixel art of a tropical palm tree from directly above. "
     "Star-burst of long green palm fronds radiating outward from a tiny brown center. "
     "7-9 fronds spread evenly, lighter green tips. Pure white background."),

    ("bush_cluster", 48, 32,
     "Top-down bird's-eye pixel art of a low ornamental bush cluster from directly above. "
     "3-4 rounded dark-green blobs clustered together, lighter green highlights on tops. "
     "Pure white background."),

    # ── Street furniture ──

    ("street_lamp", 16, 16,
     "Top-down bird's-eye pixel art of a street lamp post seen from directly above. "
     "A small circle or cross shape representing the lamp head, dark gray. "
     "Centered in canvas. Pure white background."),

    ("park_bench", 40, 24,
     "Top-down bird's-eye pixel art of a park bench from directly above. "
     "Brown wooden slats arranged horizontally, dark metal legs at ends. Pure white background."),

    ("trash_can", 20, 20,
     "Top-down bird's-eye pixel art of a cylindrical public trash bin seen from directly above. "
     "Round dark-gray circle with a slightly lighter circular lid. Pure white background."),

    ("traffic_light", 16, 20,
     "Top-down bird's-eye pixel art of a traffic light post seen from directly above. "
     "A thin cross or T-shape, black post with tiny colored dots. Pure white background."),

    ("fountain", 72, 72,
     "Top-down bird's-eye pixel art of a circular plaza fountain from directly above. "
     "White marble circular basin ring, blue water surface inside, "
     "central bright white jet point, concentric ripple circles. Pure white background."),

    ("metro_entrance", 64, 64,
     "Top-down bird's-eye pixel art of a Shenzhen Metro subway entrance roof from directly above. "
     "Dark green rectangular canopy roof with red 地铁 sign visible on roof edge, "
     "glass panels forming a rectangle. Pure white background."),
]

STYLE_PREFIX = (
    "Pixel art game sprite, classic SNES/GBA top-down RPG style (like Pokemon FireRed or Zelda LTTP). "
    "Strictly top-down 2D view — the object is seen from DIRECTLY ABOVE (bird's eye). "
    "NO isometric perspective, NO 3D oblique angle, NO perspective distortion. "
    "The sprite shows the ROOF/TOP of the building from above, with at most a 1-2 pixel "
    "front-wall strip visible at the very bottom of the sprite. "
    "Clean hard pixel edges, limited color palette (≤32 colors), no anti-aliasing. "
    "Single isolated object on pure white background. "
)

# ── API helpers ────────────────────────────────────────────────────────────────
def _headers():
    return {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

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

def _fetch_sprite(prompt: str, model: str) -> bytes:
    if model.startswith("imagen-"):
        return _call_imagen(prompt, model)
    return _call_gemini(prompt, model)

# ── background removal ────────────────────────────────────────────────────────
def remove_bg(img: Image.Image, threshold: int = 230) -> Image.Image:
    """
    Remove white / near-white background from an AI-generated sprite.
    Algorithm:
      1. Flood-fill from all four corners to find connected near-white regions.
      2. Set those pixels to transparent.
      3. Apply a mild edge-soften pass.
    """
    img = img.convert("RGBA")
    w, h = img.size
    pixels = img.load()

    def is_bg(px):
        r, g, b, a = px
        return a > 0 and r >= threshold and g >= threshold and b >= threshold

    visited = [[False] * h for _ in range(w)]
    stack = []
    for corner in [(0,0),(w-1,0),(0,h-1),(w-1,h-1)]:
        if not visited[corner[0]][corner[1]]:
            stack.append(corner)

    while stack:
        x, y = stack.pop()
        if x < 0 or x >= w or y < 0 or y >= h:
            continue
        if visited[x][y]:
            continue
        visited[x][y] = True
        if is_bg(pixels[x, y]):
            pixels[x, y] = (0, 0, 0, 0)
            stack += [(x+1,y),(x-1,y),(x,y+1),(x,y-1)]

    return img

def _pixelate(img: Image.Image, target_w: int, target_h: int) -> Image.Image:
    """
    Downscale with NEAREST to enforce pixel-art look, preserving RGBA transparency.
    If the image is larger than target, scale down. If smaller or equal, just fit.
    """
    img = img.convert("RGBA")
    src_w, src_h = img.size
    if src_w == target_w and src_h == target_h:
        return img
    # Scale to fit inside target, maintaining aspect ratio
    ratio = min(target_w / src_w, target_h / src_h)
    new_w = max(1, int(src_w * ratio))
    new_h = max(1, int(src_h * ratio))
    small = img.resize((new_w, new_h), Image.LANCZOS)
    # Center onto target canvas
    canvas = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
    off_x = (target_w - new_w) // 2
    off_y = (target_h - new_h) // 2
    canvas.paste(small, (off_x, off_y), small)
    return canvas

# ── procedural building sprites (guaranteed top-down, consistent with road tiles) ────
def _draw_building_topdown(key: str) -> Image.Image | None:
    """
    Classic 2.5D RPG building sprite (Pokémon / Zelda LTTP style):
      • Top portion  = roof seen from slightly-elevated camera (mostly top-down)
      • Bottom strip = front wall face (south facade) — height communicates # floors
      • Below        = soft drop shadow

    Supports colour variants via key suffix: "office_tower" (v0), "office_tower_v1", "office_tower_v2".
    Returns None for non-building types (fall through to AI).
    """
    import re
    m = re.match(r'^(.*?)(?:_v(\d+))?$', key)
    base_key = m.group(1) if m else key
    variant   = int(m.group(2)) if (m and m.group(2)) else 0

    # per-type geometry (shared across all variants)
    GEOM: dict[str, dict] = {
        "office_tower":    dict(rW=64, rH=42, wall=22, shad=12),
        "cbd_building":    dict(rW=88, rH=46, wall=18, shad=10),
        "apartment_block": dict(rW=88, rH=44, wall=16, shad=10),
        "shop_building":   dict(rW=72, rH=38, wall=10, shad=8),
        "village_building":dict(rW=80, rH=40, wall=14, shad=8),
    }
    if base_key not in GEOM:
        return None

    # colour variants per type  [v0, v1, v2]
    # Each entry: (roof, panel, acc, wall_top, wall_bot, win_rgb)
    COLOURS: dict[str, list] = {
        "office_tower": [
            ("#1A2840", "#243D5C", "#8AB0D0", "#162030", "#0C1422", (90,130,190)),   # v0 deep blue glass
            ("#183828", "#225238", "#70C090", "#102818", "#081A0E", (70,180,100)),   # v1 green eco glass
            ("#303840", "#3C4850", "#B0C0D0", "#202830", "#141E24", (175,210,240)),  # v2 silver curtain
        ],
        "cbd_building": [
            ("#183030", "#224A4A", "#80B0A8", "#142828", "#0C1C1C", (70,160,180)),   # v0 teal
            ("#282C30", "#343840", "#90A0B0", "#1C2024", "#10141A", (140,165,190)),  # v1 cool gray steel
            ("#383018", "#504828", "#D0B860", "#281C10", "#180E08", (220,180,80)),   # v2 warm gold
        ],
        "apartment_block": [
            ("#C4B48A", "#B8A478", "#8A7A60", "#9A7A50", "#7A5A38", (210,190,140)), # v0 beige/tan
            ("#8AB0C8", "#789EB8", "#5088A8", "#607888", "#485868", (180,220,240)), # v1 sky blue
            ("#D0A898", "#C09888", "#9A7870", "#A07060", "#784848", (235,195,180)), # v2 salmon pink
        ],
        "shop_building": [
            ("#E0D0A8", "#D0BC8C", "#A09070", "#B89060", "#906840", (230,200,130)), # v0 cream
            ("#D8905C", "#C87848", "#F0B090", "#A05830", "#783818", (250,200,150)), # v1 terracotta
            ("#E8E8E8", "#D8D8D8", "#A8B0B8", "#B8B8B8", "#909090", (200,220,240)),# v2 white modern
        ],
        "village_building": [
            ("#B0A898", "#A09880", "#787060", "#908070", "#706050", (190,175,150)), # v0 gray plaster
            ("#C89070", "#B88060", "#E0B090", "#A06040", "#783828", (235,195,155)), # v1 warm orange
            ("#788870", "#687860", "#90A888", "#586850", "#404840", (160,185,155)), # v2 aged green
        ],
    }

    cv = COLOURS[base_key][variant % len(COLOURS[base_key])]
    geom = GEOM[base_key]

    # Build a combined SPECS dict for the drawing code below
    SPECS = {key: {
        **geom,
        "roof": cv[0], "panel": cv[1], "acc": cv[2],
        "wall_top": cv[3], "wall_bot": cv[4], "win": cv[5],
    }}
    s = SPECS[key]
    if s is None:
        return None

    W = s["rW"];  RH = s["rH"];  WALL = s["wall"];  SHAD = s["shad"]
    H = RH + WALL + SHAD

    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    def c(h): r,g,b = int(h[1:3],16),int(h[3:5],16),int(h[5:7],16); return (r,g,b,255)

    # ─── 1. ROOF ──────────────────────────────────────────────────────────────
    d.rectangle([0, 0, W-1, RH-1], fill=c(s["roof"]))
    # Panel grid lines
    stride = 8 if key in ("office_tower","cbd_building") else 10
    pc = c(s["panel"])
    for gx in range(0, W, stride):
        d.line([gx, 0, gx, RH-1], fill=pc)
    for gy in range(0, RH, stride):
        d.line([0, gy, W-1, gy], fill=pc)
    # Roof edge highlight (top of building, northernmost edge)
    ec = c(s["acc"])
    d.line([0, 0, W-1, 0], fill=ec)
    d.line([0, 0, 0, RH-1], fill=ec)

    # ─── 2. TYPE-SPECIFIC ROOF DETAILS ───────────────────────────────────────
    if base_key == "office_tower":
        cx, cy = W//2, RH//2
        # Helipad H
        d.rectangle([cx-9, cy-6, cx-4, cy+6], fill=(200,200,210,255))
        d.rectangle([cx+4,  cy-6, cx+9, cy+6], fill=(200,200,210,255))
        d.rectangle([cx-3,  cy-2, cx+3, cy+2], fill=(200,200,210,255))
        d.ellipse([cx-12, cy-12, cx+12, cy+12], outline=(230,200,50,200))
        # 4 HVAC corner units
        for hx, hy in [(2,2),(W-10,2),(2,RH-10),(W-10,RH-10)]:
            d.rectangle([hx, hy, hx+7, hy+7], fill=(55,60,72,255))
            d.rectangle([hx+1,hy+1,hx+6,hy+6], fill=(75,80,92,255))
        d.line([W//2, 0, W//2, 4], fill=(180,195,215,255))

    elif base_key == "cbd_building":
        for sx in range(3):
            for sy in range(3):
                d.rectangle([W//2-14+sx*10, RH//2-14+sy*10,
                              W//2-14+sx*10+7, RH//2-14+sy*10+7],
                             fill=(80,150,185,200))
        for hx, hy in [(2,2),(W-14,2),(2,RH-10),(W-14,RH-10)]:
            d.rectangle([hx, hy, hx+11, hy+7], fill=(50,58,68,255))
            for i in range(3):
                d.rectangle([hx+1+i*4,hy+1,hx+3+i*4,hy+6], fill=(68,75,88,255))

    elif base_key == "apartment_block":
        for wy in range(4, RH-4, 8):
            for wx in range(4, W-4, 6):
                sh = (158,143,102,255) if (wx//6+wy//8)%2==0 else (138,123,85,255)
                d.rectangle([wx, wy, wx+3, wy+5], fill=sh)
        d.rectangle([W-16,2,W-4,14], fill=(128,118,102,255))
        d.rectangle([W-14,4,W-6,12], fill=(108,98,85,255))
        d.rectangle([2,2,12,10], fill=(98,92,80,255))

    elif base_key == "shop_building":
        awnings = [(200,55,55,255),(55,145,200,255),(195,155,45,255),(75,168,75,255)]
        sw = W // len(awnings)
        for i, ac in enumerate(awnings):
            d.rectangle([i*sw, RH-8, (i+1)*sw-1, RH-1], fill=ac)
        for hx in range(5, W-5, 18):
            d.rectangle([hx, 3, hx+11, 10], fill=(148,138,118,255))

    elif base_key == "village_building":
        for i in range(4):
            hx = 3 + i*(W//4); hy = 3 + (i%2)*12
            d.rectangle([hx, hy, hx+9, hy+7], fill=(118,113,103,255))
        d.ellipse([W//2-8,RH//2-8,W//2+8,RH//2+8], fill=(88,83,73,255))
        d.ellipse([W//2-6,RH//2-6,W//2+6,RH//2+6], fill=(103,98,86,255))
        d.line([W//4,2,W//4,RH-2], fill=(98,93,83,155))
        d.line([W*3//4,2,W*3//4,RH-2], fill=(98,93,83,155))

    # ─── 3. FRONT WALL (south facade) ────────────────────────────────────────
    # Gradient: lighter at top (roof edge), darker at bottom (ground)
    wt = c(s["wall_top"]); wb = c(s["wall_bot"])
    for row in range(WALL):
        t = row / max(WALL-1, 1)
        r = int(wt[0]*(1-t) + wb[0]*t)
        g = int(wt[1]*(1-t) + wb[1]*t)
        b = int(wt[2]*(1-t) + wb[2]*t)
        d.line([0, RH+row, W-1, RH+row], fill=(r,g,b,255))
    # Window row(s) on the facade — size scales with WALL height
    win_h = max(3, WALL//4)
    rows_of_windows = 1 if WALL < 14 else 2
    wc = s["win"] + (255,)
    for wr in range(rows_of_windows):
        wy = RH + 2 + wr * (WALL//(rows_of_windows+1))
        for wx in range(3, W-3, max(6, W//8)):
            d.rectangle([wx, wy, wx+4, wy+win_h-1], fill=wc)
    # Roof-wall boundary line (strong shadow where roof meets wall)
    d.line([0, RH, W-1, RH], fill=(0,0,0,180))
    # Side edges
    d.line([0,RH,0,RH+WALL-1], fill=(0,0,0,120))
    d.line([W-1,RH,W-1,RH+WALL-1], fill=(0,0,0,80))

    # ─── 4. DROP SHADOW ──────────────────────────────────────────────────────
    for i in range(SHAD):
        alpha = int(140 * (1 - i/SHAD)**1.5)
        d.line([0, RH+WALL+i, W-1, RH+WALL+i], fill=(0,0,0,alpha))

    return img


# ── placeholder for dry-run ───────────────────────────────────────────────────
def _placeholder(w: int, h: int) -> Image.Image:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for y in range(h):
        for x in range(w):
            if (x//8 + y//8) % 2 == 0:
                d.point((x, y), fill=(180, 180, 255, 160))
    d.rectangle([0, 0, w-1, h-1], outline=(100, 100, 200, 200))
    return img

# ── object sheet builder ──────────────────────────────────────────────────────
def build_object_sheet(model: str, dry_run: bool):
    print(f"\n=== Building object sheet (AI={model}) ===")
    SHEET_W = 96
    PAD = 4
    sprites: list[tuple[str, int, int, Image.Image]] = []

    for key, w, h, desc in OBJECT_SPECS:
        print(f"  [{key}] {w}×{h} ...", end=" ", flush=True)

        # Buildings are always drawn with PIL (guaranteed top-down consistency)
        pil_spr = _draw_building_topdown(key)
        if pil_spr is not None:
            spr = pil_spr
            print("PIL ✓")
        elif dry_run:
            spr = _placeholder(w, h)
            print("placeholder")
        else:
            prompt = STYLE_PREFIX + desc
            spr = None
            for attempt in range(3):
                try:
                    raw = _fetch_sprite(prompt, model)
                    ai_img = Image.open(io.BytesIO(raw)).convert("RGBA")
                    ai_img = remove_bg(ai_img)
                    spr = _pixelate(ai_img, w, h)
                    print("✓")
                    break
                except Exception as e:
                    print(f"\n    attempt {attempt+1} failed: {e}", end=" ")
                    if attempt < 2:
                        time.sleep(3 * (attempt + 1))
            if spr is None:
                print("\n    → using PIL fallback")
                spr = _placeholder(w, h)

        sprites.append((key, w, h, spr))

    total_h = sum(h + PAD for _, _, h, _ in sprites) + PAD
    sheet = Image.new("RGBA", (SHEET_W, total_h), (0, 0, 0, 0))
    manifest: dict = {}
    y_cursor = PAD

    for key, w, h, spr in sprites:
        x_off = (SHEET_W - w) // 2
        sheet.paste(spr, (x_off, y_cursor), spr)
        manifest[key] = {"x": x_off, "y": y_cursor, "w": w, "h": h}
        y_cursor += h + PAD

    out_dir = SHEET_DIR / "objects"
    out_dir.mkdir(parents=True, exist_ok=True)
    sheet.save(out_dir / "objects_sheet.png")
    with open(out_dir / "objects_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"  → objects_sheet.png  ({SHEET_W}×{total_h})  objects_manifest.json  ✓")


# ══════════════════════════════════════════════════════════════════════════════
#  PREVIEW helper
# ══════════════════════════════════════════════════════════════════════════════
def save_preview():
    import subprocess
    out = Path("/tmp/sprites_preview.png")
    try:
        t_sheet = Image.open(SHEET_DIR / "tiles" / "tiles_sheet.png")
        o_sheet = Image.open(SHEET_DIR / "objects" / "objects_sheet.png")

        SCALE = 3
        tw = t_sheet.width * SCALE; th = T * SCALE
        ow = o_sheet.width * SCALE; oh = o_sheet.height * SCALE

        preview = Image.new("RGB", (max(tw, ow), th + oh + 8), (30, 30, 30))
        t_zoom = t_sheet.resize((tw, th), Image.NEAREST)
        preview.paste(Image.new("RGB", (tw, th), (50, 50, 50)), (0, 0))
        preview.paste(t_zoom, (0, 0), t_zoom.convert("RGBA"))
        o_zoom = o_sheet.resize((ow, oh), Image.NEAREST)
        bg = Image.new("RGB", (ow, oh), (60, 60, 60))
        bg.paste(o_zoom, (0, 0), o_zoom.convert("RGBA"))
        preview.paste(bg, (0, th + 8))

        preview.save(out)
        print(f"\n  Preview → {out}")
        subprocess.run(["open", str(out)])
    except Exception as e:
        print(f"  (preview failed: {e})")


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model",        default="gemini-2.5-flash-image")
    p.add_argument("--dry-run",      action="store_true")
    p.add_argument("--tiles-only",   action="store_true")
    p.add_argument("--objects-only", action="store_true")
    p.add_argument("--preview",      action="store_true", help="Open preview after build")
    args = p.parse_args()

    model = os.getenv("COMPASS_MODEL", args.model)
    dry   = args.dry_run

    print(f"Base URL : {BASE_URL}")
    print(f"Model    : {model}  (objects only — tiles use PIL)")
    print(f"Dry run  : {dry}")

    if not dry and not args.tiles_only and not API_KEY:
        sys.exit("\nSet COMPASS_API_KEY=<key>  (or use --dry-run / --tiles-only)")

    if not args.objects_only:
        build_tile_sheet()

    if not args.tiles_only:
        build_object_sheet(model, dry)

    if args.preview:
        save_preview()

    print("\nDone.")

if __name__ == "__main__":
    import io
    main()
