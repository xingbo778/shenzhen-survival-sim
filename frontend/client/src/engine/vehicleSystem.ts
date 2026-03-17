/**
 * Vehicle System — lane-based ambient vehicles and boats.
 *
 * Each vehicle/boat type uses its own sprite sheet (single-row, right-facing frames).
 * Left-facing is rendered by flipping the canvas horizontally.
 */

import { preloadImage, getImage, isImageLoaded } from './imageCache'
import type { ZDrawable } from './types'

// ── Types ────────────────────────────────────────────────────────
export type VehicleType =
  | 'shared_bike' | 'meituan' | 'sweeper' | 'taxi'
  | 'huolala' | 'bus' | 'fishing_boat' | 'cruise' | 'speedboat'

export interface VehicleConfig {
  sheetUrl: string
  cellW: number
  cellH: number
  frames: number
  scale: number
  speed: number
  frameRate: number
  zOffset: number
  isBoat?: boolean
}

export const VEHICLE_CONFIGS: Record<VehicleType, VehicleConfig> = {
  taxi:         { sheetUrl: '/sprites/vehicles/taxi.png',         cellW: 205, cellH: 420, frames: 4, scale: 0.12, speed: 0.09, frameRate: 8,  zOffset: 0 },
  huolala:      { sheetUrl: '/sprites/vehicles/huolala.png',      cellW: 326, cellH: 207, frames: 2, scale: 0.15, speed: 0.07, frameRate: 8,  zOffset: 0 },
  meituan:      { sheetUrl: '/sprites/vehicles/meituan.png',      cellW: 233, cellH: 168, frames: 2, scale: 0.20, speed: 0.09, frameRate: 10, zOffset: 0 },
  sweeper:      { sheetUrl: '/sprites/vehicles/sweeper.png',      cellW: 264, cellH: 252, frames: 4, scale: 0.16, speed: 0.04, frameRate: 6,  zOffset: 0 },
  shared_bike:  { sheetUrl: '/sprites/vehicles/shared_bike.png',  cellW: 241, cellH: 255, frames: 4, scale: 0.14, speed: 0.05, frameRate: 8,  zOffset: 0 },
  bus:          { sheetUrl: '/sprites/vehicles/bus.png',          cellW: 1335, cellH: 235, frames: 1, scale: 0.32, speed: 0.05, frameRate: 6, zOffset: 0 },
  fishing_boat: { sheetUrl: '/sprites/boats/fishing_boat.png',   cellW: 400, cellH: 213, frames: 4, scale: 0.14, speed: 0.025, frameRate: 4, zOffset: 0, isBoat: true },
  cruise:       { sheetUrl: '/sprites/boats/cruise.png',         cellW: 535, cellH: 239, frames: 4, scale: 0.16, speed: 0.035, frameRate: 4, zOffset: 0, isBoat: true },
  speedboat:    { sheetUrl: '/sprites/boats/speedboat.png',      cellW: 354, cellH: 177, frames: 4, scale: 0.14, speed: 0.055, frameRate: 6, zOffset: 0, isBoat: true },
}

export interface VehicleLane {
  type: VehicleType
  y: number
  xMin: number
  xMax: number
  dir: 1 | -1
}

export const SCENE_VEHICLE_LANES: Record<string, VehicleLane[]> = {
  '宝安城中村': [
    { type: 'shared_bike', y: 0.35, xMin: 0.05, xMax: 0.90, dir:  1 },
    { type: 'shared_bike', y: 0.62, xMin: 0.05, xMax: 0.90, dir: -1 },
    { type: 'meituan',     y: 0.35, xMin: 0.05, xMax: 0.90, dir: -1 },
    { type: 'meituan',     y: 0.62, xMin: 0.05, xMax: 0.90, dir:  1 },
    { type: 'shared_bike', y: 0.50, xMin: 0.10, xMax: 0.50, dir:  1 },
    { type: 'shared_bike', y: 0.50, xMin: 0.50, xMax: 0.90, dir: -1 },
    { type: 'sweeper',     y: 0.78, xMin: 0.05, xMax: 0.95, dir:  1 },
  ],
  '南山科技园': [
    { type: 'shared_bike', y: 0.55, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'shared_bike', y: 0.75, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'meituan',     y: 0.55, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'taxi',        y: 0.80, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'taxi',        y: 0.80, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'bus',         y: 0.85, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'sweeper',     y: 0.88, xMin: 0.05, xMax: 0.95, dir: -1 },
  ],
  '福田CBD': [
    // 红荔路 (~row 12%)
    { type: 'taxi',        y: 0.12, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'shared_bike', y: 0.13, xMin: 0.05, xMax: 0.95, dir: -1 },
    // 福华路 (~row 38%)
    { type: 'taxi',        y: 0.37, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'bus',         y: 0.39, xMin: 0.05, xMax: 0.95, dir: -1 },
    // 深南大道 (~row 58%, widest road)
    { type: 'taxi',        y: 0.56, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'taxi',        y: 0.57, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'bus',         y: 0.59, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'huolala',     y: 0.60, xMin: 0.05, xMax: 0.95, dir: -1 },
    // 滨河大道 (~row 82%)
    { type: 'taxi',        y: 0.81, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'meituan',     y: 0.83, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'sweeper',     y: 0.84, xMin: 0.05, xMax: 0.95, dir:  1 },
  ],
  '华强北': [
    { type: 'meituan',     y: 0.30, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'meituan',     y: 0.30, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'shared_bike', y: 0.50, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'shared_bike', y: 0.50, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'meituan',     y: 0.70, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'taxi',        y: 0.85, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'sweeper',     y: 0.88, xMin: 0.05, xMax: 0.95, dir:  1 },
  ],
  '东门老街': [
    { type: 'shared_bike', y: 0.30, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'shared_bike', y: 0.55, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'meituan',     y: 0.30, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'shared_bike', y: 0.75, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'meituan',     y: 0.75, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'sweeper',     y: 0.80, xMin: 0.05, xMax: 0.95, dir:  1 },
  ],
  '南山公寓': [
    { type: 'taxi',        y: 0.50, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'taxi',        y: 0.55, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'shared_bike', y: 0.60, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'meituan',     y: 0.75, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'taxi',        y: 0.75, xMin: 0.05, xMax: 0.95, dir:  1 },
    { type: 'bus',         y: 0.80, xMin: 0.05, xMax: 0.95, dir: -1 },
    { type: 'sweeper',     y: 0.83, xMin: 0.05, xMax: 0.95, dir:  1 },
  ],
  '深圳湾公园': [
    { type: 'shared_bike',  y: 0.32, xMin: 0.02, xMax: 0.98, dir:  1 },
    { type: 'shared_bike',  y: 0.32, xMin: 0.02, xMax: 0.98, dir: -1 },
    { type: 'shared_bike',  y: 0.36, xMin: 0.02, xMax: 0.98, dir:  1 },
    { type: 'meituan',      y: 0.38, xMin: 0.02, xMax: 0.98, dir: -1 },
    { type: 'sweeper',      y: 0.40, xMin: 0.02, xMax: 0.98, dir:  1 },
    { type: 'fishing_boat', y: 0.68, xMin: 0.02, xMax: 0.98, dir:  1 },
    { type: 'cruise',       y: 0.75, xMin: 0.02, xMax: 0.98, dir: -1 },
    { type: 'speedboat',    y: 0.82, xMin: 0.02, xMax: 0.98, dir:  1 },
    { type: 'fishing_boat', y: 0.88, xMin: 0.02, xMax: 0.98, dir: -1 },
  ],
}

export interface VehicleState {
  id: string
  type: VehicleType
  lane: VehicleLane
  x: number
  y: number
  dir: 1 | -1
  frame: number
  frameTimer: number
}

// ── Lifecycle ────────────────────────────────────────────────────

export function preloadVehicleSheets(): void {
  const seen = new Set<string>()
  for (const config of Object.values(VEHICLE_CONFIGS)) {
    if (!seen.has(config.sheetUrl)) {
      seen.add(config.sheetUrl)
      preloadImage(config.sheetUrl)
    }
  }
}

export function initVehicles(location: string, botCount: number): VehicleState[] {
  const lanes = SCENE_VEHICLE_LANES[location] || []
  const vehicles: VehicleState[] = []
  const extraPerLane = Math.floor(botCount / 5)
  lanes.forEach((lane, laneIdx) => {
    const config = VEHICLE_CONFIGS[lane.type]
    const count = 3 + Math.min(extraPerLane, 4)
    for (let i = 0; i < count; i++) {
      const spread = lane.xMax - lane.xMin
      const x = lane.xMin + (i / count) * spread + Math.random() * (spread / count) * 0.5
      vehicles.push({
        id: `v_${location}_${laneIdx}_${i}`,
        type: lane.type, lane,
        x: Math.max(lane.xMin, Math.min(lane.xMax, x)),
        y: lane.y, dir: lane.dir,
        frame: Math.floor(Math.random() * config.frames),
        frameTimer: Math.random() * (1 / config.frameRate),
      })
    }
  })
  return vehicles
}

// ── Drawing ──────────────────────────────────────────────────────

function drawVehicle(
  ctx: CanvasRenderingContext2D,
  v: VehicleState,
  worldX: number, worldY: number, worldW: number, worldH: number,
): void {
  const config = VEHICLE_CONFIGS[v.type]
  const sheet = getImage(config.sheetUrl)
  if (!sheet || !isImageLoaded(config.sheetUrl)) return

  const { cellW, cellH, frames, scale } = config
  const sx = (v.frame % frames) * cellW
  const renderW = Math.round(cellW * scale)
  const renderH = Math.round(cellH * scale)
  const cx = worldX + v.x * worldW
  const cy = worldY + v.y * worldH

  ctx.save()
  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'

  if (v.dir === -1) {
    ctx.translate(cx, 0)
    ctx.scale(-1, 1)
    ctx.drawImage(sheet, sx, 0, cellW, cellH,
      -renderW / 2, cy - renderH * 0.85, renderW, renderH)
  } else {
    ctx.drawImage(sheet, sx, 0, cellW, cellH,
      cx - renderW / 2, cy - renderH * 0.85, renderW, renderH)
  }

  ctx.restore()
}

/**
 * Advance all vehicles by dt, then push their shadow + sprite drawables.
 * Vehicles outside the viewport are culled before pushing.
 */
export function tickAndCollectVehicleDrawables(
  vehicles: VehicleState[],
  dt: number,
  worldX: number, worldY: number, worldW: number, worldH: number,
  cssW: number, cssH: number,
  drawables: ZDrawable[],
): void {
  vehicles.forEach(v => {
    const config = VEHICLE_CONFIGS[v.type]
    v.frameTimer += dt
    if (v.frameTimer >= 1 / config.frameRate) {
      v.frameTimer -= 1 / config.frameRate
      v.frame = (v.frame + 1) % config.frames
    }
    v.x += v.dir * config.speed * dt
    if (v.dir === 1  && v.x > v.lane.xMax + 0.05) v.x = v.lane.xMin - 0.05
    if (v.dir === -1 && v.x < v.lane.xMin - 0.05) v.x = v.lane.xMax + 0.05

    const vCx = worldX + v.x * worldW
    const vCy = worldY + v.y * worldH
    if (vCx < -100 || vCx > cssW + 100 || vCy < -100 || vCy > cssH + 100) return

    if (!config.isBoat) {
      const s = config.scale
      drawables.push({
        zY: vCy - 0.5,
        draw: (c) => {
          c.save()
          c.beginPath()
          c.ellipse(vCx, vCy + 2, 30 * s, 10 * s, 0, 0, Math.PI * 2)
          c.fillStyle = 'rgba(0,0,0,0.25)'
          c.fill()
          c.restore()
        },
      })
    }

    const vSnap = { ...v }
    drawables.push({
      zY: vCy,
      draw: (c) => drawVehicle(c, vSnap, worldX, worldY, worldW, worldH),
    })
  })
}

/** Returns world-local positions and radii for collision avoidance. */
export function getVehiclePositions(
  vehicles: VehicleState[],
  worldW: number,
  worldH: number,
): { x: number; y: number; radius: number }[] {
  return vehicles.map(v => ({
    x: v.x * worldW,
    y: v.y * worldH,
    radius: 20 * VEHICLE_CONFIGS[v.type].scale * (VEHICLE_CONFIGS[v.type].isBoat ? 0 : 1),
  }))
}
