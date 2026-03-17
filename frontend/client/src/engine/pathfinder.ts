/**
 * Pathfinder — navigation mesh construction + A* search
 * Supports pedestrian, vehicle, and boat movement modes.
 *
 * Optimizations:
 * - Binary heap for open list (O(log n) pop vs O(n) linear scan)
 * - Path cache with TTL to avoid redundant A* for same from→to
 * - Pre-indexed walkable tiles per row band for randomWalkableTile
 */

import type { TileType } from './sceneTiles'

export type NavMode = 'pedestrian' | 'vehicle' | 'boat'

const PEDESTRIAN_WALKABLE = new Set<TileType>([
  'road_h', 'road_v', 'road_cross',
  'road_cross_zebra_n', 'road_cross_zebra_s', 'road_cross_zebra_w', 'road_cross_zebra_e',
  'road_stop_h', 'road_stop_v',
  'sidewalk', 'sidewalk_edge',
  'alley',
  'grass', 'grass_lush',
  'concrete', 'tile_plaza',
  'park_path',
])

const VEHICLE_DRIVABLE = new Set<TileType>([
  'road_h', 'road_v', 'road_cross',
  'road_cross_zebra_n', 'road_cross_zebra_s', 'road_cross_zebra_w', 'road_cross_zebra_e',
  'road_stop_h', 'road_stop_v',
])

const BOAT_NAVIGABLE = new Set<TileType>([
  'water', 'water_edge',
])

/**
 * Build a boolean passability grid from the tile map.
 */
export function buildNavMesh(tilemap: TileType[][], mode: NavMode): boolean[][] {
  const passable =
    mode === 'pedestrian' ? PEDESTRIAN_WALKABLE :
    mode === 'vehicle' ? VEHICLE_DRIVABLE :
    BOAT_NAVIGABLE

  return tilemap.map(row => row.map(tile => passable.has(tile)))
}

// ── Binary min-heap for A* open list ─────────────────────────────

interface Node {
  col: number
  row: number
  g: number
  f: number
  parent: Node | null
}

class MinHeap {
  private data: Node[] = []

  get length() { return this.data.length }

  push(node: Node) {
    this.data.push(node)
    this._bubbleUp(this.data.length - 1)
  }

  pop(): Node | undefined {
    const top = this.data[0]
    const last = this.data.pop()
    if (this.data.length > 0 && last) {
      this.data[0] = last
      this._sinkDown(0)
    }
    return top
  }

  private _bubbleUp(i: number) {
    const d = this.data
    while (i > 0) {
      const p = (i - 1) >> 1
      if (d[p].f <= d[i].f) break
      ;[d[p], d[i]] = [d[i], d[p]]
      i = p
    }
  }

  private _sinkDown(i: number) {
    const d = this.data
    const n = d.length
    while (true) {
      let smallest = i
      const l = 2 * i + 1
      const r = 2 * i + 2
      if (l < n && d[l].f < d[smallest].f) smallest = l
      if (r < n && d[r].f < d[smallest].f) smallest = r
      if (smallest === i) break
      ;[d[smallest], d[i]] = [d[i], d[smallest]]
      i = smallest
    }
  }
}

// ── Path cache ───────────────────────────────────────────────────

interface CachedPath {
  path: [number, number][]
  ts: number
}

const PATH_CACHE = new Map<string, CachedPath>()
const CACHE_TTL = 5000  // 5 seconds
const MAX_CACHE_SIZE = 200

function prunePathCache() {
  if (PATH_CACHE.size <= MAX_CACHE_SIZE) return
  const now = Date.now()
  PATH_CACHE.forEach((entry, key) => {
    if (now - entry.ts > CACHE_TTL) PATH_CACHE.delete(key)
  })
  // If still too large, drop oldest half
  if (PATH_CACHE.size > MAX_CACHE_SIZE) {
    const entries = Array.from(PATH_CACHE.entries())
    entries.sort((a, b) => a[1].ts - b[1].ts)
    const toRemove = entries.slice(0, Math.floor(entries.length / 2))
    toRemove.forEach(([k]) => PATH_CACHE.delete(k))
  }
}

// ── A* pathfinding ──────────────────────────────────────────────

const DIRS: [number, number][] = [[0, -1], [0, 1], [-1, 0], [1, 0]]

function heuristic(ac: number, ar: number, bc: number, br: number): number {
  return Math.abs(ac - bc) + Math.abs(ar - br)
}

/**
 * A* search on the nav mesh. Returns tile coordinate path from `from` to `to` (inclusive).
 * Returns empty array if unreachable. Results are cached for 5 seconds.
 */
export function findPath(
  mesh: boolean[][],
  from: [number, number],
  to: [number, number],
): [number, number][] {
  const rows = mesh.length
  const cols = mesh[0]?.length ?? 0
  if (rows === 0 || cols === 0) return []

  const [fc, fr] = from
  const [tc, tr] = to

  if (fr < 0 || fr >= rows || fc < 0 || fc >= cols) return []
  if (tr < 0 || tr >= rows || tc < 0 || tc >= cols) return []
  if (!mesh[tr][tc]) return []

  // Check cache
  const cacheKey = `${fc},${fr}-${tc},${tr}`
  const cached = PATH_CACHE.get(cacheKey)
  if (cached && Date.now() - cached.ts < CACHE_TTL) {
    return cached.path.map(p => [p[0], p[1]] as [number, number])
  }

  // If start is blocked, allow it (entity might be on a building edge)
  const open = new MinHeap()
  open.push({ col: fc, row: fr, g: 0, f: heuristic(fc, fr, tc, tr), parent: null })

  const closed = new Set<number>()
  const key = (c: number, r: number) => r * cols + c

  const gMap = new Map<number, number>()
  gMap.set(key(fc, fr), 0)

  while (open.length > 0) {
    const current = open.pop()!

    if (current.col === tc && current.row === tr) {
      // Reconstruct path
      const path: [number, number][] = []
      let n: Node | null = current
      while (n) {
        path.push([n.col, n.row])
        n = n.parent
      }
      path.reverse()
      // Cache result
      PATH_CACHE.set(cacheKey, { path, ts: Date.now() })
      prunePathCache()
      return path
    }

    const ck = key(current.col, current.row)
    if (closed.has(ck)) continue
    closed.add(ck)

    for (const [dc, dr] of DIRS) {
      const nc = current.col + dc
      const nr = current.row + dr
      if (nr < 0 || nr >= rows || nc < 0 || nc >= cols) continue
      if (!mesh[nr][nc]) continue
      const nk = key(nc, nr)
      if (closed.has(nk)) continue

      const ng = current.g + 1
      const prev = gMap.get(nk)
      if (prev !== undefined && ng >= prev) continue

      gMap.set(nk, ng)
      open.push({
        col: nc,
        row: nr,
        g: ng,
        f: ng + heuristic(nc, nr, tc, tr),
        parent: current,
      })
    }
  }

  // Cache negative result too
  PATH_CACHE.set(cacheKey, { path: [], ts: Date.now() })
  return []
}

// ── Walkable tile index ─────────────────────────────────────────

let _walkableAll: [number, number][] | null = null
let _walkableMesh: boolean[][] | null = null

function ensureWalkableIndex(mesh: boolean[][]) {
  if (_walkableMesh === mesh) return
  _walkableMesh = mesh
  _walkableAll = []
  for (let r = 0; r < mesh.length; r++) {
    for (let c = 0; c < (mesh[0]?.length ?? 0); c++) {
      if (mesh[r][c]) _walkableAll.push([c, r])
    }
  }
}

/**
 * Pick a random walkable tile, optionally biased toward a specific row range.
 */
export function randomWalkableTile(
  mesh: boolean[][],
  nearRow?: number,
  rowRange: number = 6,
): [number, number] {
  ensureWalkableIndex(mesh)
  if (!_walkableAll || _walkableAll.length === 0) return [0, 0]

  if (nearRow !== undefined) {
    const rMin = Math.max(0, nearRow - rowRange)
    const rMax = Math.min(mesh.length - 1, nearRow + rowRange)
    // Filter from pre-built index
    const nearby = _walkableAll.filter(([, r]) => r >= rMin && r <= rMax)
    if (nearby.length > 0) {
      return nearby[Math.floor(Math.random() * nearby.length)]
    }
  }

  return _walkableAll[Math.floor(Math.random() * _walkableAll.length)]
}
