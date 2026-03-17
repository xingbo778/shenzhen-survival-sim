/**
 * Game Entity — tile-based entity movement with smooth pixel interpolation.
 * Entities follow A* paths on the nav mesh and derive destinations from LLM activity strings.
 */

import type { TileType } from './sceneTiles'
import { findPath, randomWalkableTile } from './pathfinder'

export type Facing = 'front' | 'back' | 'left' | 'right'
                   | 'front_left' | 'front_right' | 'back_left' | 'back_right'

export interface GameEntity {
  id: string
  col: number
  row: number
  pixelX: number
  pixelY: number
  path: [number, number][]
  pathIdx: number
  facing: Facing
  animFrame: number
  frameTimer: number
  activity: string
  isBoat: boolean
}

const WALK_SPEED = 2.8       // tiles per second
const FRAME_DURATION = 0.14  // seconds per animation frame
const BOAT_SPEED = 1.4

/**
 * Advance entity position along its path with sub-tile interpolation.
 */
export function tickEntity(entity: GameEntity, dt: number, tileSize: number): void {
  if (entity.pathIdx >= entity.path.length) return

  const speed = entity.isBoat ? BOAT_SPEED : WALK_SPEED
  const target = entity.path[entity.pathIdx]
  const targetPx = target[0] * tileSize + tileSize * 0.5
  const targetPy = target[1] * tileSize + tileSize * 0.5

  const dx = targetPx - entity.pixelX
  const dy = targetPy - entity.pixelY
  const dist = Math.sqrt(dx * dx + dy * dy)
  const step = speed * tileSize * dt

  if (dist <= step) {
    entity.pixelX = targetPx
    entity.pixelY = targetPy
    entity.col = target[0]
    entity.row = target[1]
    entity.pathIdx++
  } else {
    entity.pixelX += (dx / dist) * step
    entity.pixelY += (dy / dist) * step
  }

  // Update facing direction (8-way)
  const adx = Math.abs(dx)
  const ady = Math.abs(dy)
  if (adx > 0.5 || ady > 0.5) {
    const goRight = dx > 0
    const goDown  = dy > 0
    if (adx > ady * 2) {
      entity.facing = goRight ? 'right' : 'left'
    } else if (ady > adx * 2) {
      entity.facing = goDown ? 'front' : 'back'
    } else {
      if (goRight) {
        entity.facing = goDown ? 'front_right' : 'back_right'
      } else {
        entity.facing = goDown ? 'front_left' : 'back_left'
      }
    }
  }

  // Advance animation frame
  entity.frameTimer += dt
  if (entity.frameTimer >= FRAME_DURATION) {
    entity.frameTimer -= FRAME_DURATION
    entity.animFrame = (entity.animFrame + 1) % 6
  }
}

/**
 * Create a new game entity at the given tile position.
 */
export function createEntity(
  id: string,
  col: number,
  row: number,
  tileSize: number,
  isBoat: boolean = false,
): GameEntity {
  return {
    id,
    col,
    row,
    pixelX: col * tileSize + tileSize * 0.5,
    pixelY: row * tileSize + tileSize * 0.5,
    path: [],
    pathIdx: 0,
    facing: 'front',
    animFrame: 0,
    frameTimer: 0,
    activity: '',
    isBoat,
  }
}

// ── Activity → destination tile mapping ─────────────────────────

const ACTIVITY_TILE_PREFS: Record<string, TileType[]> = {
  rest:        ['sidewalk', 'sidewalk_edge', 'concrete'],
  在家:        ['sidewalk', 'sidewalk_edge', 'concrete'],
  sleep:       ['sidewalk', 'concrete'],
  work:        ['tile_plaza', 'concrete', 'sidewalk'],
  工作:        ['tile_plaza', 'concrete', 'sidewalk'],
  上班:        ['tile_plaza', 'concrete', 'sidewalk'],
  walk_around: ['road_h', 'road_v', 'sidewalk', 'park_path'],
  散步:        ['road_h', 'road_v', 'sidewalk', 'park_path'],
  逛街:        ['sidewalk', 'road_h', 'road_v', 'alley'],
  park:        ['grass', 'grass_lush', 'park_path'],
  公园:        ['grass', 'grass_lush', 'park_path'],
  exercise:    ['grass', 'park_path', 'sidewalk'],
  运动:        ['grass', 'park_path', 'sidewalk'],
  eat:         ['sidewalk', 'alley', 'tile_plaza'],
  吃饭:        ['sidewalk', 'alley', 'tile_plaza'],
  shop:        ['sidewalk', 'alley', 'tile_plaza'],
  购物:        ['sidewalk', 'alley', 'tile_plaza'],
  swim:        ['water', 'water_edge'],
}

// Cache activity candidates per keyword+tilemap to avoid rebuilding every call
let _actCacheTilemap: TileType[][] | null = null
const _actCandidateCache = new Map<string, [number, number][]>()

/**
 * Map an LLM activity string to a destination tile on the nav mesh.
 * Tries to find tiles matching the activity's preferred terrain; falls back to random walkable.
 */
export function activityToDestTile(
  activity: string,
  tilemap: TileType[][],
  navMesh: boolean[][],
): [number, number] {
  // Invalidate cache on tilemap change (scene switch)
  if (_actCacheTilemap !== tilemap) {
    _actCacheTilemap = tilemap
    _actCandidateCache.clear()
  }

  const rows = tilemap.length
  const cols = tilemap[0]?.length ?? 0

  // Find matching preference
  const actLower = activity.toLowerCase()
  let matchedKeyword: string | undefined
  let preferredTypes: TileType[] | undefined
  for (const [keyword, types] of Object.entries(ACTIVITY_TILE_PREFS)) {
    if (actLower.includes(keyword)) {
      matchedKeyword = keyword
      preferredTypes = types
      break
    }
  }

  if (preferredTypes && matchedKeyword) {
    let candidates = _actCandidateCache.get(matchedKeyword)
    if (!candidates) {
      const typeSet = new Set(preferredTypes)
      candidates = []
      for (let r = 0; r < rows; r++) {
        for (let c = 0; c < cols; c++) {
          if (navMesh[r][c] && typeSet.has(tilemap[r][c])) {
            candidates.push([c, r])
          }
        }
      }
      _actCandidateCache.set(matchedKeyword, candidates)
    }
    if (candidates.length > 0) {
      return candidates[Math.floor(Math.random() * candidates.length)]
    }
  }

  return randomWalkableTile(navMesh)
}

/**
 * Assign a new path to the entity based on its activity, using A* on the nav mesh.
 * Returns true if a valid path was found.
 */
export function assignActivityPath(
  entity: GameEntity,
  activity: string,
  tilemap: TileType[][],
  navMesh: boolean[][],
): boolean {
  const dest = activityToDestTile(activity, tilemap, navMesh)
  const path = findPath(navMesh, [entity.col, entity.row], dest)
  if (path.length > 1) {
    entity.path = path
    entity.pathIdx = 1 // skip the starting tile
    entity.activity = activity
    return true
  }
  // If pathfinding fails, try a random walkable tile
  const fallback = randomWalkableTile(navMesh, entity.row)
  const fallbackPath = findPath(navMesh, [entity.col, entity.row], fallback)
  if (fallbackPath.length > 1) {
    entity.path = fallbackPath
    entity.pathIdx = 1
    entity.activity = activity
    return true
  }
  return false
}
