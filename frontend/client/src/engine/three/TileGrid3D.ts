/**
 * TileGrid3D — builds a flat ground mesh from the tilemap.
 *
 * Each tile type gets a distinct canvas-painted texture so the ground
 * looks like the existing 2D tile renderer, but lies in 3D space.
 * For performance all tiles of the same type share the same material,
 * and we use InstancedMesh per tile type.
 */

import * as THREE from 'three'
import type { TileType } from '../sceneTiles'
import { TILE_COLORS }   from '../sceneTiles'
import { TILE_SIZE }     from './ThreeScene'

// ── Texture cache ─────────────────────────────────────────────────────
const TEX_CACHE = new Map<TileType, THREE.CanvasTexture>()

function paintTileCanvas(type: TileType): HTMLCanvasElement {
  const S  = 64
  const c  = document.createElement('canvas')
  c.width  = S
  c.height = S
  const ctx = c.getContext('2d')!
  const col = TILE_COLORS[type]

  ctx.fillStyle = col.base
  ctx.fillRect(0, 0, S, S)

  if (col.detail) {
    // Fine noise
    for (let i = 0; i < 120; i++) {
      ctx.fillStyle = col.detail
      const px = Math.floor(Math.random() * S)
      const py = Math.floor(Math.random() * S)
      const pw = 1 + Math.floor(Math.random() * 2)
      ctx.fillRect(px, py, pw, 1)
    }
  }

  if (col.line) {
    ctx.strokeStyle = col.line
    ctx.lineWidth   = 0.5

    if (type === 'road_h') {
      // Asphalt texture variation
      ctx.fillStyle = '#505050'
      for (let i = 0; i < 30; i++) {
        ctx.fillRect(Math.random() * S, Math.random() * S, 2 + Math.random() * 3, 1)
      }
      // Double yellow center line (Shenzhen-style)
      ctx.strokeStyle = '#FFCC00'
      ctx.lineWidth = 1.0
      ctx.beginPath()
      ctx.moveTo(0, S / 2 - 1.5); ctx.lineTo(S, S / 2 - 1.5)
      ctx.moveTo(0, S / 2 + 1.5); ctx.lineTo(S, S / 2 + 1.5)
      ctx.stroke()
      // White dashed lane lines
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 0.6
      ctx.setLineDash([6, 8])
      ctx.beginPath()
      ctx.moveTo(0, S * 0.25); ctx.lineTo(S, S * 0.25)
      ctx.moveTo(0, S * 0.75); ctx.lineTo(S, S * 0.75)
      ctx.stroke()
      ctx.setLineDash([])
      // Solid white edge lines
      ctx.lineWidth = 0.8
      ctx.beginPath()
      ctx.moveTo(0, 2); ctx.lineTo(S, 2)
      ctx.moveTo(0, S - 2); ctx.lineTo(S, S - 2)
      ctx.stroke()
    } else if (type === 'road_v') {
      ctx.fillStyle = '#505050'
      for (let i = 0; i < 30; i++) {
        ctx.fillRect(Math.random() * S, Math.random() * S, 1, 2 + Math.random() * 3)
      }
      ctx.strokeStyle = '#FFCC00'
      ctx.lineWidth = 1.0
      ctx.beginPath()
      ctx.moveTo(S / 2 - 1.5, 0); ctx.lineTo(S / 2 - 1.5, S)
      ctx.moveTo(S / 2 + 1.5, 0); ctx.lineTo(S / 2 + 1.5, S)
      ctx.stroke()
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 0.6
      ctx.setLineDash([6, 8])
      ctx.beginPath()
      ctx.moveTo(S * 0.25, 0); ctx.lineTo(S * 0.25, S)
      ctx.moveTo(S * 0.75, 0); ctx.lineTo(S * 0.75, S)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.lineWidth = 0.8
      ctx.beginPath()
      ctx.moveTo(2, 0); ctx.lineTo(2, S)
      ctx.moveTo(S - 2, 0); ctx.lineTo(S - 2, S)
      ctx.stroke()
    } else if (type === 'road_cross') {
      // Intersection center — clean asphalt, no markings
      ctx.fillStyle = '#505050'
      for (let i = 0; i < 15; i++) {
        ctx.fillRect(Math.random() * S, Math.random() * S, 2, 2)
      }
    } else if (type === 'road_cross_zebra_n' || type === 'road_cross_zebra_s'
      || type === 'road_cross_zebra_w' || type === 'road_cross_zebra_e') {
      // Crosswalk zebra stripes at intersection edge
      ctx.fillStyle = '#505050'
      for (let i = 0; i < 10; i++) {
        ctx.fillRect(Math.random() * S, Math.random() * S, 2, 2)
      }
      const sw = 3, sg = 4  // stripe width, gap
      ctx.fillStyle = 'rgba(255,255,255,0.8)'
      if (type === 'road_cross_zebra_n') {
        // Stripes along top edge (pedestrians cross N-S)
        for (let x = 3; x < S - 3; x += sw + sg)
          ctx.fillRect(x, 1, sw, S * 0.3)
      } else if (type === 'road_cross_zebra_s') {
        for (let x = 3; x < S - 3; x += sw + sg)
          ctx.fillRect(x, S * 0.7, sw, S * 0.3 - 1)
      } else if (type === 'road_cross_zebra_w') {
        for (let y = 3; y < S - 3; y += sw + sg)
          ctx.fillRect(1, y, S * 0.3, sw)
      } else {
        for (let y = 3; y < S - 3; y += sw + sg)
          ctx.fillRect(S * 0.7, y, S * 0.3 - 1, sw)
      }
    } else if (type === 'road_stop_h') {
      // road_h approaching intersection — has stop line
      ctx.fillStyle = '#505050'
      for (let i = 0; i < 20; i++) {
        ctx.fillRect(Math.random() * S, Math.random() * S, 2 + Math.random() * 3, 1)
      }
      // Yellow center line
      ctx.strokeStyle = '#FFCC00'
      ctx.lineWidth = 1.0
      ctx.beginPath()
      ctx.moveTo(0, S / 2 - 1.5); ctx.lineTo(S, S / 2 - 1.5)
      ctx.moveTo(0, S / 2 + 1.5); ctx.lineTo(S, S / 2 + 1.5)
      ctx.stroke()
      // White dashed lane lines
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 0.6
      ctx.setLineDash([6, 8])
      ctx.beginPath()
      ctx.moveTo(0, S * 0.25); ctx.lineTo(S * 0.85, S * 0.25)
      ctx.moveTo(0, S * 0.75); ctx.lineTo(S * 0.85, S * 0.75)
      ctx.stroke()
      ctx.setLineDash([])
      // Solid white stop line on right edge
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(S - 2, 2); ctx.lineTo(S - 2, S - 2)
      ctx.stroke()
    } else if (type === 'road_stop_v') {
      ctx.fillStyle = '#505050'
      for (let i = 0; i < 20; i++) {
        ctx.fillRect(Math.random() * S, Math.random() * S, 1, 2 + Math.random() * 3)
      }
      ctx.strokeStyle = '#FFCC00'
      ctx.lineWidth = 1.0
      ctx.beginPath()
      ctx.moveTo(S / 2 - 1.5, 0); ctx.lineTo(S / 2 - 1.5, S)
      ctx.moveTo(S / 2 + 1.5, 0); ctx.lineTo(S / 2 + 1.5, S)
      ctx.stroke()
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 0.6
      ctx.setLineDash([6, 8])
      ctx.beginPath()
      ctx.moveTo(S * 0.25, 0); ctx.lineTo(S * 0.25, S * 0.85)
      ctx.moveTo(S * 0.75, 0); ctx.lineTo(S * 0.75, S * 0.85)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.strokeStyle = '#FFFFFF'
      ctx.lineWidth = 2
      ctx.beginPath()
      ctx.moveTo(2, S - 2); ctx.lineTo(S - 2, S - 2)
      ctx.stroke()
    } else if (type === 'sidewalk' || type === 'sidewalk_edge') {
      ctx.strokeStyle = col.line
      ctx.lineWidth   = 0.5
      ctx.beginPath()
      for (let x = 8; x < S; x += 8) {
        ctx.moveTo(x, 0); ctx.lineTo(x, S)
      }
      ctx.stroke()
    } else if (type === 'grass' || type === 'grass_lush') {
      for (let i = 0; i < 20; i++) {
        const bx = Math.random() * S
        const by = Math.random() * S
        ctx.strokeStyle = col.line
        ctx.lineWidth   = 0.5
        ctx.beginPath()
        ctx.moveTo(bx, by + 2)
        ctx.lineTo(bx - 1, by - 2)
        ctx.moveTo(bx, by + 2)
        ctx.lineTo(bx + 1, by - 2)
        ctx.stroke()
      }
    } else if (type === 'tile_plaza') {
      ctx.strokeStyle = col.line
      ctx.lineWidth   = 0.5
      for (let x = 0; x < S; x += 8) {
        ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, S); ctx.stroke()
      }
      for (let y = 0; y < S; y += 8) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(S, y); ctx.stroke()
      }
    } else if (type === 'water' || type === 'water_edge') {
      ctx.strokeStyle = col.line
      ctx.lineWidth   = 0.5
      ctx.setLineDash([4, 3])
      for (let y = 4; y < S; y += 10) {
        ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(S, y); ctx.stroke()
      }
      ctx.setLineDash([])
    }
  }

  return c
}

function getTileTexture(type: TileType): THREE.CanvasTexture {
  if (TEX_CACHE.has(type)) return TEX_CACHE.get(type)!
  const canvas  = paintTileCanvas(type)
  const tex     = new THREE.CanvasTexture(canvas)
  tex.wrapS     = THREE.RepeatWrapping
  tex.wrapT     = THREE.RepeatWrapping
  tex.repeat.set(1, 1)
  tex.colorSpace = THREE.SRGBColorSpace
  TEX_CACHE.set(type, tex)
  return tex
}

// ── Public API ────────────────────────────────────────────────────────

export interface TileGrid3DHandle {
  group:   THREE.Group
  dispose: () => void
}

export function buildTileGrid3D(tilemap: TileType[][]): TileGrid3DHandle {
  const group  = new THREE.Group()
  const rows   = tilemap.length
  const cols   = tilemap[0]?.length ?? 0

  // Group tiles by type → InstancedMesh per type
  const typeInstances = new Map<TileType, THREE.Matrix4[]>()
  const geom = new THREE.PlaneGeometry(TILE_SIZE, TILE_SIZE)
  const rotMat = new THREE.Matrix4().makeRotationX(-Math.PI / 2)

  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      const type = tilemap[r][c]
      if (!typeInstances.has(type)) typeInstances.set(type, [])
      const m = new THREE.Matrix4()
      m.makeTranslation(
        (c + 0.5) * TILE_SIZE,
        0,
        (r + 0.5) * TILE_SIZE,
      )
      m.multiply(rotMat)
      typeInstances.get(type)!.push(m)
    }
  }

  const allMeshes: THREE.InstancedMesh[] = []

  typeInstances.forEach((matrices, type) => {
    const mat  = new THREE.MeshLambertMaterial({
      map:  getTileTexture(type),
      side: THREE.FrontSide,
    })
    const mesh = new THREE.InstancedMesh(geom, mat, matrices.length)
    mesh.receiveShadow = true
    matrices.forEach((m, i) => mesh.setMatrixAt(i, m))
    mesh.instanceMatrix.needsUpdate = true
    group.add(mesh)
    allMeshes.push(mesh)
  })

  function dispose() {
    allMeshes.forEach(m => {
      m.dispose()
      const mat = m.material as THREE.MeshLambertMaterial
      if (mat.map) mat.map.dispose()
      mat.dispose()
    })
    geom.dispose()
    TEX_CACHE.clear()
  }

  return { group, dispose }
}
