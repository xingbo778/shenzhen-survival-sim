/**
 * Buildings3D — textured BoxGeometry buildings sized to their tile footprint.
 *
 * Each building occupies a specific number of tiles (tileW × tileH).
 * The box width/depth matches the footprint exactly (with a small margin).
 * `scale` only affects height, never the footprint.
 *
 * Landmark buildings (市民中心, 平安金融中心, 会展中心, etc.) get unique
 * procedural geometry instead of generic boxes.
 */

import * as THREE from 'three'
import type { SceneObject } from '../sceneTiles'
import { TILE_SIZE }        from './ThreeScene'
import { isFurnitureKey }   from './StreetFurniture3D'

// ── Building base height table ───────────────────────────────────────
const MODEL_META: Record<string, { h: number; color: string }> = {
  office_tower:       { h: 6.0, color: '#4488BB' },
  office_tower_v1:    { h: 5.5, color: '#44AA88' },
  office_tower_v2:    { h: 7.0, color: '#8899BB' },
  office_tower_v3:    { h: 6.5, color: '#5599CC' },
  office_tower_v4:    { h: 5.8, color: '#445566' },
  office_tower_v5:    { h: 7.5, color: '#6699CC' },
  cbd_building:       { h: 4.5, color: '#336699' },
  cbd_building_v1:    { h: 4.0, color: '#667788' },
  cbd_building_v2:    { h: 5.0, color: '#AA9955' },
  cbd_building_v3:    { h: 4.2, color: '#778899' },
  cbd_building_v4:    { h: 5.5, color: '#BBAA88' },
  cbd_building_v5:    { h: 4.8, color: '#DDDDDD' },
  apartment_block:    { h: 3.0, color: '#AA9977' },
  apartment_block_v1: { h: 2.6, color: '#88AABB' },
  apartment_block_v2: { h: 2.8, color: '#CC8877' },
  apartment_block_v3: { h: 3.2, color: '#999999' },
  apartment_block_v4: { h: 2.5, color: '#CCBB66' },
  shop_building:      { h: 1.5, color: '#CCAA66' },
  shop_building_v1:   { h: 1.3, color: '#CC7744' },
  shop_building_v2:   { h: 1.4, color: '#EEEEEE' },
  shop_building_v3:   { h: 1.6, color: '#889999' },
  village_building:   { h: 2.5, color: '#888877' },
  village_building_v1:{ h: 2.2, color: '#AA7744' },
  village_building_v2:{ h: 2.3, color: '#668866' },
  village_building_v3:{ h: 2.4, color: '#777766' },
  palm_tree:          { h: 2.0, color: '#226611' },
  street_tree:        { h: 1.5, color: '#336622' },
  metro_entrance:     { h: 0.8, color: '#114499' },
  fountain:           { h: 0.5, color: '#4488CC' },
  // Landmarks
  landmark_civic:     { h: 4.0, color: '#CCDDEE' },
  landmark_pingan:    { h: 18.0, color: '#88AACC' },
  landmark_expo:      { h: 3.0, color: '#BBCCDD' },
  landmark_kk100:     { h: 14.0, color: '#6688AA' },
}

const DEFAULT_META = { h: 2.0, color: '#666677' }

// ── Landmark keys ────────────────────────────────────────────────────
const LANDMARK_KEYS = new Set([
  'landmark_civic', 'landmark_pingan', 'landmark_expo', 'landmark_kk100',
])

function isLandmarkKey(key: string): boolean {
  return LANDMARK_KEYS.has(key)
}

// ── Texture loading ──────────────────────────────────────────────────
const texLoader = new THREE.TextureLoader()
const texCache  = new Map<string, THREE.Texture>()
const matCache  = new Map<string, THREE.MeshLambertMaterial>()

function loadTex(url: string): THREE.Texture {
  if (texCache.has(url)) return texCache.get(url)!
  const tex = texLoader.load(url)
  tex.colorSpace = THREE.SRGBColorSpace
  tex.wrapS = THREE.RepeatWrapping
  tex.wrapT = THREE.RepeatWrapping
  tex.generateMipmaps = true
  tex.minFilter = THREE.LinearMipmapLinearFilter
  texCache.set(url, tex)
  return tex
}

function getBuildingTextures(key: string) {
  const base = `/sprites/buildings/textures/${key}`
  return {
    facade: loadTex(`${base}_facade.png`),
    roof:   loadTex(`${base}_roof.png`),
  }
}

// ── Seeded random ────────────────────────────────────────────────────
let _seed = 1
function sr(): number {
  _seed = (_seed * 16807 + 0) % 2147483647
  return (_seed - 1) / 2147483646
}

// ── Landmark geometry builders ───────────────────────────────────────

function buildLandmarkCivic(width: number, depth: number): THREE.Object3D {
  // 市民中心 — low curved roof with wings, like a giant bird
  const obj = new THREE.Object3D()
  const bodyH = 2.5
  const bodyMat = new THREE.MeshLambertMaterial({ color: 0xDDEEFF })
  const glassMat = new THREE.MeshLambertMaterial({ color: 0x88BBDD, transparent: true, opacity: 0.6 })

  // Central dome
  const domeR = Math.min(width, depth) * 0.3
  const dome = new THREE.Mesh(
    new THREE.SphereGeometry(domeR, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2),
    glassMat,
  )
  dome.position.y = bodyH
  obj.add(dome)

  // Main body — wide flat box
  const body = new THREE.Mesh(new THREE.BoxGeometry(width, bodyH, depth), bodyMat)
  body.position.y = bodyH / 2
  obj.add(body)

  // Wing extensions
  const wingW = width * 0.15, wingH = bodyH * 0.6, wingD = depth * 1.1
  const wingMat = new THREE.MeshLambertMaterial({ color: 0xCCDDEE })
  for (const side of [-1, 1]) {
    const wing = new THREE.Mesh(new THREE.BoxGeometry(wingW, wingH, wingD), wingMat)
    wing.position.set(side * (width / 2 + wingW / 2), wingH / 2, 0)
    obj.add(wing)
  }

  // Roof overhang
  const roofGeo = new THREE.BoxGeometry(width * 1.15, 0.15, depth * 1.15)
  const roof = new THREE.Mesh(roofGeo, new THREE.MeshLambertMaterial({ color: 0xEEEEEE }))
  roof.position.y = bodyH
  obj.add(roof)

  return obj
}

function buildLandmarkPingan(width: number, depth: number): THREE.Object3D {
  // 平安金融中心 — tallest building in Shenzhen, tapered tower with spire
  const obj = new THREE.Object3D()
  const totalH = 18

  // Main tower — tapered
  const towerGeo = new THREE.CylinderGeometry(
    Math.min(width, depth) * 0.25,  // top radius (narrower)
    Math.min(width, depth) * 0.4,   // bottom radius
    totalH * 0.85,
    8,
  )
  const towerMat = new THREE.MeshLambertMaterial({ color: 0x88AACC })
  const tower = new THREE.Mesh(towerGeo, towerMat)
  tower.position.y = totalH * 0.85 / 2
  obj.add(tower)

  // Glass curtain wall effect — slightly larger transparent shell
  const glassMat = new THREE.MeshLambertMaterial({
    color: 0xAADDFF, transparent: true, opacity: 0.3,
  })
  const glassGeo = new THREE.CylinderGeometry(
    Math.min(width, depth) * 0.26,
    Math.min(width, depth) * 0.41,
    totalH * 0.85,
    8,
  )
  const glass = new THREE.Mesh(glassGeo, glassMat)
  glass.position.y = totalH * 0.85 / 2
  obj.add(glass)

  // Spire
  const spireH = totalH * 0.15
  const spireGeo = new THREE.ConeGeometry(0.15, spireH, 4)
  const spireMat = new THREE.MeshLambertMaterial({ color: 0xCCCCCC })
  const spire = new THREE.Mesh(spireGeo, spireMat)
  spire.position.y = totalH * 0.85 + spireH / 2
  obj.add(spire)

  // Base podium
  const podiumH = 1.5
  const podium = new THREE.Mesh(
    new THREE.BoxGeometry(width * 0.9, podiumH, depth * 0.9),
    new THREE.MeshLambertMaterial({ color: 0x667788 }),
  )
  podium.position.y = podiumH / 2
  obj.add(podium)

  return obj
}

function buildLandmarkExpo(width: number, depth: number): THREE.Object3D {
  // 会展中心 — long, low, wavy-roofed exhibition hall
  const obj = new THREE.Object3D()
  const bodyH = 2.5
  const bodyMat = new THREE.MeshLambertMaterial({ color: 0xBBCCDD })

  // Main body
  const body = new THREE.Mesh(new THREE.BoxGeometry(width, bodyH, depth), bodyMat)
  body.position.y = bodyH / 2
  obj.add(body)

  // Wavy roof segments
  const segments = 5
  const segW = width / segments
  const roofMat = new THREE.MeshLambertMaterial({ color: 0xEEEEFF })
  for (let i = 0; i < segments; i++) {
    const archGeo = new THREE.CylinderGeometry(segW * 0.4, segW * 0.4, depth * 0.95, 8, 1, false, 0, Math.PI)
    const arch = new THREE.Mesh(archGeo, roofMat)
    arch.rotation.z = Math.PI / 2
    arch.rotation.y = Math.PI / 2
    arch.position.set(-width / 2 + segW * (i + 0.5), bodyH + segW * 0.15, 0)
    obj.add(arch)
  }

  // Glass entrance
  const entranceMat = new THREE.MeshLambertMaterial({ color: 0x88BBDD, transparent: true, opacity: 0.5 })
  const entrance = new THREE.Mesh(new THREE.BoxGeometry(width * 0.3, bodyH * 0.8, 0.3), entranceMat)
  entrance.position.set(0, bodyH * 0.4, depth / 2 + 0.15)
  obj.add(entrance)

  return obj
}

function buildLandmarkKK100(width: number, depth: number): THREE.Object3D {
  // 京基100 — second tallest, rectangular tapered tower
  const obj = new THREE.Object3D()
  const totalH = 14

  // Main tower — box that tapers
  const sections = 4
  const sectionH = totalH / sections
  for (let i = 0; i < sections; i++) {
    const taper = 1 - i * 0.08
    const sW = width * 0.7 * taper
    const sD = depth * 0.7 * taper
    const mat = new THREE.MeshLambertMaterial({
      color: new THREE.Color(0x6688AA).lerp(new THREE.Color(0x88AACC), i / sections),
    })
    const section = new THREE.Mesh(new THREE.BoxGeometry(sW, sectionH, sD), mat)
    section.position.y = sectionH * i + sectionH / 2
    obj.add(section)
  }

  // Crown
  const crownH = 1.0
  const crown = new THREE.Mesh(
    new THREE.CylinderGeometry(0.2, width * 0.15, crownH, 6),
    new THREE.MeshLambertMaterial({ color: 0xCCCCCC }),
  )
  crown.position.y = totalH + crownH / 2
  obj.add(crown)

  return obj
}

function buildLandmarkLOD(key: string, width: number, depth: number): THREE.Object3D | null {
  let detailed: THREE.Object3D | null = null
  switch (key) {
    case 'landmark_civic':  detailed = buildLandmarkCivic(width, depth); break
    case 'landmark_pingan': detailed = buildLandmarkPingan(width, depth); break
    case 'landmark_expo':   detailed = buildLandmarkExpo(width, depth); break
    case 'landmark_kk100':  detailed = buildLandmarkKK100(width, depth); break
    default: return null
  }
  if (!detailed) return null

  const meta = MODEL_META[key] ?? DEFAULT_META
  const lod = new THREE.LOD()

  // Level 0: detailed geometry (close range)
  lod.addLevel(detailed, 0)

  // Level 1: simple box (far range, > 60 units)
  const simpleH = meta.h
  const simpleMat = new THREE.MeshLambertMaterial({ color: new THREE.Color(meta.color) })
  const simpleBox = new THREE.Mesh(new THREE.BoxGeometry(width, simpleH, depth), simpleMat)
  simpleBox.position.y = simpleH / 2
  const simpleGroup = new THREE.Object3D()
  simpleGroup.add(simpleBox)
  lod.addLevel(simpleGroup, 60)

  return lod
}

// ── Build a single building sized to its tile footprint ──────────────

const MARGIN = 0.12  // gap between building edge and tile boundary

function buildTexturedBox(
  key: string,
  heightScale: number,
  tileW: number,
  tileH: number,
): THREE.Object3D {
  const meta  = MODEL_META[key] ?? DEFAULT_META
  const color = new THREE.Color(meta.color)

  // Footprint: exactly tileW × tileH tiles, minus margin
  const width  = tileW * TILE_SIZE - MARGIN * 2
  const depth  = tileH * TILE_SIZE - MARGIN * 2

  // Height: base height × heightScale with slight random variation
  const hv     = 0.85 + sr() * 0.3
  const height = meta.h * heightScale * hv

  const { facade, roof } = getBuildingTextures(key)

  const facadeKey = `facade:${key}`
  const roofKey   = `roof:${key}`
  const bottomKey = 'bottom'
  if (!matCache.has(facadeKey)) matCache.set(facadeKey, new THREE.MeshLambertMaterial({ map: facade }))
  if (!matCache.has(roofKey))   matCache.set(roofKey,   new THREE.MeshLambertMaterial({ map: roof }))
  if (!matCache.has(bottomKey)) matCache.set(bottomKey, new THREE.MeshLambertMaterial({ color: 0x222222 }))
  const facadeMat = matCache.get(facadeKey)!
  const roofMat   = matCache.get(roofKey)!
  const bottomMat = matCache.get(bottomKey)!

  const materials = [
    facadeMat, facadeMat,   // +x, -x
    roofMat,   bottomMat,   // +y, -y
    facadeMat, facadeMat,   // +z, -z
  ]

  const obj = new THREE.Object3D()

  // Main body
  const geom = new THREE.BoxGeometry(width, height, depth)
  const mesh = new THREE.Mesh(geom, materials)
  mesh.castShadow    = false
  mesh.receiveShadow = false
  mesh.position.y    = height / 2
  obj.add(mesh)

  // Stepped setback for tall buildings
  if (meta.h >= 4.0 && sr() > 0.4) {
    const setbackH = height * (0.12 + sr() * 0.18)
    const setbackW = width * 0.65
    const setbackD = depth * 0.65
    const setbackGeom = new THREE.BoxGeometry(setbackW, setbackH, setbackD)
    const setbackMat = new THREE.MeshLambertMaterial({ color: color.clone().multiplyScalar(0.9) })
    const setback = new THREE.Mesh(setbackGeom, [
      setbackMat, setbackMat,
      roofMat, setbackMat,
      setbackMat, setbackMat,
    ])
    setback.castShadow = true
    setback.position.y = height + setbackH / 2
    obj.add(setback)
  }

  // Rooftop antenna for some tall buildings
  if (meta.h >= 3.5 && sr() > 0.55) {
    const antennaH = height * (0.08 + sr() * 0.12)
    const antennaGeom = new THREE.CylinderGeometry(0.02, 0.04, antennaH, 4)
    const antennaMat = new THREE.MeshLambertMaterial({ color: 0x888888 })
    const antenna = new THREE.Mesh(antennaGeom, antennaMat)
    antenna.castShadow = true
    antenna.position.y = height + antennaH / 2
    antenna.position.x = (sr() - 0.5) * width * 0.2
    antenna.position.z = (sr() - 0.5) * depth * 0.2
    obj.add(antenna)
  }

  return obj
}

// ── Public API ────────────────────────────────────────────────────────

export interface Buildings3DHandle {
  group:   THREE.Group
  updateLOD: (camera: THREE.Camera) => void
  dispose: () => void
}

export async function buildBuildings3D(objects: SceneObject[]): Promise<Buildings3DHandle> {
  const group = new THREE.Group()
  _seed = 12345

  objects.forEach(obj => {
    const key = obj.pngKey ?? ''
    if (!key) return
    if (isFurnitureKey(key)) return

    const heightScale = obj.scale ?? 1
    const tileW = obj.tileW ?? 2
    const tileH = obj.tileH ?? 2

    const posX = (obj.col + tileW / 2) * TILE_SIZE
    const posZ = (obj.row + tileH / 2) * TILE_SIZE

    let instance: THREE.Object3D

    if (isLandmarkKey(key)) {
      const width = tileW * TILE_SIZE - MARGIN * 2
      const depth = tileH * TILE_SIZE - MARGIN * 2
      const lm = buildLandmarkLOD(key, width, depth)
      if (!lm) return
      instance = lm
    } else {
      instance = buildTexturedBox(key, heightScale, tileW, tileH)
    }

    instance.position.x = posX
    instance.position.z = posZ
    group.add(instance)
  })

  function updateLOD(camera: THREE.Camera) {
    group.traverse(child => {
      if (child instanceof THREE.LOD) {
        child.update(camera)
      }
    })
  }

  function dispose() {
    group.traverse(child => {
      if (child instanceof THREE.Mesh) {
        child.geometry.dispose()
      }
    })
    matCache.forEach(m => {
      if (m.map) m.map.dispose()
      m.dispose()
    })
    matCache.clear()
    texCache.clear()
  }

  return { group, updateLOD, dispose }
}

export function preloadBuildings(keys: string[]): void {
  keys.forEach(k => getBuildingTextures(k))
}
