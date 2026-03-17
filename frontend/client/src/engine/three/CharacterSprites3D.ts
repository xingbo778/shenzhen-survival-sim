/**
 * CharacterSprites3D — renders game entities as 3D GLB models when available,
 * falling back to billboard sprites from 2D sprite sheets.
 *
 * GLB models are loaded from /models/characters/{sheetKey}.glb
 * and normalized to a consistent height. They rotate to face the
 * movement direction.
 */

import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { CSS2DObject } from 'three/addons/renderers/CSS2DRenderer.js'
import type { GameEntity } from '../gameEntity'
import type { Facing }     from '../gameEntity'
import type { WorldState } from '@/types/world'
import {
  CHAR_SHEETS,
  CHAR_CELL_W, CHAR_CELL_H,
  getCharSheetKey,
} from '../charSprites'
import { getImage, preloadImage } from '../imageCache'
import { TILE_SIZE }               from './ThreeScene'

// ── Constants ─────────────────────────────────────────────────────────
const SHEET_COLS  = 8
const SHEET_ROWS  = 6

const FACING_COL: Record<Facing, number> = {
  front: 0, back: 1, left: 2, right: 3,
  front_left: 4, back_left: 5, front_right: 6, back_right: 7,
}

// No more static FACING_ANGLE table — we compute the angle from the actual
// movement delta (prevX/Z → worldX/Z) so the model always faces exactly
// where it is walking, regardless of coordinate-system quirks.

const CHAR_HEIGHT = TILE_SIZE * 2.5
const SPRITE_WORLD_H = CHAR_HEIGHT

// Walk animation parameters
const WALK_FREQ = 3.5         // steps per second (natural walking pace)
const WALK_LEAN = 0.06        // forward/back lean in radians (~3.4°)
const WALK_BOB  = 0.04        // vertical bounce amplitude

// ── GLB model cache ──────────────────────────────────────────────────
const gltfLoader = new GLTFLoader()

interface CharModel {
  scene: THREE.Object3D
  baseScale: number  // uniform scale that makes the model CHAR_HEIGHT tall
}

const glbCache = new Map<string, CharModel | null>()
const glbLoading = new Map<string, Promise<CharModel | null>>()

function loadCharGLB(key: string): Promise<CharModel | null> {
  if (glbCache.has(key)) return Promise.resolve(glbCache.get(key)!)
  if (glbLoading.has(key)) return glbLoading.get(key)!

  const url = `/models/characters/${key}.glb`
  const promise = new Promise<CharModel | null>((resolve) => {
    gltfLoader.load(
      url,
      (gltf) => {
        const model = gltf.scene
        model.traverse(child => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true
            child.receiveShadow = true
          }
        })

        // Measure raw bounding box at identity scale
        const box = new THREE.Box3().setFromObject(model)
        const size = new THREE.Vector3()
        box.getSize(size)
        const rawH = size.y || 1

        // Compute uniform scale to reach CHAR_HEIGHT
        const baseScale = CHAR_HEIGHT / rawH

        // Center horizontally, feet on y=0; keep original model orientation
        const center = new THREE.Vector3()
        box.getCenter(center)
        model.position.set(-center.x, -box.min.y, -center.z)

        // Wrap in a container so position/rotation offset is baked in
        const container = new THREE.Object3D()
        container.add(model)
        container.scale.setScalar(baseScale)

        const result: CharModel = { scene: container, baseScale }
        glbCache.set(key, result)
        resolve(result)
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

// Preload all character GLBs
const ALL_SHEET_KEYS = Object.keys(CHAR_SHEETS)
ALL_SHEET_KEYS.forEach(k => loadCharGLB(k))

// ── Sprite sheet texture cache (fallback) ────────────────────────────
const texCache = new Map<string, THREE.Texture>()

function getSheetTexture(sheetKey: string): THREE.Texture {
  if (texCache.has(sheetKey)) return texCache.get(sheetKey)!
  const img = getImage(CHAR_SHEETS[sheetKey])
  const tex = new THREE.Texture(img ?? document.createElement('canvas'))
  tex.colorSpace = THREE.SRGBColorSpace
  tex.needsUpdate = true
  texCache.set(sheetKey, tex)
  return tex
}

function updateUV(
  mat: THREE.SpriteMaterial,
  facing: Facing,
  frame: number,
  sheetKey: string,
): void {
  const tex = getSheetTexture(sheetKey)
  const img = getImage(CHAR_SHEETS[sheetKey])
  if (!img) return

  const col = FACING_COL[facing] ?? 0
  const row = frame % SHEET_ROWS
  const uw = 1 / SHEET_COLS
  const uh = 1 / SHEET_ROWS
  tex.offset.set(col * uw, 1 - (row + 1) * uh)
  tex.repeat.set(uw, uh)

  if (mat.map !== tex) {
    mat.map = tex
    mat.needsUpdate = true
  }
  tex.needsUpdate = false
}

// ── Per-entity entry ─────────────────────────────────────────────────
interface CharEntry {
  sheetKey: string
  mode: '3d' | 'sprite'
  // 3D mode
  model?: THREE.Object3D
  baseScale?: number
  walkPhase?: number
  prevX?: number
  prevZ?: number
  facingAngle?: number
  lastScale?: number
  // Sprite mode
  sprite?: THREE.Sprite
  material?: THREE.SpriteMaterial
}

// ── Public API ────────────────────────────────────────────────────────

export interface CharacterSprites3DHandle {
  group:   THREE.Group
  sync:    (
    entities: Record<string, GameEntity>,
    world:    WorldState | null,
    tileSize: number,
    selectedBotId: string | null,
    camera?:  THREE.Camera,
  ) => void
  dispose: () => void
}

export function createCharacterSprites3D(): CharacterSprites3DHandle {
  const group = new THREE.Group()
  const entries = new Map<string, CharEntry>()

  Object.values(CHAR_SHEETS).forEach(url => preloadImage(url))

  function getOrCreate(botId: string, occupation: string, paletteIndex: number): CharEntry {
    if (entries.has(botId)) return entries.get(botId)!

    const sheetKey = getCharSheetKey(occupation, paletteIndex)
    const charModel = glbCache.get(sheetKey)

    let entry: CharEntry

    if (charModel) {
      const model = charModel.scene.clone()
      group.add(model)
      entry = { sheetKey, mode: '3d', model, baseScale: charModel.baseScale }
    } else {
      const tex = getSheetTexture(sheetKey)
      const mat = new THREE.SpriteMaterial({
        map: tex,
        transparent: true,
        alphaTest: 0.1,
        depthWrite: false,
        sizeAttenuation: true,
      })
      const sprite = new THREE.Sprite(mat)
      const aspect = CHAR_CELL_W / CHAR_CELL_H
      sprite.scale.set(SPRITE_WORLD_H * aspect, SPRITE_WORLD_H, 1)
      sprite.position.y = SPRITE_WORLD_H / 2
      group.add(sprite)
      entry = { sheetKey, mode: 'sprite', sprite, material: mat }
    }

    entries.set(botId, entry)
    return entry
  }

  function disposeEntry(entry: CharEntry) {
    if (entry.model) {
      entry.model.traverse(child => {
        if (child instanceof THREE.Mesh) {
          child.geometry?.dispose()
          const mats = Array.isArray(child.material) ? child.material : [child.material]
          mats.forEach(m => m.dispose?.())
        }
      })
      group.remove(entry.model)
    }
    if (entry.sprite) {
      group.remove(entry.sprite)
      entry.material?.dispose()
    }
  }

  function removeStale(activeIds: Set<string>) {
    Array.from(entries.entries()).forEach(([id, entry]) => {
      if (!activeIds.has(id)) {
        disposeEntry(entry)
        entries.delete(id)
      }
    })
  }

  const _frustum = new THREE.Frustum()
  const _projMatrix = new THREE.Matrix4()
  const _testPoint = new THREE.Vector3()

  function sync(
    entities: Record<string, GameEntity>,
    world: WorldState | null,
    tileSize: number,
    selectedBotId: string | null,
    camera?: THREE.Camera,
  ) {
    const activeIds = new Set(Object.keys(entities))
    removeStale(activeIds)

    // Build frustum for culling (with margin)
    if (camera) {
      _projMatrix.multiplyMatrices(camera.projectionMatrix, camera.matrixWorldInverse)
      _frustum.setFromProjectionMatrix(_projMatrix)
    }

    let idx = 0
    for (const [botId, entity] of Object.entries(entities)) {
      const bot = world?.bots[botId]
      const occ = bot?.occupation ?? ''
      const entry = getOrCreate(botId, occ, idx++)

      const col = entity.pixelX / (tileSize || 1)
      const row = entity.pixelY / (tileSize || 1)
      const worldX = col * TILE_SIZE
      const worldZ = row * TILE_SIZE

      // Frustum culling — skip off-screen entities (unless selected)
      if (camera && botId !== selectedBotId) {
        _testPoint.set(worldX, CHAR_HEIGHT, worldZ)
        if (!_frustum.containsPoint(_testPoint)) {
          if (entry.model) entry.model.visible = false
          if (entry.sprite) entry.sprite.visible = false
          continue
        }
      }
      if (entry.model) entry.model.visible = true
      if (entry.sprite) entry.sprite.visible = true

      if (entry.mode === '3d' && entry.model) {
        // Compute movement delta to detect walking & derive facing angle
        const dx = (entry.prevX !== undefined) ? worldX - entry.prevX : 0
        const dz = (entry.prevZ !== undefined) ? worldZ - entry.prevZ : 0
        const isMoving = Math.abs(dx) > 0.001 || Math.abs(dz) > 0.001

        if (isMoving) {
          entry.facingAngle = Math.atan2(dx, dz)
        }
        entry.prevX = worldX
        entry.prevZ = worldZ

        // Walk animation: accumulate phase based on real frequency
        const dt = 1 / 60
        if (isMoving) {
          entry.walkPhase = ((entry.walkPhase ?? 0) + dt * WALK_FREQ * Math.PI * 2) % (Math.PI * 2)
        } else {
          const p = entry.walkPhase ?? 0
          if (Math.abs(p) > 0.01) {
            entry.walkPhase = p * 0.88
          } else {
            entry.walkPhase = 0
          }
        }
        const phase = entry.walkPhase ?? 0
        const swing = Math.sin(phase)

        entry.model.position.set(worldX, WALK_BOB * Math.abs(swing), worldZ)

        entry.model.rotation.y = entry.facingAngle ?? 0
        entry.model.rotation.x = swing * WALK_LEAN

        const s = (entry.baseScale ?? 1) * (botId === selectedBotId ? 1.3 : 1.0)
        if (entry.lastScale !== s) {
          entry.model.scale.setScalar(s)
          entry.lastScale = s
        }
      } else if (entry.sprite && entry.material) {
        entry.sprite.position.x = worldX
        entry.sprite.position.z = worldZ
        entry.sprite.position.y = SPRITE_WORLD_H / 2

        updateUV(entry.material, entity.facing, entity.animFrame, entry.sheetKey)

        const scale = botId === selectedBotId ? 1.4 : 1.0
        const aspect = CHAR_CELL_W / CHAR_CELL_H
        entry.sprite.scale.set(
          SPRITE_WORLD_H * aspect * scale,
          SPRITE_WORLD_H * scale,
          1,
        )
      }
    }
  }

  function dispose() {
    entries.forEach(entry => disposeEntry(entry))
    entries.clear()
  }

  return { group, sync, dispose }
}

// ── Emotion bubble CSS2D labels ────────────────────────────────────────

export interface BubbleLabel {
  id:     string
  obj:    CSS2DObject
  timer:  number
  alpha:  number
}

export function createBubbleLabel(emoji: string): CSS2DObject {
  const div = document.createElement('div')
  div.style.cssText = `
    font-size: 18px;
    line-height: 1;
    pointer-events: none;
    user-select: none;
    text-shadow: 0 1px 3px rgba(0,0,0,0.8);
    animation: bubble-pop 0.3s ease-out;
  `
  div.textContent = emoji
  return new CSS2DObject(div)
}

export function tickBubbleLabels(
  bubbles: BubbleLabel[],
  entities: Record<string, GameEntity>,
  tileSize: number,
  dt: number,
  scene: THREE.Scene,
): BubbleLabel[] {
  return bubbles.filter(b => {
    b.timer -= dt
    b.alpha  = Math.min(1, b.timer / 1.5)

    const entity = entities[b.id]
    if (entity) {
      const col = entity.pixelX / (tileSize || 1)
      const row = entity.pixelY / (tileSize || 1)
      b.obj.position.set(col * TILE_SIZE, SPRITE_WORLD_H * 1.5, row * TILE_SIZE)
      ;(b.obj.element as HTMLElement).style.opacity = String(b.alpha)
    }

    if (b.timer <= 0) {
      scene.remove(b.obj)
      b.obj.element.remove()
      return false
    }
    return true
  })
}
