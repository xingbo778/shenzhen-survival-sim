/**
 * Vehicles3D — Shenzhen-specific 3D vehicles on roads.
 *
 * Meshy-generated GLB models for: taxi, bus, meituan, huolala, sweeper, shared_bike
 * Procedural fallback for generic sedans / SUVs.
 */

import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import type { TileType } from '../sceneTiles'
import { TILE_SIZE } from './ThreeScene'

// ── Vehicle kind ─────────────────────────────────────────────────────

type VehicleKind =
  | 'sz_taxi' | 'bus' | 'meituan_scooter' | 'huolala_truck' | 'sweeper' | 'shared_bike'
  | 'sedan_white' | 'sedan_black' | 'sedan_silver' | 'sedan_red'
  | 'suv_white' | 'suv_dark'

interface VehicleDef {
  kind: VehicleKind
  speed: number
  scale: number       // uniform scale applied to the placed mesh
  yOffset: number     // y position offset (ground level)
  glbFile?: string    // if set, load this GLB from /sprites/vehicles/models/
}

const VEHICLE_DEFS: VehicleDef[] = [
  { kind: 'sz_taxi',          speed: 3.0, scale: 0.55, yOffset: 0, glbFile: 'taxi.glb' },
  { kind: 'bus',              speed: 2.0, scale: 0.60, yOffset: 0, glbFile: 'bus.glb' },
  { kind: 'meituan_scooter',  speed: 2.5, scale: 0.45, yOffset: 0, glbFile: 'meituan.glb' },
  { kind: 'huolala_truck',    speed: 2.2, scale: 0.55, yOffset: 0, glbFile: 'huolala.glb' },
  { kind: 'sweeper',          speed: 1.5, scale: 0.45, yOffset: 0, glbFile: 'sweeper.glb' },
  { kind: 'shared_bike',      speed: 2.0, scale: 0.35, yOffset: 0, glbFile: 'shared_bike.glb' },
  { kind: 'sedan_white',      speed: 3.2, scale: 1.0,  yOffset: 0 },
  { kind: 'sedan_black',      speed: 2.8, scale: 1.0,  yOffset: 0 },
  { kind: 'sedan_silver',     speed: 3.1, scale: 1.0,  yOffset: 0 },
  { kind: 'sedan_red',        speed: 3.0, scale: 1.0,  yOffset: 0 },
  { kind: 'suv_white',        speed: 2.7, scale: 1.0,  yOffset: 0 },
  { kind: 'suv_dark',         speed: 2.9, scale: 1.0,  yOffset: 0 },
]

// ── Weighted random selection ────────────────────────────────────────

const VEHICLE_WEIGHTS: Record<VehicleKind, number> = {
  sz_taxi:          14,
  bus:               7,
  meituan_scooter:   9,
  huolala_truck:     5,
  sweeper:           2,
  shared_bike:       4,
  sedan_white:      14,
  sedan_black:      10,
  sedan_silver:      8,
  sedan_red:         4,
  suv_white:         7,
  suv_dark:          4,
}

// ── Seeded random ────────────────────────────────────────────────────

let _vseed = 7777
function vr(): number {
  _vseed = (_vseed * 16807 + 0) % 2147483647
  return (_vseed - 1) / 2147483646
}

function pickVehicleDef(): VehicleDef {
  const totalWeight = VEHICLE_DEFS.reduce((sum, d) => sum + (VEHICLE_WEIGHTS[d.kind] ?? 1), 0)
  let roll = vr() * totalWeight
  for (const def of VEHICLE_DEFS) {
    roll -= VEHICLE_WEIGHTS[def.kind] ?? 1
    if (roll <= 0) return def
  }
  return VEHICLE_DEFS[0]
}

// ── GLB model cache ──────────────────────────────────────────────────

const glbCache = new Map<string, { model: THREE.Object3D; baseY: number }>()
const gltfLoader = new GLTFLoader()

function normalizeModel(model: THREE.Object3D): void {
  model.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      child.castShadow = false
      child.receiveShadow = false
    }
  })

  // Compute bounding box and shift model so its bottom sits at y=0
  const box = new THREE.Box3().setFromObject(model)
  const yMin = box.min.y
  if (yMin < 0) {
    model.position.y -= yMin
  }
}

async function loadGLB(file: string): Promise<THREE.Object3D> {
  if (glbCache.has(file)) return glbCache.get(file)!.model.clone()

  const url = `/sprites/vehicles/models/${file}`
  return new Promise((resolve, reject) => {
    gltfLoader.load(
      url,
      (gltf) => {
        const model = gltf.scene
        normalizeModel(model)
        glbCache.set(file, { model, baseY: 0 })
        resolve(model.clone())
      },
      undefined,
      (err) => reject(err),
    )
  })
}

async function preloadAllGLBs(): Promise<void> {
  const files = VEHICLE_DEFS
    .filter(d => d.glbFile)
    .map(d => d.glbFile!)
  const unique = Array.from(new Set(files))
  await Promise.all(unique.map(async f => {
    try {
      await loadGLB(f)
      // Pre-compute baseY at scale=1 so spawn doesn't need Box3
      const cached = glbCache.get(f)
      if (cached && cached.baseY === 0) {
        const tempClone = cached.model.clone()
        const box = new THREE.Box3().setFromObject(tempClone)
        cached.baseY = -box.min.y
      }
    } catch (e) {
      console.warn(`[Vehicles3D] Failed to load ${f}:`, e)
    }
  }))
}

// ── Procedural fallback meshes ───────────────────────────────────────

function mat(color: number): THREE.MeshLambertMaterial {
  return new THREE.MeshLambertMaterial({ color })
}

function buildProceduralCar(bodyColor: number): THREE.Object3D {
  const g = new THREE.Object3D()
  const w = 0.65, h = 0.40, d = 1.6
  const base = 0.12

  const body = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(bodyColor))
  body.position.y = h / 2 + base
  g.add(body)

  const cabH = h * 0.55
  const cabin = new THREE.Mesh(
    new THREE.BoxGeometry(w * 0.78, cabH, d * 0.40),
    new THREE.MeshLambertMaterial({ color: 0x334455, transparent: true, opacity: 0.7 }),
  )
  cabin.position.y = h + cabH / 2 + base
  cabin.position.z = -d * 0.04
  g.add(cabin)

  const wheelGeo = new THREE.CylinderGeometry(0.10, 0.10, 0.06, 8)
  const wmat = mat(0x222222)
  for (const [px, pz] of [[-w/2-0.02, -d*0.32], [w/2+0.02, -d*0.32], [-w/2-0.02, d*0.32], [w/2+0.02, d*0.32]]) {
    const wheel = new THREE.Mesh(wheelGeo, wmat)
    wheel.rotation.z = Math.PI / 2
    wheel.position.set(px, 0.10, pz)
    g.add(wheel)
  }

  for (const side of [-1, 1]) {
    const hl = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.05, 0.03), mat(0xFFFFDD))
    hl.position.set(side * w * 0.3, h * 0.4 + base, d / 2 + 0.02)
    g.add(hl)
    const tl = new THREE.Mesh(new THREE.BoxGeometry(0.07, 0.05, 0.03), mat(0xFF2222))
    tl.position.set(side * w * 0.3, h * 0.4 + base, -d / 2 - 0.02)
    g.add(tl)
  }

  return g
}

function buildProceduralSUV(bodyColor: number): THREE.Object3D {
  const g = new THREE.Object3D()
  const w = 0.70, h = 0.50, d = 1.8
  const base = 0.14

  const body = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mat(bodyColor))
  body.position.y = h / 2 + base
  g.add(body)

  const cabH = h * 0.6
  const cabin = new THREE.Mesh(
    new THREE.BoxGeometry(w * 0.82, cabH, d * 0.48),
    new THREE.MeshLambertMaterial({ color: 0x334455, transparent: true, opacity: 0.7 }),
  )
  cabin.position.y = h + cabH / 2 + base
  cabin.position.z = -d * 0.03
  g.add(cabin)

  for (const side of [-1, 1]) {
    const rail = new THREE.Mesh(new THREE.BoxGeometry(0.03, 0.03, d * 0.35), mat(0xCCCCCC))
    rail.position.set(side * w * 0.38, h + cabH + base + 0.01, -d * 0.03)
    g.add(rail)
  }

  const wheelGeo = new THREE.CylinderGeometry(0.12, 0.12, 0.07, 8)
  const wmat = mat(0x222222)
  for (const [px, pz] of [[-w/2-0.02, -d*0.32], [w/2+0.02, -d*0.32], [-w/2-0.02, d*0.32], [w/2+0.02, d*0.32]]) {
    const wheel = new THREE.Mesh(wheelGeo, wmat)
    wheel.rotation.z = Math.PI / 2
    wheel.position.set(px, 0.12, pz)
    g.add(wheel)
  }

  for (const side of [-1, 1]) {
    const hl = new THREE.Mesh(new THREE.BoxGeometry(0.10, 0.06, 0.03), mat(0xFFFFDD))
    hl.position.set(side * w * 0.28, h * 0.4 + base, d / 2 + 0.02)
    g.add(hl)
    const tl = new THREE.Mesh(new THREE.BoxGeometry(0.08, 0.06, 0.03), mat(0xFF2222))
    tl.position.set(side * w * 0.28, h * 0.4 + base, -d / 2 - 0.02)
    g.add(tl)
  }

  return g
}

function buildFallbackMesh(kind: VehicleKind): THREE.Object3D {
  switch (kind) {
    case 'sedan_white':   return buildProceduralCar(0xEEEEEE)
    case 'sedan_black':   return buildProceduralCar(0x222222)
    case 'sedan_silver':  return buildProceduralCar(0xBBBBBB)
    case 'sedan_red':     return buildProceduralCar(0xCC2222)
    case 'suv_white':     return buildProceduralSUV(0xF0F0F0)
    case 'suv_dark':      return buildProceduralSUV(0x333344)
    default:              return buildProceduralCar(0x888888)
  }
}

// ── Vehicle state ────────────────────────────────────────────────────

interface Vehicle3D {
  mesh: THREE.Object3D
  x: number
  z: number
  dir: 'h' | 'v'
  sign: 1 | -1
  speed: number
  roadMin: number
  roadMax: number
}

// ── Public API ───────────────────────────────────────────────────────

export interface Vehicles3DHandle {
  group: THREE.Group
  tick: (dt: number) => void
  dispose: () => void
}

function isRoadTile(t: TileType, horizontal: boolean): boolean {
  if (t === 'road_cross' || t.startsWith('road_cross_zebra')) return true
  if (horizontal) return t === 'road_h' || t === 'road_stop_h'
  return t === 'road_v' || t === 'road_stop_v'
}

export async function buildVehicles3D(
  tilemap: TileType[][],
  maxVehicles = 120,
): Promise<Vehicles3DHandle> {
  const group = new THREE.Group()
  const vehicles: Vehicle3D[] = []
  const rows = tilemap.length
  const cols = tilemap[0]?.length ?? 0

  _vseed = 7777

  // Pre-load all GLB models
  await preloadAllGLBs()

  // Find horizontal road lanes
  const hLanes: { row: number; minCol: number; maxCol: number }[] = []
  for (let r = 0; r < rows; r++) {
    let start = -1
    for (let c = 0; c < cols; c++) {
      if (isRoadTile(tilemap[r][c], true)) {
        if (start < 0) start = c
      } else {
        if (start >= 0 && c - start > 8) {
          hLanes.push({ row: r, minCol: start, maxCol: c - 1 })
        }
        start = -1
      }
    }
    if (start >= 0 && cols - start > 8)
      hLanes.push({ row: r, minCol: start, maxCol: cols - 1 })
  }

  // Find vertical road lanes
  const vLanes: { col: number; minRow: number; maxRow: number }[] = []
  for (let c = 0; c < cols; c++) {
    let start = -1
    for (let r = 0; r < rows; r++) {
      if (isRoadTile(tilemap[r][c], false)) {
        if (start < 0) start = r
      } else {
        if (start >= 0 && r - start > 8) {
          vLanes.push({ col: c, minRow: start, maxRow: r - 1 })
        }
        start = -1
      }
    }
    if (start >= 0 && rows - start > 8)
      vLanes.push({ col: c, minRow: start, maxRow: rows - 1 })
  }

  const pickedH = hLanes.filter((_, i) => i % 2 === 0)
  const pickedV = vLanes.filter((_, i) => i % 2 === 0)

  let count = 0

  async function spawnOnLane(
    dir: 'h' | 'v',
    lanePos: number,
    laneMin: number,
    laneMax: number,
  ) {
    const laneLen = laneMax - laneMin
    const numToSpawn = Math.max(1, Math.floor(laneLen / 8))
    for (let i = 0; i < numToSpawn && count < maxVehicles; i++) {
      const def = pickVehicleDef()

      let mesh: THREE.Object3D
      let baseY = 0
      if (def.glbFile && glbCache.has(def.glbFile)) {
        const cached = glbCache.get(def.glbFile)!
        mesh = cached.model.clone()
        mesh.scale.setScalar(def.scale)
        // Use cached baseY scaled proportionally (model is normalized at y=0)
        baseY = cached.baseY * def.scale
      } else {
        mesh = buildFallbackMesh(def.kind)
      }

      const sign: 1 | -1 = (lanePos + i) % 2 === 0 ? 1 : -1
      const fraction = (i + 0.2 + vr() * 0.6) / numToSpawn
      const laneStart = laneMin + fraction * laneLen

      let x: number, z: number
      if (dir === 'h') {
        x = (laneStart + 0.5) * TILE_SIZE
        z = (lanePos + 0.5) * TILE_SIZE
        mesh.rotation.y = sign > 0 ? 0 : Math.PI
      } else {
        x = (lanePos + 0.5) * TILE_SIZE
        z = (laneStart + 0.5) * TILE_SIZE
        mesh.rotation.y = sign > 0 ? Math.PI / 2 : -Math.PI / 2
      }

      mesh.position.set(x, baseY, z)
      group.add(mesh)

      vehicles.push({
        mesh, x, z,
        dir, sign,
        speed: def.speed * (0.8 + vr() * 0.4),
        roadMin: laneMin * TILE_SIZE,
        roadMax: (laneMax + 1) * TILE_SIZE,
      })
      count++
    }
  }

  for (const lane of pickedH) {
    if (count >= maxVehicles) break
    await spawnOnLane('h', lane.row, lane.minCol, lane.maxCol)
  }

  for (const lane of pickedV) {
    if (count >= maxVehicles) break
    await spawnOnLane('v', lane.col, lane.minRow, lane.maxRow)
  }

  function tick(dt: number) {
    for (const v of vehicles) {
      if (v.dir === 'h') {
        v.x += v.sign * v.speed * TILE_SIZE * dt
        if (v.sign > 0 && v.x > v.roadMax) v.x = v.roadMin
        if (v.sign < 0 && v.x < v.roadMin) v.x = v.roadMax
        v.mesh.position.x = v.x
      } else {
        v.z += v.sign * v.speed * TILE_SIZE * dt
        if (v.sign > 0 && v.z > v.roadMax) v.z = v.roadMin
        if (v.sign < 0 && v.z < v.roadMin) v.z = v.roadMax
        v.mesh.position.z = v.z
      }
    }
  }

  function dispose() {
    group.traverse(child => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose()
        const mats = Array.isArray(child.material) ? child.material : [child.material]
        mats.forEach(m => {
          if (m.map) m.map.dispose()
          m.dispose()
        })
      }
    })
  }

  return { group, tick, dispose }
}

/** Clear cached GLB models to free memory between scenes. */
export function clearVehicleCache(): void {
  glbCache.clear()
}
