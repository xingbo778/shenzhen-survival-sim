/**
 * StreetFurniture3D — loads and places GLB models for trees, traffic lights,
 * road signs, street lamps, benches, and other non-building 3D objects.
 *
 * Falls back to simple procedural geometry when a GLB file is not available.
 */

import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import type { SceneObject } from '../sceneTiles'
import { TILE_SIZE } from './ThreeScene'

const FURNITURE_KEYS = new Set([
  'palm_tree', 'street_tree', 'traffic_light', 'road_sign',
  'street_lamp', 'bench', 'metro_entrance', 'fountain',
  'fire_hydrant', 'trash_bin', 'bus_stop', 'bollard',
  'phone_booth', 'mailbox', 'flower_bed', 'billboard',
])

export function isFurnitureKey(key: string): boolean {
  return FURNITURE_KEYS.has(key)
}

// ── GLB cache ────────────────────────────────────────────────────────
const glbCache = new Map<string, THREE.Object3D | null>()
const glbLoading = new Map<string, Promise<THREE.Object3D | null>>()
const gltfLoader = new GLTFLoader()

// Normalize GLB model to fit within a unit bounding box
function normalizeModel(model: THREE.Object3D): void {
  const box = new THREE.Box3().setFromObject(model)
  const size = new THREE.Vector3()
  box.getSize(size)
  const maxDim = Math.max(size.x, size.y, size.z)
  if (maxDim <= 0) return
  const s = 1.0 / maxDim
  model.scale.multiplyScalar(s)
  // Derive center/bottom from original box scaled, avoiding second Box3 traversal
  const center = new THREE.Vector3()
  box.getCenter(center)
  center.multiplyScalar(s)
  model.position.sub(center)
  model.position.y -= box.min.y * s
}

function loadGLB(key: string): Promise<THREE.Object3D | null> {
  if (glbCache.has(key)) return Promise.resolve(glbCache.get(key)!)
  if (glbLoading.has(key)) return glbLoading.get(key)!

  const url = `/models/furniture/${key}.glb`
  const promise = new Promise<THREE.Object3D | null>((resolve) => {
    gltfLoader.load(
      url,
      (gltf) => {
        const model = gltf.scene
        model.traverse(child => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = false
            child.receiveShadow = true
          }
        })
        normalizeModel(model)
        glbCache.set(key, model)
        resolve(model)
      },
      undefined,
      () => {
        glbCache.set(key, null)
        resolve(null)
      },
    )
  })
  glbLoading.set(key, promise)
  return promise
}

// ── Procedural fallbacks ─────────────────────────────────────────────

function makePalmTree(): THREE.Object3D {
  const g = new THREE.Object3D()
  const trunkGeo = new THREE.CylinderGeometry(0.06, 0.09, 2.2, 6)
  const trunkMat = new THREE.MeshLambertMaterial({ color: 0x8B6914 })
  const trunk = new THREE.Mesh(trunkGeo, trunkMat)
  trunk.position.y = 1.1; trunk.castShadow = false; g.add(trunk)
  const canopyGeo = new THREE.SphereGeometry(0.6, 6, 4)
  const canopyMat = new THREE.MeshLambertMaterial({ color: 0x228B22 })
  const canopy = new THREE.Mesh(canopyGeo, canopyMat)
  canopy.position.y = 2.4; canopy.scale.set(1, 0.6, 1); canopy.castShadow = false; g.add(canopy)
  return g
}

function makeStreetTree(): THREE.Object3D {
  const g = new THREE.Object3D()
  const trunkGeo = new THREE.CylinderGeometry(0.05, 0.07, 1.2, 6)
  const trunkMat = new THREE.MeshLambertMaterial({ color: 0x654321 })
  const trunk = new THREE.Mesh(trunkGeo, trunkMat)
  trunk.position.y = 0.6; trunk.castShadow = false; g.add(trunk)
  const canopyGeo = new THREE.SphereGeometry(0.55, 8, 6)
  const canopyMat = new THREE.MeshLambertMaterial({ color: 0x2E8B57 })
  const canopy = new THREE.Mesh(canopyGeo, canopyMat)
  canopy.position.y = 1.5; canopy.castShadow = false; g.add(canopy)
  return g
}

function makeTrafficLight(): THREE.Object3D {
  const g = new THREE.Object3D()
  const poleGeo = new THREE.CylinderGeometry(0.03, 0.03, 1.8, 6)
  const poleMat = new THREE.MeshLambertMaterial({ color: 0x444444 })
  const pole = new THREE.Mesh(poleGeo, poleMat)
  pole.position.y = 0.9; pole.castShadow = false; g.add(pole)
  // Horizontal arm
  const armGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.6, 4)
  const arm = new THREE.Mesh(armGeo, poleMat)
  arm.position.set(0.3, 1.8, 0); arm.rotation.z = Math.PI / 2; g.add(arm)
  // Light box
  const boxGeo = new THREE.BoxGeometry(0.12, 0.35, 0.1)
  const box = new THREE.Mesh(boxGeo, new THREE.MeshLambertMaterial({ color: 0x222222 }))
  box.position.set(0.6, 1.8, 0); box.castShadow = false; g.add(box)
  const lightGeo = new THREE.SphereGeometry(0.04, 6, 4)
  const colors = [0xff0000, 0xffaa00, 0x00cc00]
  colors.forEach((c, i) => {
    const light = new THREE.Mesh(lightGeo, new THREE.MeshBasicMaterial({ color: c }))
    light.position.set(0.6, 1.9 - i * 0.1, 0.06); g.add(light)
  })
  return g
}

function makeRoadSign(): THREE.Object3D {
  const g = new THREE.Object3D()
  const poleGeo = new THREE.CylinderGeometry(0.02, 0.02, 1.4, 6)
  const poleMat = new THREE.MeshLambertMaterial({ color: 0x888888 })
  const pole = new THREE.Mesh(poleGeo, poleMat)
  pole.position.y = 0.7; pole.castShadow = false; g.add(pole)
  const signGeo = new THREE.BoxGeometry(0.45, 0.3, 0.03)
  const sign = new THREE.Mesh(signGeo, new THREE.MeshLambertMaterial({ color: 0x2255AA }))
  sign.position.y = 1.5; sign.castShadow = false; g.add(sign)
  return g
}

function makeStreetLamp(): THREE.Object3D {
  const g = new THREE.Object3D()
  const poleGeo = new THREE.CylinderGeometry(0.025, 0.03, 2.0, 6)
  const poleMat = new THREE.MeshLambertMaterial({ color: 0x555555 })
  const pole = new THREE.Mesh(poleGeo, poleMat)
  pole.position.y = 1.0; pole.castShadow = false; g.add(pole)
  const armGeo = new THREE.CylinderGeometry(0.015, 0.015, 0.4, 4)
  const arm = new THREE.Mesh(armGeo, poleMat)
  arm.position.set(0.2, 1.95, 0); arm.rotation.z = Math.PI / 2; g.add(arm)
  const lampGeo = new THREE.SphereGeometry(0.08, 6, 4)
  const lamp = new THREE.Mesh(lampGeo, new THREE.MeshBasicMaterial({ color: 0xFFEEAA }))
  lamp.position.set(0.4, 1.95, 0); g.add(lamp)
  return g
}

function makeBench(): THREE.Object3D {
  const g = new THREE.Object3D()
  const woodMat = new THREE.MeshLambertMaterial({ color: 0x8B4513 })
  const metalMat = new THREE.MeshLambertMaterial({ color: 0x333333 })
  const seat = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.04, 0.2), woodMat)
  seat.position.y = 0.3; seat.castShadow = false; g.add(seat)
  const legGeo = new THREE.BoxGeometry(0.03, 0.3, 0.03)
  for (const x of [-0.25, 0.25]) {
    for (const z of [-0.07, 0.07]) {
      const leg = new THREE.Mesh(legGeo, metalMat)
      leg.position.set(x, 0.15, z); g.add(leg)
    }
  }
  const back = new THREE.Mesh(new THREE.BoxGeometry(0.6, 0.2, 0.03), woodMat)
  back.position.set(0, 0.42, -0.1); back.castShadow = false; g.add(back)
  return g
}

function makeMetroEntrance(): THREE.Object3D {
  const g = new THREE.Object3D()
  const base = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.5, 0.5), new THREE.MeshLambertMaterial({ color: 0x114499 }))
  base.position.y = 0.25; base.castShadow = false; g.add(base)
  const canopy = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.05, 0.6), new THREE.MeshLambertMaterial({ color: 0x006633 }))
  canopy.position.y = 0.53; canopy.castShadow = false; g.add(canopy)
  const sign = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.1, 0.03), new THREE.MeshBasicMaterial({ color: 0xFF2222 }))
  sign.position.set(0, 0.6, 0.26); g.add(sign)
  return g
}

function makeFireHydrant(): THREE.Object3D {
  const g = new THREE.Object3D()
  const bodyGeo = new THREE.CylinderGeometry(0.06, 0.08, 0.4, 8)
  const body = new THREE.Mesh(bodyGeo, new THREE.MeshLambertMaterial({ color: 0xCC2222 }))
  body.position.y = 0.2; body.castShadow = false; g.add(body)
  const capGeo = new THREE.SphereGeometry(0.07, 6, 4)
  const cap = new THREE.Mesh(capGeo, new THREE.MeshLambertMaterial({ color: 0xCC2222 }))
  cap.position.y = 0.42; g.add(cap)
  // Side nozzles
  const nozzleGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.08, 4)
  const nozzleMat = new THREE.MeshLambertMaterial({ color: 0xAA1111 })
  for (const side of [-1, 1]) {
    const nozzle = new THREE.Mesh(nozzleGeo, nozzleMat)
    nozzle.position.set(side * 0.08, 0.28, 0); nozzle.rotation.z = Math.PI / 2; g.add(nozzle)
  }
  return g
}

function makeTrashBin(): THREE.Object3D {
  const g = new THREE.Object3D()
  const bodyGeo = new THREE.CylinderGeometry(0.08, 0.1, 0.4, 8)
  const body = new THREE.Mesh(bodyGeo, new THREE.MeshLambertMaterial({ color: 0x336633 }))
  body.position.y = 0.2; body.castShadow = false; g.add(body)
  const lidGeo = new THREE.CylinderGeometry(0.1, 0.1, 0.03, 8)
  const lid = new THREE.Mesh(lidGeo, new THREE.MeshLambertMaterial({ color: 0x224422 }))
  lid.position.y = 0.42; g.add(lid)
  return g
}

function makeBusStop(): THREE.Object3D {
  const g = new THREE.Object3D()
  const poleMat = new THREE.MeshLambertMaterial({ color: 0x666666 })
  // Two poles
  for (const x of [-0.3, 0.3]) {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.02, 0.02, 1.6, 4), poleMat)
    pole.position.set(x, 0.8, 0); pole.castShadow = false; g.add(pole)
  }
  // Roof
  const roof = new THREE.Mesh(new THREE.BoxGeometry(0.7, 0.04, 0.35), new THREE.MeshLambertMaterial({ color: 0x4488CC }))
  roof.position.y = 1.6; roof.castShadow = false; g.add(roof)
  // Back panel
  const panel = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.8, 0.03), new THREE.MeshLambertMaterial({ color: 0x88BBDD }))
  panel.position.set(0, 1.1, -0.16); panel.castShadow = false; g.add(panel)
  // Bench
  const seat = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.03, 0.15), new THREE.MeshLambertMaterial({ color: 0x8B4513 }))
  seat.position.set(0, 0.35, 0); g.add(seat)
  return g
}

function makeBollard(): THREE.Object3D {
  const g = new THREE.Object3D()
  const bodyGeo = new THREE.CylinderGeometry(0.04, 0.05, 0.35, 6)
  const body = new THREE.Mesh(bodyGeo, new THREE.MeshLambertMaterial({ color: 0x888888 }))
  body.position.y = 0.175; body.castShadow = false; g.add(body)
  const topGeo = new THREE.SphereGeometry(0.05, 6, 4)
  const top = new THREE.Mesh(topGeo, new THREE.MeshLambertMaterial({ color: 0xAAAA00 }))
  top.position.y = 0.37; g.add(top)
  return g
}

function makePhoneBooth(): THREE.Object3D {
  const g = new THREE.Object3D()
  const body = new THREE.Mesh(new THREE.BoxGeometry(0.3, 1.0, 0.3), new THREE.MeshLambertMaterial({ color: 0xCC3333, transparent: true, opacity: 0.85 }))
  body.position.y = 0.5; body.castShadow = false; g.add(body)
  const roof = new THREE.Mesh(new THREE.BoxGeometry(0.35, 0.05, 0.35), new THREE.MeshLambertMaterial({ color: 0xAA2222 }))
  roof.position.y = 1.02; g.add(roof)
  return g
}

function makeMailbox(): THREE.Object3D {
  const g = new THREE.Object3D()
  const poleGeo = new THREE.CylinderGeometry(0.02, 0.02, 0.5, 4)
  const pole = new THREE.Mesh(poleGeo, new THREE.MeshLambertMaterial({ color: 0x555555 }))
  pole.position.y = 0.25; g.add(pole)
  const box = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.2, 0.12), new THREE.MeshLambertMaterial({ color: 0x006600 }))
  box.position.y = 0.6; box.castShadow = false; g.add(box)
  return g
}

function makeFlowerBed(): THREE.Object3D {
  const g = new THREE.Object3D()
  const bedGeo = new THREE.CylinderGeometry(0.25, 0.3, 0.12, 8)
  const bed = new THREE.Mesh(bedGeo, new THREE.MeshLambertMaterial({ color: 0x8B6914 }))
  bed.position.y = 0.06; g.add(bed)
  // Flowers
  const colors = [0xFF6699, 0xFFCC00, 0xFF4444, 0xCC66FF, 0xFF8844]
  for (let i = 0; i < 7; i++) {
    const flowerGeo = new THREE.SphereGeometry(0.05 + Math.random() * 0.03, 5, 3)
    const flower = new THREE.Mesh(flowerGeo, new THREE.MeshLambertMaterial({ color: colors[i % colors.length] }))
    const angle = (i / 7) * Math.PI * 2
    const r = 0.1 + Math.random() * 0.1
    flower.position.set(Math.cos(angle) * r, 0.15 + Math.random() * 0.05, Math.sin(angle) * r)
    g.add(flower)
  }
  return g
}

function makeBillboard(): THREE.Object3D {
  const g = new THREE.Object3D()
  const poleMat = new THREE.MeshLambertMaterial({ color: 0x555555 })
  // Two poles
  for (const x of [-0.25, 0.25]) {
    const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.025, 0.025, 2.0, 4), poleMat)
    pole.position.set(x, 1.0, 0); pole.castShadow = false; g.add(pole)
  }
  // Board
  const board = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.5, 0.04), new THREE.MeshLambertMaterial({ color: 0xEEEEEE }))
  board.position.y = 2.2; board.castShadow = false; g.add(board)
  // Frame
  const frame = new THREE.Mesh(new THREE.BoxGeometry(0.84, 0.54, 0.02), new THREE.MeshLambertMaterial({ color: 0x333333 }))
  frame.position.set(0, 2.2, -0.02); g.add(frame)
  return g
}

function makeFountain(): THREE.Object3D {
  const g = new THREE.Object3D()
  const basinGeo = new THREE.CylinderGeometry(0.35, 0.4, 0.15, 12)
  const basin = new THREE.Mesh(basinGeo, new THREE.MeshLambertMaterial({ color: 0x999999 }))
  basin.position.y = 0.075; g.add(basin)
  // Water
  const waterGeo = new THREE.CylinderGeometry(0.32, 0.32, 0.08, 12)
  const water = new THREE.Mesh(waterGeo, new THREE.MeshLambertMaterial({ color: 0x4488CC, transparent: true, opacity: 0.7 }))
  water.position.y = 0.12; g.add(water)
  // Center spout
  const spoutGeo = new THREE.CylinderGeometry(0.03, 0.04, 0.3, 6)
  const spout = new THREE.Mesh(spoutGeo, new THREE.MeshLambertMaterial({ color: 0x888888 }))
  spout.position.y = 0.3; g.add(spout)
  return g
}

const FALLBACK_BUILDERS: Record<string, () => THREE.Object3D> = {
  palm_tree:      makePalmTree,
  street_tree:    makeStreetTree,
  traffic_light:  makeTrafficLight,
  road_sign:      makeRoadSign,
  street_lamp:    makeStreetLamp,
  bench:          makeBench,
  metro_entrance: makeMetroEntrance,
  fountain:       makeFountain,
  fire_hydrant:   makeFireHydrant,
  trash_bin:      makeTrashBin,
  bus_stop:       makeBusStop,
  bollard:        makeBollard,
  phone_booth:    makePhoneBooth,
  mailbox:        makeMailbox,
  flower_bed:     makeFlowerBed,
  billboard:      makeBillboard,
}

// ── Public API ────────────────────────────────────────────────────────

export interface StreetFurniture3DHandle {
  group:   THREE.Group
  dispose: () => void
}

export async function buildStreetFurniture3D(objects: SceneObject[]): Promise<StreetFurniture3DHandle> {
  const group = new THREE.Group()
  const furnitureObjs = objects.filter(o => o.pngKey && isFurnitureKey(o.pngKey))

  // Try loading GLBs for all unique keys
  const uniqueKeys = Array.from(new Set(furnitureObjs.map(o => o.pngKey!)))
  await Promise.all(uniqueKeys.map(k => loadGLB(k)))

  for (const obj of furnitureObjs) {
    const key = obj.pngKey!
    const scale = obj.scale ?? 1.0
    const posX = (obj.col + 0.5) * TILE_SIZE
    const posZ = (obj.row + 0.5) * TILE_SIZE

    const glbTemplate = glbCache.get(key)
    let instance: THREE.Object3D

    if (glbTemplate) {
      instance = glbTemplate.clone()
      // GLB is normalized to 1 unit; scale to desired tile-relative size
      instance.scale.setScalar(scale * TILE_SIZE)
    } else {
      const builder = FALLBACK_BUILDERS[key]
      if (!builder) continue
      instance = builder()
      instance.scale.setScalar(scale)
    }

    instance.position.set(posX, 0, posZ)
    group.add(instance)
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

  return { group, dispose }
}

/** Clear cached GLB models to free memory between scenes. */
export function clearFurnitureCache(): void {
  glbCache.clear()
  glbLoading.clear()
}
