#!/usr/bin/env python3
"""
Pixel sprite sheet generator for Shenzhen Pixel City.
Style reference: Futian CBD top-down pixel art (dark roads, yellow markings, stone plazas).

Generates:
  sprites/tiles/tiles_sheet.png     — 15 tile types × 64×64 px  (960×64)
  sprites/tiles/tiles_index.json
  sprites/objects/objects_sheet.png — buildings, trees, urban furniture
  sprites/objects/objects_manifest.json

Run:
  python3.11 generate_sprites.py
"""

import os, math, json
from PIL import Image, ImageDraw, ImageFilter

T = 64  # canonical tile pixel size

# ── Colour palette (extracted from Futian CBD reference image) ────
#  Roads
C_ROAD        = '#2A2A32'   # very dark charcoal asphalt
C_ROAD_DARK   = '#1E1E26'   # shadow / crack
C_ROAD_GRAIN  = '#323238'   # asphalt grain
C_YELLOW      = '#E8C832'   # road markings – warm gold-yellow
C_YELLOW_DARK = '#C4A828'   # darker yellow for depth
C_WHITE_LINE  = '#D8D8CC'   # road edge stripe

#  Sidewalk / kerb
C_SIDE        = '#9898A0'   # medium cool-gray stone
C_SIDE_LIGHT  = '#ACACB4'   # tile highlight
C_SIDE_DARK   = '#74747C'   # tile seam / shadow
C_KERB        = '#C0C0C8'   # kerb top face
C_KERB_DARK   = '#5A5A62'   # kerb shadow

#  Plaza (大理石广场)
C_PLAZA       = '#C8C4B4'   # warm cream marble
C_PLAZA_LIGHT = '#DEDACC'   # polished highlight
C_PLAZA_DARK  = '#A8A498'   # seam line
C_PLAZA_SHADOW= '#8E8A7A'   # deep seam

#  Grass
C_GRASS       = '#2A5C22'   # deep forest green
C_GRASS_MID   = '#347028'   # mid variation
C_GRASS_LIGHT = '#3E7C30'   # highlight blade tip
C_GRASS_DARK  = '#1E4418'   # shadow / depth

#  Water
C_WATER       = '#1E4878'   # deep navy-blue
C_WATER_MID   = '#2A5E92'   # mid water
C_WATER_LIGHT = '#3A78AA'   # highlight / wave
C_WATER_FOAM  = '#5A98C0'   # foam crest

#  Concrete / parking lot
C_CONCRETE    = '#62626A'   # blue-gray parking concrete
C_CONCRETE_L  = '#74747C'   # highlight
C_CONCRETE_D  = '#4A4A52'   # shadow

#  Park path (wood)
C_WOOD        = '#7A5828'   # plank base
C_WOOD_LIGHT  = '#9A7040'   # plank highlight
C_WOOD_DARK   = '#5A3E18'   # plank seam / shadow

#  Fence / hedge
C_HEDGE       = '#1E4A14'   # dense dark hedge
C_HEDGE_MID   = '#2A5E1E'   # mid green
C_HEDGE_LIGHT = '#3A7228'   # highlight

#  Alley
C_ALLEY       = '#2E2E28'   # damp alley base
C_ALLEY_DARK  = '#222218'   # shadow edges
C_ALLEY_GRAIN = '#383830'   # surface grain

#  Building ground
C_BLDG_BASE   = '#12121A'   # near-black base


# ── Helpers ──────────────────────────────────────────────────────
def rnd(col: int, row: int, s: int = 0) -> float:
    """Deterministic pseudo-random in [0,1)."""
    v = (col * 374761393 + row * 668265263 + s * 1234567) & 0xFFFFFFFF
    v = ((v ^ (v >> 13)) * 1274126177) & 0xFFFFFFFF
    return ((v ^ (v >> 16)) & 0xFFFFFFFF) / 4294967296

def c(hex_color: str, a: int = 255):
    s = hex_color.lstrip('#')
    return (int(s[0:2],16), int(s[2:4],16), int(s[4:6],16), a)

def lerp_c(c1, c2, t):
    return tuple(int(c1[i]*(1-t)+c2[i]*t) for i in range(3)) + (255,)

def new(color=None):
    base = c(color) if color else (0,0,0,0)
    img = Image.new('RGBA', (T, T), base)
    return img, ImageDraw.Draw(img)


# ════════════════════════════════════════════════════════════════
#  TILE DRAWERS
# ════════════════════════════════════════════════════════════════

def tile_road_h():
    img, d = new(C_ROAD)
    # asphalt micro-grain
    for i in range(50):
        x = int(rnd(i, 1) * T)
        y = int(rnd(1, i) * T)
        d.point((x, y), fill=c(C_ROAD_GRAIN))
    # subtle lighter strip in centre (worn)
    d.rectangle([0, T//2-4, T-1, T//2+3], fill=c('#2E2E36'))
    # yellow SOLID edge stripes (Chinese road style)
    d.rectangle([0, 2, T-1, 4],     fill=c(C_YELLOW))
    d.rectangle([0, T-5, T-1, T-3], fill=c(C_YELLOW))
    # yellow centre dashes
    dash_w, gap = 10, 7
    cy = T // 2 - 1
    x = 0
    while x < T:
        d.rectangle([x, cy, min(x+dash_w-1,T-1), cy+2], fill=c(C_YELLOW))
        x += dash_w + gap
    # very thin white curb edge
    d.rectangle([0, 0, T-1, 1],   fill=c(C_WHITE_LINE))
    d.rectangle([0, T-2, T-1, T-1], fill=c(C_WHITE_LINE))
    # subtle crack
    cx0 = int(rnd(7, 3) * T)
    d.line([(cx0, 8),(cx0+4, 22)], fill=c(C_ROAD_DARK), width=1)
    return img

def tile_road_v():
    return tile_road_h().rotate(90, expand=False)

def tile_road_cross():
    img, d = new(C_ROAD)
    # grain
    for i in range(40):
        d.point((int(rnd(i,2)*T), int(rnd(2,i)*T)), fill=c(C_ROAD_GRAIN))
    # YELLOW zebra stripes (matches reference image exactly)
    SW, SG = 6, 4   # stripe width, gap
    # top pedestrian band
    band_y, band_h = 0, T // 5
    x = T * 2 // 10
    while x < T * 8 // 10:
        d.rectangle([x, band_y, x+SW-1, band_y+band_h-1], fill=c(C_YELLOW))
        x += SW + SG
    # bottom band
    band_y = T - T // 5
    x = T * 2 // 10
    while x < T * 8 // 10:
        d.rectangle([x, band_y, x+SW-1, T-1], fill=c(C_YELLOW))
        x += SW + SG
    # left band
    band_x, band_w = 0, T // 5
    y = T * 2 // 10
    while y < T * 8 // 10:
        d.rectangle([band_x, y, band_x+band_w-1, y+SW-1], fill=c(C_YELLOW))
        y += SW + SG
    # right band
    band_x = T - T // 5
    y = T * 2 // 10
    while y < T * 8 // 10:
        d.rectangle([band_x, y, T-1, y+SW-1], fill=c(C_YELLOW))
        y += SW + SG
    # stop lines (solid yellow bar)
    d.rectangle([0, T//5-2, T-1, T//5+1],       fill=c(C_YELLOW))
    d.rectangle([0, T*4//5-2, T-1, T*4//5+1],    fill=c(C_YELLOW))
    d.rectangle([T//5-2, 0, T//5+1, T-1],        fill=c(C_YELLOW))
    d.rectangle([T*4//5-2, 0, T*4//5+1, T-1],    fill=c(C_YELLOW))
    return img

def tile_sidewalk():
    """Medium-gray stone pavement — clean rectangular tiles."""
    img, d = new(C_SIDE)
    TW, TH = T // 2, T // 3   # tile cell size
    for row in range(4):
        for col in range(3):
            # alternating offset rows (brick bond)
            ox = (TW // 2) if (row % 2 == 1) else 0
            x0 = ox + col * TW
            y0 = row * TH
            x1 = x0 + TW - 1
            y1 = y0 + TH - 1
            if x0 >= T: continue
            x1 = min(x1, T-1)
            # tile face – slight random brightness variation
            shade_t = rnd(col*3+row, row*2+col) * 0.08
            face = lerp_c(c(C_SIDE), c(C_SIDE_LIGHT), shade_t)
            d.rectangle([x0, y0, x1, y1], fill=face)
            # top highlight edge
            d.rectangle([x0, y0, x1, y0+1], fill=c(C_SIDE_LIGHT))
            d.rectangle([x0, y0, x0+1, y1], fill=c(C_SIDE_LIGHT))
            # bottom/right shadow
            d.rectangle([x0, y1-1, x1, y1], fill=c(C_SIDE_DARK))
            d.rectangle([x1-1, y0, x1, y1], fill=c(C_SIDE_DARK))
    # seam lines (mortar)
    for row in range(4):
        y = row * TH
        if 0 < y < T:
            d.rectangle([0, y, T-1, y], fill=c(C_SIDE_DARK))
    return img

def tile_sidewalk_edge():
    """Kerb / road-edge strip."""
    img, d = new(C_KERB)
    # top face (lighter)
    d.rectangle([0, 0, T-1, T//4], fill=c(C_KERB))
    d.rectangle([0, 0, T-1, 2],    fill=c('#E0E0E8'))
    # front face (shadow)
    d.rectangle([0, T//4, T-1, T-1], fill=c(C_KERB_DARK))
    # horizontal stripe detail
    for y in range(T//4, T, T//8):
        d.rectangle([0, y, T-1, y], fill=c(C_SIDE_DARK))
    return img

def tile_grass():
    """Deep forest-green grass — dense, uniform like the reference."""
    img, d = new(C_GRASS)
    # base variation noise
    for i in range(80):
        x = int(rnd(i, 3) * T)
        y = int(rnd(3, i) * T)
        t_v = rnd(i*2, 3+i)
        col = lerp_c(c(C_GRASS_DARK), c(C_GRASS_MID), t_v)
        d.point((x, y), fill=col)
    # grass blades (tiny V strokes)
    for i in range(28):
        bx = int(rnd(i*3, 7) * (T-4)) + 2
        by = int(rnd(7, i*3) * (T-4)) + 2
        tip = lerp_c(c(C_GRASS), c(C_GRASS_LIGHT), rnd(i,i+5))
        d.line([(bx-1, by+3),(bx, by)],   fill=tip, width=1)
        d.line([(bx+1, by+3),(bx, by)],   fill=tip, width=1)
    # occasional dark patch
    for i in range(6):
        px = int(rnd(i*9,11)*(T-6))+3
        py = int(rnd(11,i*9)*(T-6))+3
        d.rectangle([px, py, px+3, py+2], fill=c(C_GRASS_DARK))
    return img

def tile_grass_lush():
    """Richer grass with varied greens and tiny flowers."""
    img = tile_grass()
    d = ImageDraw.Draw(img)
    # add bright-tip blades
    for i in range(15):
        bx = int(rnd(i*5,13)*(T-4))+2
        by = int(rnd(13,i*5)*(T-4))+2
        d.line([(bx, by+4),(bx-1, by)], fill=c(C_GRASS_LIGHT), width=1)
        d.line([(bx, by+4),(bx+1, by)], fill=c(C_GRASS_LIGHT), width=1)
    # tiny yellow / white flowers
    for i in range(4):
        fx = int(rnd(i*11,17)*(T-4))+2
        fy = int(rnd(17,i*11)*(T-4))+2
        d.ellipse([fx-2, fy-2, fx+2, fy+2], fill=c('#F0E040'))
        d.point((fx, fy), fill=c('#FFF080'))
    return img

def tile_water():
    """Navy-blue water with horizontal wave shimmers."""
    img, d = new(C_WATER)
    # depth gradient
    for row in range(T):
        t_v = row / T
        col = lerp_c(c(C_WATER), c(C_WATER_MID), t_v)
        d.line([(0, row),(T-1, row)], fill=col)
    # wave lines
    for wy in range(0, T, 10):
        for wx in range(0, T, 9):
            wave_y = wy + int(math.sin(wx * 0.5) * 2)
            if 0 <= wave_y < T:
                d.rectangle([wx, wave_y, wx+5, wave_y], fill=c(C_WATER_LIGHT))
    # foam crest sparkles
    for i in range(8):
        sx = int(rnd(i*7,5)*T); sy = int(rnd(5,i*7)*T)
        d.rectangle([sx, sy, sx+3, sy], fill=c(C_WATER_FOAM, 200))
    # dark left/bottom edge (depth)
    d.rectangle([0,T-3,T-1,T-1], fill=c(C_WATER))
    return img

def tile_water_edge():
    """Shore transition — lighter water with foam."""
    img = tile_water()
    d = ImageDraw.Draw(img)
    # lighter top 8px — shallow water
    for y in range(8):
        a = 180 - y*20
        d.rectangle([0, y, T-1, y], fill=c(C_WATER_LIGHT, a))
    # foam pebbles
    for i in range(10):
        x = int(rnd(i*4,9)*(T-4))+2
        d.ellipse([x-2, 1, x+2, 4], fill=c(C_WATER_FOAM, 160))
    return img

def tile_concrete():
    """Blue-gray parking / forecourt concrete slab."""
    img, d = new(C_CONCRETE)
    # slab grid 2×2
    d.rectangle([T//2-1, 0,  T//2+1, T-1], fill=c(C_CONCRETE_D))
    d.rectangle([0,  T//2-1, T-1,  T//2+1], fill=c(C_CONCRETE_D))
    # surface noise
    for i in range(25):
        d.point((int(rnd(i,6)*T), int(rnd(6,i)*T)), fill=c(C_CONCRETE_D))
    # slab highlight top-left quadrant
    for (qx, qy) in ((2,2),(T//2+2,2),(2,T//2+2),(T//2+2,T//2+2)):
        d.rectangle([qx, qy, qx+T//2-6, qy+2], fill=c(C_CONCRETE_L))
        d.rectangle([qx, qy, qx+2, qy+T//2-6], fill=c(C_CONCRETE_L))
    # bottom shadow
    d.rectangle([0, T-3, T-1, T-1], fill=c(C_CONCRETE_D))
    return img

def tile_tile_plaza():
    """Large white/cream marble plaza tiles — reference: light stone square."""
    img, d = new(C_PLAZA)
    HT = T // 2
    # four marble tiles
    for (tx, ty) in ((0,0),(HT,0),(0,HT),(HT,HT)):
        # face with slight gradient
        for ry in range(HT):
            t_v = ry / HT * 0.15
            row_c = lerp_c(c(C_PLAZA_LIGHT), c(C_PLAZA), t_v)
            d.rectangle([tx+1, ty+ry, tx+HT-2, ty+ry], fill=row_c)
        # bevel edges
        d.rectangle([tx,      ty,      tx+HT-1, ty+1      ], fill=c(C_PLAZA_LIGHT))  # top
        d.rectangle([tx,      ty,      tx+1,    ty+HT-1   ], fill=c(C_PLAZA_LIGHT))  # left
        d.rectangle([tx,      ty+HT-2, tx+HT-1, ty+HT-1   ], fill=c(C_PLAZA_SHADOW)) # bottom
        d.rectangle([tx+HT-2, ty,      tx+HT-1, ty+HT-1   ], fill=c(C_PLAZA_SHADOW)) # right
        # subtle diagonal veining
        vx = int(rnd(tx,ty)*HT//2)+tx+4
        vy = ty + 4
        d.line([(vx,vy),(vx+6,vy+10)], fill=c(C_PLAZA_DARK, 100), width=1)
    # cross seam (mortar lines)
    d.rectangle([0, HT-1, T-1, HT+1],   fill=c(C_PLAZA_DARK))
    d.rectangle([HT-1, 0, HT+1, T-1],   fill=c(C_PLAZA_DARK))
    return img

def tile_building():
    """Concrete floor beneath building zone — lighter, textured, not void-like."""
    BASE = '#2C2A34'   # medium-dark slate concrete
    img, d = new(BASE)
    # Concrete slab seams (faint dark grid every 2 tiles — handled by col/row parity
    # in the renderer; here we just add intra-tile texture)
    d.line([(0, T//2), (T-1, T//2)], fill=c('#24222C'), width=1)
    d.line([(T//2, 0), (T//2, T-1)], fill=c('#24222C'), width=1)
    # Surface speckle: random lighter and darker pixels
    for i in range(18):
        lx, ly = int(rnd(i, 17)*T), int(rnd(17, i)*T)
        shade = '#36343E' if rnd(i, i+1) > 0.5 else '#222028'
        d.point((lx, ly), fill=c(shade))
    # Faint parking bay line
    d.line([(T//2, 2), (T//2, T-3)], fill=c('#383645', 60), width=1)
    return img

def tile_park_path():
    """Wooden plank walkway."""
    img, d = new(C_WOOD)
    PH = T // 5   # plank height
    for idx in range(5):
        y0 = idx * PH
        shade = lerp_c(c(C_WOOD_DARK), c(C_WOOD_LIGHT), rnd(idx, 2) * 0.6 + 0.2)
        d.rectangle([0, y0, T-1, y0+PH-2], fill=shade)
        # highlight top edge
        d.rectangle([0, y0, T-1, y0+1], fill=c(C_WOOD_LIGHT))
        # wood grain lines
        for gi in range(2):
            gx = int(rnd(idx*3+gi, 4) * (T-4)) + 2
            d.line([(gx, y0+2),(gx+int(rnd(gi,idx)*10), y0+PH-3)],
                   fill=c(C_WOOD_DARK), width=1)
        # plank gap
        d.rectangle([0, y0+PH-2, T-1, y0+PH-1], fill=c(C_WOOD_DARK))
    return img

def tile_fence_green():
    """Dense hedge / green fence."""
    img, d = new(C_HEDGE)
    # base noise
    for i in range(70):
        x = int(rnd(i*3,9)*(T-2))+1
        y = int(rnd(9,i*3)*(T-2))+1
        col = lerp_c(c(C_HEDGE), c(C_HEDGE_MID), rnd(i, i+4))
        d.point((x,y), fill=col)
    # rounded bush clusters
    for i in range(9):
        bx = int(rnd(i*6,11)*(T-12))+6
        by = int(rnd(11,i*6)*(T-12))+6
        r  = int(rnd(i,i+7)*4)+4
        d.ellipse([bx-r,by-r,bx+r,by+r], fill=c(C_HEDGE_MID, 200))
        d.point((bx-1, by-1), fill=c(C_HEDGE_LIGHT))
    # ground shadow bottom
    d.rectangle([0, T-4, T-1, T-1], fill=c(C_HEDGE, 180))
    return img

def tile_alley():
    """Narrow damp alley — dark, slightly wet."""
    img, d = new(C_ALLEY)
    # surface texture
    for i in range(40):
        x = int(rnd(i*4,13)*T); y = int(rnd(13,i*4)*T)
        d.point((x,y), fill=c(C_ALLEY_GRAIN))
    # dark gutter edges
    d.rectangle([0, 0, 3, T-1],   fill=c(C_ALLEY_DARK))
    d.rectangle([T-4,0, T-1,T-1], fill=c(C_ALLEY_DARK))
    # crack line
    cx = T // 2 + int(rnd(5,3)*6)-3
    d.line([(cx,4),(cx+2,T-5)], fill=c(C_ALLEY_DARK), width=1)
    # wet puddle reflection
    d.ellipse([T//4,   T//2, T*3//4, T*3//4], fill=c('#263040', 160))
    d.ellipse([T//4+3, T//2+3, T*3//4-3, T*3//4-3], fill=c('#384858', 100))
    return img


# ════════════════════════════════════════════════════════════════
#  TILE SHEET  (15 tiles × 64px = 960×64)
# ════════════════════════════════════════════════════════════════

TILE_ORDER = [
    'road_h', 'road_v', 'road_cross', 'sidewalk', 'sidewalk_edge',
    'grass', 'grass_lush', 'water', 'water_edge', 'concrete',
    'tile_plaza', 'building', 'park_path', 'fence_green', 'alley',
]
TILE_DRAWERS = {
    'road_h':        tile_road_h,
    'road_v':        tile_road_v,
    'road_cross':    tile_road_cross,
    'sidewalk':      tile_sidewalk,
    'sidewalk_edge': tile_sidewalk_edge,
    'grass':         tile_grass,
    'grass_lush':    tile_grass_lush,
    'water':         tile_water,
    'water_edge':    tile_water_edge,
    'concrete':      tile_concrete,
    'tile_plaza':    tile_tile_plaza,
    'building':      tile_building,
    'park_path':     tile_park_path,
    'fence_green':   tile_fence_green,
    'alley':         tile_alley,
}

def build_tile_sheet():
    n = len(TILE_ORDER)
    sheet = Image.new('RGBA', (n * T, T))
    for i, name in enumerate(TILE_ORDER):
        tile_img = TILE_DRAWERS[name]()
        sheet.paste(tile_img, (i * T, 0))
    index = {name: i for i, name in enumerate(TILE_ORDER)}
    return sheet, index


# ════════════════════════════════════════════════════════════════
#  SCENE OBJECT DRAWERS
# ════════════════════════════════════════════════════════════════

def obj_village_building(W=80, H=120):
    """Urban-village handshake apartment — laundry, AC units, shop."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    # wall
    d.rectangle([2, 10, W-3, H-1], fill=c('#C4B89A'))
    d.rectangle([2, 10, 3,  H-1],  fill=c('#9A8A6A'))   # left shadow
    d.rectangle([W-4,10,W-3,H-1],  fill=c('#9A8A6A'))   # right shadow
    # rooftop plant room
    d.rectangle([W//4, 1, W*3//4, 12], fill=c('#808080'))
    d.rectangle([W//4+1,0,W*3//4-1, 3], fill=c('#606060'))
    d.ellipse  ([W//3-3, 2, W//3+3, 8], fill=c('#505058'))  # tank
    # window rows
    for row in range(5):
        y = 16 + row * 18
        for col in range(4):
            wx = 8 + col * 17
            if wx + 10 >= W-4: continue
            d.rectangle([wx, y, wx+10, y+8], fill=c('#3A5A7A'))
            d.rectangle([wx+1,y+1,wx+4,y+3], fill=c('#7AAACE', 200))
            if (row+col)%3==0:
                d.rectangle([wx+1,y+9,wx+9,y+13],fill=c('#888890'))
    # laundry
    for li in range(3):
        ly = 20+li*22
        d.line([(6,ly),(W-6,ly)], fill=c('#C8B890',150), width=1)
        colors=['#CC4444','#4488CC','#44AA66','#AA55CC']
        for ci in range(4):
            cx2 = 10+ci*16
            if cx2+6 >= W-5: continue
            d.rectangle([cx2,ly,cx2+6,ly+10], fill=c(colors[(li+ci)%4],220))
    # ground shop
    d.rectangle([4,H-22,W-4,H-1], fill=c('#6A5A40'))
    d.rectangle([8,H-20,W//2-4,H-2], fill=c('#4A3828'))
    d.rectangle([W//2,H-20,W-8,H-2], fill=c('#4A6A8A',160))
    d.rectangle([4,H-24,W-4,H-22],   fill=c('#CC4400'))
    return img

def obj_office_tower(W=64, H=160):
    """Glass curtain-wall office tower — blue with gold accent."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    # body
    d.rectangle([2, 10, W-3, H-1], fill=c('#2A4A6A'))
    # crown
    d.rectangle([W//6, 0, W*5//6, 12], fill=c('#1A3A5A'))
    d.rectangle([W//4, 0, W*3//4, 6],  fill=c('#C8A830'))  # gold crown
    # glass bands
    for row in range(20):
        y = 14+row*8
        if y > H-2: break
        t_v = row/20
        band_c = lerp_c(c('#3A6AA0'), c('#1A3060'), t_v)
        d.rectangle([3,y,W-4,y+6], fill=band_c)
        # window dividers
        for ci in range(3):
            bx = 3+ci*((W-6)//3)
            d.rectangle([bx,y,bx+1,y+6], fill=c('#0A1828'))
        # reflective highlight
        d.rectangle([3,y,W-4,y+1], fill=c('#5A8AC0',120))
    # gold edge stripe
    d.rectangle([2, 10, 3, H-1], fill=c('#C8A830', 180))
    # side shadow
    d.rectangle([W-4,10,W-2,H-1], fill=c('#0A1828',200))
    return img

def obj_cbd_building(W=88, H=140):
    """Government / civic building — white stone, classical style."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    # body
    d.rectangle([2, 16, W-3, H-1], fill=c('#D8D4C4'))
    d.rectangle([2, 16, 4, H-1],   fill=c('#A8A494'))
    d.rectangle([W-5,16,W-3,H-1],  fill=c('#A8A494'))
    # classical pediment
    pts = [(W//2, 4),(2, 18),(W-3, 18)]
    d.polygon(pts, fill=c('#E8E4D4'))
    d.line   ([(2,18),(W//2,4),(W-3,18)], fill=c('#C0BCA8'), width=2)
    # columns
    for ci in range(5):
        cx = 10 + ci*14
        d.rectangle([cx, 18, cx+5, H-24], fill=c('#F0ECE0'))
        d.rectangle([cx, 18, cx+2, H-24], fill=c('#E0DCC8'))
    # windows
    for row in range(5):
        y=38+row*16
        for col in range(4):
            wx=9+col*19
            if wx+13>=W-4: continue
            d.rectangle([wx,y,wx+13,y+10], fill=c('#5A8AAA'))
            d.rectangle([wx+1,y+1,wx+6,y+4], fill=c('#8ABACE',180))
    # entrance
    d.rectangle([W//2-12,H-28,W//2+12,H-1], fill=c('#C8C0A8'))
    d.rectangle([W//2-10,H-26,W//2+10,H-1], fill=c('#2A2A36'))
    for pi in range(2):
        px=W//2-8+pi*14
        d.rectangle([px,H-26,px+4,H-1], fill=c('#D8D4C4'))
    return img

def obj_shop_building(W=72, H=88):
    """Street-level shop / mall entrance."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    d.rectangle([2,10,W-3,H-1], fill=c('#C8C0A4'))
    d.rectangle([2,10,3,H-1],   fill=c('#9A9278'))
    d.rectangle([W-4,10,W-3,H-1],fill=c('#9A9278'))
    # roof
    d.rectangle([0, 4, W-1, 12], fill=c('#A09070'))
    d.rectangle([0, 0, W-1,  6], fill=c('#B8A878'))
    # upper windows
    for ci in range(3):
        wx=6+ci*22
        d.rectangle([wx,15,wx+16,30], fill=c('#5A7A9A'))
        d.rectangle([wx+1,16,wx+7,21], fill=c('#7AAACE',180))
    # colorful shop front
    for (sx,sy,sw,sh,col2) in [
        (2,H-34,W-4,12,'#CC3333'),
        (6,H-44,W-8,10,'#FFCC00'),
    ]:
        d.rectangle([sx,sy,sx+sw,sy+sh], fill=c(col2))
    # door + windows
    d.rectangle([W//2-8,H-32,W//2+8,H-1], fill=c('#2A1A10'))
    d.rectangle([6,H-32,W//2-10,H-1],      fill=c('#AAC8E0',160))
    d.rectangle([W//2+10,H-32,W-6,H-1],    fill=c('#AAC8E0',160))
    # ac units
    for i in range(2):
        d.rectangle([8+i*26,33,20+i*26,41], fill=c('#909098'))
    return img

def obj_apartment_block(W=88, H=130):
    """Residential high-rise."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    d.rectangle([2,8,W-3,H-1], fill=c('#B8C0C8'))
    d.rectangle([0,0,W-1,10],  fill=c('#8898A0'))
    d.rectangle([4,2,W-5,8],   fill=c('#98A8B0'))
    # balconies
    for floor in range(6):
        y=14+floor*18
        for side in (0,W-20):
            d.rectangle([side+2,y,side+18,y+14], fill=c('#A8B8C8'))
            d.rectangle([side+2,y,side+18,y+2],  fill=c('#C8D8E8'))
            for ri in range(4):
                d.rectangle([side+3+ri*4,y+3,side+4+ri*4,y+14], fill=c('#D0D8E0'))
    # windows
    for floor in range(6):
        y=16+floor*18
        for col in range(3):
            wx=22+col*16
            d.rectangle([wx,y,wx+12,y+10], fill=c('#5A8AAA'))
            d.rectangle([wx+1,y+1,wx+5,y+4], fill=c('#A0C8E0',200))
    # entrance
    d.rectangle([W//2-12,H-24,W//2+12,H-1], fill=c('#6A6060'))
    d.rectangle([W//2-10,H-22,W//2+10,H-1], fill=c('#141420'))
    d.rectangle([W//2-2,H-14,W//2+2,H-1],   fill=c('#888880'))
    return img

def obj_street_tree(W=56, H=80):
    """Round multi-layer canopy — matches reference palm avenue."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    cx = W//2
    # ground shadow
    d.ellipse([cx-20,H-20,cx+20,H-8], fill=c('#101008',80))
    # trunk
    d.rectangle([cx-3,H-24,cx+3,H-8], fill=c('#5A3A14'))
    d.rectangle([cx-2,H-8, cx+2,H-4], fill=c('#3A2808'))
    # canopy layers
    d.ellipse([cx-22,14,cx+22,H-16], fill=c(C_GRASS_DARK))
    d.ellipse([cx-18, 9,cx+18,H-22], fill=c(C_GRASS))
    d.ellipse([cx-14, 5,cx+14,H-28], fill=c(C_GRASS_MID))
    d.ellipse([cx-8,  2,cx+8, H-34], fill=c(C_GRASS_LIGHT))
    d.ellipse([cx-4,  2,cx-1,  8],   fill=c('#80C040',180))
    return img

def obj_palm_tree(W=48, H=100):
    """Tropical palm — common along Shenzhen boulevards."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    cx = W//2
    # shadow
    d.ellipse([cx-16,H-14,cx+20,H-6], fill=c('#101008',70))
    # trunk (slight lean)
    for y in range(H-16, 22, -1):
        lean = int((H-16-y) / (H-38) * 6)
        shade = lerp_c(c('#7A6040'), c('#5A4020'), (H-16-y)/(H-38))
        d.rectangle([cx-3+lean,y,cx+3+lean,y+2], fill=shade)
        if (y%8)<2:
            d.rectangle([cx-3+lean,y+1,cx+3+lean,y+2], fill=c('#4A3010'))
    # fronds
    cx_t = cx+6
    for ang in range(0, 360, 40):
        angle = math.radians(ang)
        length = 20
        ex = cx_t + int(math.cos(angle)*length)
        ey = 24   + int(math.sin(angle)*length*0.35)
        d.line([(cx_t,22),(ex,ey)], fill=c('#2E6A18'), width=3)
        for li in range(3):
            lx=cx_t+int(math.cos(angle)*(li+1)*6)
            ly=22  +int(math.sin(angle)*(li+1)*6*0.35)
            d.line([(lx,ly),(lx+int(math.cos(angle+1.3)*7),ly+int(math.sin(angle+1.3)*4))],
                   fill=c('#3A8020'),width=1)
    d.ellipse([cx_t-5,16,cx_t+5,28], fill=c('#4A8828'))
    return img

def obj_bush_cluster(W=48, H=32):
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    d.ellipse([4, H-8,  24, H-1],  fill=c('#1E4A12'))
    d.ellipse([20,H-10, 44, H-2],  fill=c('#2A5E1A'))
    d.ellipse([12,H-14, 36, H-3],  fill=c('#2A6018'))
    d.ellipse([14,H-14, 34, H-6],  fill=c('#388022', 200))
    d.point   ((21,H-10), fill=c('#5A9030'))
    d.ellipse([4,H-4,W-4,H-1], fill=c('#101008',50))
    return img

def obj_street_lamp(W=16, H=64):
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    cx = W//2
    d.rectangle([cx-4,H-6,cx+4,H-1], fill=c('#484858'))
    d.rectangle([cx-5,H-8,cx+5,H-6], fill=c('#383848'))
    d.rectangle([cx-1,12,cx+1,H-6],  fill=c('#909098'))
    d.line([(cx,12),(cx+6,8),(cx+10,8)], fill=c('#909098'), width=2)
    d.rectangle([cx+4,3,cx+12,9], fill=c('#505060'))
    d.ellipse  ([cx+5,4,cx+11,8], fill=c('#FFF080'))
    d.ellipse  ([cx+6,5,cx+10,7], fill=c('#FFFFF0'))
    d.ellipse  ([cx+2,1,cx+14,11],fill=c('#FFE860',40))
    return img

def obj_park_bench(W=40, H=24):
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    d.ellipse([2,H-6,W-2,H-2], fill=c('#101008',60))
    for pi in range(3):
        y = 9+pi*4
        d.rectangle([4,y,W-4,y+3], fill=c(C_WOOD))
        d.rectangle([4,y,W-4,y+1], fill=c(C_WOOD_LIGHT))
    for lx in (6,W-9):
        d.rectangle([lx,5,lx+3,H-4], fill=c(C_WOOD_DARK))
    d.rectangle([4,4,W-4,10], fill=c('#6A4820'))
    d.rectangle([4,4,W-4,5],  fill=c(C_WOOD_LIGHT))
    return img

def obj_trash_can(W=20, H=28):
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    cx=W//2
    d.ellipse([2,H-5,W-2,H-2], fill=c('#101008',60))
    d.rectangle([3,8,W-3,H-4], fill=c('#2A7A2A'))
    d.rectangle([3,8,4,H-4],   fill=c('#1A5A1A'))
    d.rectangle([W-5,8,W-3,H-4],fill=c('#1A5A1A'))
    d.rectangle([2,4,W-2,9],   fill=c('#228A22'))
    d.rectangle([cx-3,2,cx+3,6],fill=c('#165016'))
    d.ellipse  ([6,14,14,20],   fill=c('#44AA44',200))
    d.point    ((cx,17), fill=c('#AAFFAA'))
    return img

def obj_traffic_light(W=16, H=48):
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    cx=W//2
    d.rectangle([cx-1,28,cx+1,H-1], fill=c('#585868'))
    d.rectangle([cx-3,H-4,cx+3,H-1],fill=c('#404050'))
    d.rectangle([cx-5,4,cx+5,28],   fill=c('#1C1C26'))
    d.rectangle([cx-4,5,cx+4,27],   fill=c('#28283A'))
    d.ellipse  ([cx-3, 6,cx+3,12],  fill=c('#DD2222'))
    d.ellipse  ([cx-3,14,cx+3,20],  fill=c('#887830'))
    d.ellipse  ([cx-3,22,cx+3,28],  fill=c('#22AA22'))
    d.ellipse  ([cx-4,21,cx+4,29],  fill=c('#44FF44',70))
    return img

def obj_fountain(W=72, H=40):
    """Decorative fountain — visible in the reference image plaza."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    cx, cy = W//2, H//2+4
    # basin outer rim
    d.ellipse([4,cy-14,W-4,cy+10], fill=c('#9090A0'))
    d.ellipse([6,cy-12,W-6,cy+8],  fill=c('#7070 80'))
    # water surface
    d.ellipse([8,cy-10,W-8,cy+6],  fill=c(C_WATER_MID))
    d.ellipse([10,cy-8,W-10,cy+4], fill=c(C_WATER_LIGHT))
    # central spout base
    d.rectangle([cx-3,cy-10,cx+3,cy+2], fill=c('#A8A8B0'))
    # water jet (arcs)
    for ang in range(0, 360, 60):
        a = math.radians(ang)
        for r in range(1,12,2):
            jx = cx+int(math.cos(a)*r*0.7)
            jy = cy-8-int(r*0.6)
            d.point((jx,jy), fill=c(C_WATER_FOAM, 200-r*10))
    # top sparkle
    d.ellipse([cx-2,cy-18,cx+2,cy-12], fill=c('#AADDFF',200))
    return img

def obj_metro_entrance(W=64, H=52):
    """地铁站 entrance — iconic Shenzhen metro sign."""
    img = Image.new('RGBA', (W, H))
    d = ImageDraw.Draw(img)
    # canopy
    d.rectangle([0,10,W-1,26], fill=c('#2A4A7A'))
    d.rectangle([0,10,W-1,12], fill=c('#4A6A9A'))
    # 地铁 sign board
    d.rectangle([8,10,W-8,24], fill=c('#CC2222'))
    d.rectangle([10,12,W-10,22], fill=c('#EE3333'))
    # 地铁站 text area (simplified)
    for i in range(3):
        d.rectangle([12+i*14, 14, 22+i*14, 20], fill=c('#FFFFFF', 200))
    # stairs
    for step in range(4):
        y=26+step*6
        d.rectangle([step*3, y, W-1-step*3, y+5], fill=c('#9898A0'))
        d.rectangle([step*3, y, W-1-step*3, y+1], fill=c('#B8B8C0'))
    # side walls
    d.rectangle([0,0,5,H-1],  fill=c('#484858'))
    d.rectangle([W-6,0,W-1,H-1],fill=c('#484858'))
    return img


# ════════════════════════════════════════════════════════════════
#  OBJECTS SHEET
# ════════════════════════════════════════════════════════════════

SCENE_OBJECTS = [
    # key                  drawer                W    H
    ('village_building',   obj_village_building, 80,  120),
    ('office_tower',       obj_office_tower,     64,  160),
    ('cbd_building',       obj_cbd_building,     88,  140),
    ('shop_building',      obj_shop_building,    72,   88),
    ('apartment_block',    obj_apartment_block,  88,  130),
    ('street_tree',        obj_street_tree,      56,   80),
    ('palm_tree',          obj_palm_tree,        48,  100),
    ('bush_cluster',       obj_bush_cluster,     48,   32),
    ('street_lamp',        obj_street_lamp,      16,   64),
    ('park_bench',         obj_park_bench,       40,   24),
    ('trash_can',          obj_trash_can,        20,   28),
    ('traffic_light',      obj_traffic_light,    16,   48),
    ('fountain',           obj_fountain,         72,   40),
    ('metro_entrance',     obj_metro_entrance,   64,   52),
]

def build_objects_sheet():
    PAD = 4
    total_w = max(w for _,_,w,_ in SCENE_OBJECTS) + PAD*2
    total_h = sum(h+PAD for _,_,_,h in SCENE_OBJECTS) + PAD
    sheet    = Image.new('RGBA', (total_w, total_h))
    manifest = {}
    y_cur = PAD
    for key, drawer, w, h in SCENE_OBJECTS:
        spr = drawer(w, h)
        x_off = (total_w-w)//2
        sheet.paste(spr, (x_off, y_cur), spr)
        manifest[key] = {'x': x_off, 'y': y_cur, 'w': w, 'h': h}
        y_cur += h + PAD
    return sheet, manifest


# ════════════════════════════════════════════════════════════════
#  MAIN
# ════════════════════════════════════════════════════════════════

def main():
    base = os.path.dirname(os.path.abspath(__file__))

    print('Generating tile sheet …')
    tiles_dir = os.path.join(base, 'tiles')
    os.makedirs(tiles_dir, exist_ok=True)
    sheet, index = build_tile_sheet()
    sheet.save(os.path.join(tiles_dir, 'tiles_sheet.png'))
    with open(os.path.join(tiles_dir, 'tiles_index.json'), 'w') as f:
        json.dump({'tileSize': T, 'tiles': index}, f, indent=2)
    print(f'  tiles_sheet.png  {sheet.width}×{sheet.height}  ({len(index)} tiles)')

    print('Generating objects sheet …')
    objs_dir = os.path.join(base, 'objects')
    os.makedirs(objs_dir, exist_ok=True)
    obj_sheet, manifest = build_objects_sheet()
    obj_sheet.save(os.path.join(objs_dir, 'objects_sheet.png'))
    with open(os.path.join(objs_dir, 'objects_manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2)
    print(f'  objects_sheet.png  {obj_sheet.width}×{obj_sheet.height}  ({len(manifest)} objects)')

    print('\nDone! New keys:', list(manifest.keys()))

if __name__ == '__main__':
    main()
