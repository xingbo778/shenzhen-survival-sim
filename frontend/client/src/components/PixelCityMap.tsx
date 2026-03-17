/**
 * PixelCityMap — tile-based game canvas with A* pathfinding.
 *
 * Rendering layers (bottom → top):
 *  1. Tile map            renderTileMap
 *  2. Scene objects       renderSceneObjects
 *  3. Vehicles / boats    vehicleSystem
 *  4. Bot characters      charSprites
 *  5. Emotion bubbles     charSprites
 *  6. UI overlay          pan indicator, vignette
 */

import { useRef, useEffect, useCallback, useState } from 'react'
import type { WorldState } from '@/types/world'
import { getDominantEmotion } from '@/types/world'
import { SCENE_META, SCENE_NAMES, MAP_SCALE, ZOOM_MIN, ZOOM_MAX, ZOOM_STEP } from '@/config/scenes'
import { SCENE_CONFIGS } from '@/engine/sceneTiles'
import { renderTileMap, renderSceneObjects, TILE_SHEET_URL } from '@/engine/tileRenderer'
import type { ObjectManifest } from '@/engine/tileRenderer'
import { buildNavMesh, randomWalkableTile } from '@/engine/pathfinder'
import { createEntity, tickEntity, assignActivityPath } from '@/engine/gameEntity'
import type { GameEntity } from '@/engine/gameEntity'
import {
  preloadAllCharSheets, collectBotDrawables, tickAndCollectBubbleDrawables,
  CHAR_CELL_W, CHAR_CELL_H, CHAR_SCALE, CHAR_OFFSET_Y,
} from '@/engine/charSprites'
import type { EmotionBubble } from '@/engine/charSprites'
import {
  preloadVehicleSheets, initVehicles,
  tickAndCollectVehicleDrawables, getVehiclePositions,
} from '@/engine/vehicleSystem'
import type { VehicleState } from '@/engine/vehicleSystem'
import { preloadImage, getImage } from '@/engine/imageCache'
import { useGameLoop } from '@/hooks/useGameLoop'
import { useCanvasResize } from '@/hooks/useCanvasResize'
import type { ZDrawable } from '@/engine/types'

const OBJECTS_SHEET_URL    = '/sprites/objects/objects_sheet.png'
const OBJECTS_MANIFEST_URL = '/sprites/objects/objects_manifest.json'

interface Props {
  world: WorldState | null
  selectedBotId: string | null
  onBotClick: (botId: string) => void
  onLocationClick: (location: string) => void
  currentLocation?: string
}

type NavMeshCache = { loc: string; ped: boolean[][]; boat: boolean[][] } | null

// CHAR_CELL_W, CHAR_CELL_H, CHAR_SCALE, CHAR_OFFSET_Y imported from charSprites

export default function PixelCityMap({
  world, selectedBotId, onBotClick, onLocationClick, currentLocation,
}: Props) {
  const canvasRef       = useRef<HTMLCanvasElement>(null)
  const entitiesRef     = useRef<Record<string, GameEntity>>({})
  const vehiclesRef     = useRef<VehicleState[]>([])
  const bubblesRef      = useRef<EmotionBubble[]>([])
  const navMeshRef      = useRef<NavMeshCache>(null)
  const objManifestRef  = useRef<ObjectManifest | null>(null)

  // Zoom & pan
  const zoomRef       = useRef(1.0)
  const panOffsetRef  = useRef({ x: 0, y: 0 })

  // Drag state
  const isDraggingRef = useRef(false)
  const dragStartRef  = useRef({ x: 0, y: 0, panX: 0, panY: 0 })
  const didDragRef    = useRef(false)
  const touchStartRef = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null)

  const [hoveredBotId, setHoveredBotId] = useState<string | null>(null)

  const activeLocation = currentLocation || SCENE_NAMES[0]
  const meta           = SCENE_META[activeLocation] || SCENE_META['南山科技园']
  const sceneConfig    = SCENE_CONFIGS[activeLocation]

  // ── Nav mesh (recomputed only when location changes) ──────────
  if (!navMeshRef.current || navMeshRef.current.loc !== activeLocation) {
    if (sceneConfig) {
      navMeshRef.current = {
        loc: activeLocation,
        ped:  buildNavMesh(sceneConfig.tilemap, 'pedestrian'),
        boat: buildNavMesh(sceneConfig.tilemap, 'boat'),
      }
    }
  }

  // ── One-time asset preload ────────────────────────────────────
  useEffect(() => {
    preloadAllCharSheets()
    preloadVehicleSheets()
    preloadImage(TILE_SHEET_URL)
    preloadImage(OBJECTS_SHEET_URL)
    // Fetch the objects manifest JSON (tiny, cached after first load)
    fetch(OBJECTS_MANIFEST_URL)
      .then(r => r.ok ? r.json() : null)
      .then((data: ObjectManifest | null) => { if (data) objManifestRef.current = data })
      .catch(() => {/* manifest not generated yet — silently fall back to SpriteData */})
  }, [])

  // ── Reset vehicles + pan on location change ───────────────────
  useEffect(() => {
    const botCount = world
      ? Object.keys(world.bots).filter(id => world.bots[id].status === 'alive').length
      : 10
    vehiclesRef.current    = initVehicles(activeLocation, botCount)
    panOffsetRef.current   = { x: 0, y: 0 }
  }, [activeLocation])  // eslint-disable-line react-hooks/exhaustive-deps

  // ── Sync world bots → game entities ──────────────────────────
  useEffect(() => {
    if (!world || !sceneConfig || !navMeshRef.current) return

    const tilemap  = sceneConfig.tilemap
    const navMesh  = navMeshRef.current.ped
    const rows     = tilemap.length
    const cols     = tilemap[0]?.length ?? 36
    const canvas   = canvasRef.current
    const cssW     = canvas ? canvas.width / (window.devicePixelRatio || 1) : 900
    const tileSize = (cssW * MAP_SCALE * zoomRef.current) / cols

    const aliveBotIds = Object.keys(world.bots).filter(id => world.bots[id].status === 'alive')

    aliveBotIds.forEach(botId => {
      const bot = world.bots[botId]
      if (!bot) return

      if (!entitiesRef.current[botId]) {
        const spawn  = randomWalkableTile(navMesh, Math.floor(rows * 0.6))
        const entity = createEntity(botId, spawn[0], spawn[1], tileSize)
        assignActivityPath(entity, bot.current_activity || bot.occupation || '', tilemap, navMesh)
        entitiesRef.current[botId] = entity
      } else {
        const entity   = entitiesRef.current[botId]
        const activity = bot.current_activity || bot.occupation || ''
        if (entity.activity !== activity || entity.pathIdx >= entity.path.length) {
          assignActivityPath(entity, activity, tilemap, navMesh)
        }
      }

      // Random emotion bubbles
      if (Math.random() < 0.006) {
        const emotion = getDominantEmotion(bot.emotions)
        const entity  = entitiesRef.current[botId]
        if (entity) {
          bubblesRef.current.push({
            botId, emoji: emotion.emoji,
            x: entity.pixelX, y: entity.pixelY,
            alpha: 1, timer: 2.5,
          })
        }
      }
    })

    // Remove entities for dead / removed bots
    Object.keys(entitiesRef.current).forEach(id => {
      if (!aliveBotIds.includes(id)) delete entitiesRef.current[id]
    })
  }, [world, activeLocation, sceneConfig])

  // ── Hit testing ───────────────────────────────────────────────
  const getCanvasPos = useCallback((clientX: number, clientY: number) => {
    const canvas = canvasRef.current
    if (!canvas) return { mx: 0, my: 0 }
    const rect = canvas.getBoundingClientRect()
    const dpr  = window.devicePixelRatio || 1
    return {
      mx: (clientX - rect.left) * (canvas.width  / rect.width)  / dpr,
      my: (clientY - rect.top)  * (canvas.height / rect.height) / dpr,
    }
  }, [])

  const getBotAtPoint = useCallback((mx: number, my: number): string | null => {
    const canvas = canvasRef.current
    if (!canvas || !sceneConfig) return null

    const dpr    = window.devicePixelRatio || 1
    const cssW   = canvas.width  / dpr
    const cssH   = canvas.height / dpr
    const cols   = sceneConfig.tilemap[0]?.length ?? 36
    const rows   = sceneConfig.tilemap.length
    const zoom   = zoomRef.current
    const worldW = cssW * MAP_SCALE * zoom
    const worldH = rows * (worldW / cols)
    const panX   = panOffsetRef.current.x
    const panY   = panOffsetRef.current.y
    const worldX = (cssW - worldW) / 2 + panX
    const worldY = (cssH - worldH) / 2 + panY

    const hitRW = Math.round(CHAR_CELL_W * CHAR_SCALE)
    const hitRH = Math.round(CHAR_CELL_H * CHAR_SCALE)

    for (const [botId, entity] of Object.entries(entitiesRef.current)) {
      const cx = worldX + entity.pixelX
      const cy = worldY + entity.pixelY
      const bx = cx - hitRW / 2
      const by = cy - hitRH * CHAR_OFFSET_Y
      if (mx >= bx && mx <= bx + hitRW && my >= by && my <= by + hitRH) return botId
    }
    return null
  }, [sceneConfig])

  // ── Input handlers ────────────────────────────────────────────
  const handleMouseDown = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    isDraggingRef.current = true
    didDragRef.current    = false
    dragStartRef.current  = {
      x: e.clientX, y: e.clientY,
      panX: panOffsetRef.current.x, panY: panOffsetRef.current.y,
    }
  }, [])

  const handleMouseUp = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    isDraggingRef.current = false
    if (!didDragRef.current) {
      const { mx, my } = getCanvasPos(e.clientX, e.clientY)
      const botId = getBotAtPoint(mx, my)
      if (botId) onBotClick(botId)
    }
    didDragRef.current = false
  }, [getBotAtPoint, onBotClick, getCanvasPos])

  const handleMouseMove = useCallback((e: React.MouseEvent<HTMLCanvasElement>) => {
    if (isDraggingRef.current) {
      const dx = e.clientX - dragStartRef.current.x
      const dy = e.clientY - dragStartRef.current.y
      if (Math.abs(dx) > 3 || Math.abs(dy) > 3) didDragRef.current = true
      panOffsetRef.current = { x: dragStartRef.current.panX + dx, y: dragStartRef.current.panY + dy }
      return
    }
    const { mx, my } = getCanvasPos(e.clientX, e.clientY)
    setHoveredBotId(getBotAtPoint(mx, my))
  }, [getBotAtPoint, getCanvasPos])

  const handleTouchStart = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    if (e.touches.length === 1) {
      touchStartRef.current = {
        x: e.touches[0].clientX, y: e.touches[0].clientY,
        panX: panOffsetRef.current.x, panY: panOffsetRef.current.y,
      }
    }
  }, [])

  const handleTouchMove = useCallback((e: React.TouchEvent<HTMLCanvasElement>) => {
    if (e.touches.length === 1 && touchStartRef.current) {
      e.preventDefault()
      const dx = e.touches[0].clientX - touchStartRef.current.x
      const dy = e.touches[0].clientY - touchStartRef.current.y
      panOffsetRef.current = { x: touchStartRef.current.panX + dx, y: touchStartRef.current.panY + dy }
    }
  }, [])

  // Wheel zoom (non-passive so we can preventDefault)
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const onWheel = (e: WheelEvent) => {
      e.preventDefault()
      const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
      zoomRef.current = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoomRef.current + delta))
    }
    canvas.addEventListener('wheel', onWheel, { passive: false })
    return () => canvas.removeEventListener('wheel', onWheel)
  }, [])

  useCanvasResize(canvasRef)

  // ── Render loop ───────────────────────────────────────────────
  useGameLoop((dt, tick, pulse) => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr  = window.devicePixelRatio || 1
    const cssW = canvas.width  / dpr
    const cssH = canvas.height / dpr

    ctx.clearRect(0, 0, canvas.width, canvas.height)
    ctx.save()
    ctx.scale(dpr, dpr)

    ctx.fillStyle = '#0d1117'
    ctx.fillRect(0, 0, cssW, cssH)

    if (!sceneConfig) {
      ctx.fillStyle = 'rgba(255,255,255,0.3)'
      ctx.font = 'bold 24px monospace'
      ctx.textAlign = 'center'
      ctx.fillText('场景未找到', cssW / 2, cssH / 2)
      ctx.restore()
      return
    }

    const tilemap = sceneConfig.tilemap
    const mapCols = tilemap[0]?.length ?? 36
    const mapRows = tilemap.length

    const zoom   = zoomRef.current
    const worldW = cssW * MAP_SCALE * zoom
    const tileSize = worldW / mapCols
    const worldH = mapRows * tileSize

    // Clamp pan
    const maxPanX = (worldW - cssW) / 2
    const maxPanY = Math.max(0, (worldH - cssH) / 2)
    const panX = Math.max(-maxPanX, Math.min(maxPanX, panOffsetRef.current.x))
    const panY = Math.max(-maxPanY, Math.min(maxPanY, panOffsetRef.current.y))
    panOffsetRef.current = { x: panX, y: panY }

    const worldX = (cssW - worldW) / 2 + panX
    const worldY = (cssH - worldH) / 2 + panY

    // Layer 1 + 2: tiles and scene objects
    const tileSheet = getImage(TILE_SHEET_URL)
    const objSheet  = getImage(OBJECTS_SHEET_URL)
    ctx.save()
    ctx.translate(worldX, worldY)
    renderTileMap(ctx, tilemap, tileSize, tick, tileSheet)
    renderSceneObjects(ctx, sceneConfig.objects, tileSize, objSheet, objManifestRef.current)
    ctx.restore()

    const drawables: ZDrawable[] = []

    // Layer 3: vehicles
    tickAndCollectVehicleDrawables(vehiclesRef.current, dt, worldX, worldY, worldW, worldH, cssW, cssH, drawables)

    // Layer 4: bot characters
    const vehiclePositions = getVehiclePositions(vehiclesRef.current, worldW, worldH)
    const navMesh          = navMeshRef.current?.ped

    Object.entries(entitiesRef.current).forEach(([botId, entity], i) => {
      tickEntity(entity, dt, tileSize)

      // Vehicle collision avoidance
      for (const vp of vehiclePositions) {
        if (vp.radius <= 0) continue
        const edx  = entity.pixelX - vp.x
        const edy  = entity.pixelY - vp.y
        const dist = Math.sqrt(edx * edx + edy * edy)
        const minD = vp.radius + tileSize * 0.6
        if (dist < minD && dist > 0.1) {
          const push = (minD - dist) * 0.3
          entity.pixelX += (edx / dist) * push
          entity.pixelY += (edy / dist) * push
        }
      }

      // Entity–entity repulsion
      for (const [otherId, other] of Object.entries(entitiesRef.current)) {
        if (otherId === botId) continue
        const edx  = entity.pixelX - other.pixelX
        const edy  = entity.pixelY - other.pixelY
        const dist = Math.sqrt(edx * edx + edy * edy)
        const minD = tileSize * 0.7
        if (dist < minD && dist > 0.1) {
          const push = (minD - dist) * 0.15
          entity.pixelX += (edx / dist) * push
          entity.pixelY += (edy / dist) * push
        }
      }

      // Re-plan exhausted paths
      if (entity.pathIdx >= entity.path.length && navMesh && sceneConfig) {
        const bot      = world?.bots[botId]
        const activity = bot?.current_activity || bot?.occupation || ''
        assignActivityPath(entity, activity, sceneConfig.tilemap, navMesh)
      }

      collectBotDrawables(
        botId, entity, world, i % 10,
        worldX, worldY,
        selectedBotId, hoveredBotId, pulse,
        cssW, cssH, drawables,
      )
    })

    // Layer 5: emotion bubbles
    bubblesRef.current = tickAndCollectBubbleDrawables(
      bubblesRef.current, entitiesRef.current, dt, worldX, worldY, drawables,
    )

    // Z-sort and draw all
    drawables.sort((a, b) => a.zY - b.zY)
    drawables.forEach(d => d.draw(ctx))

    // Pan arrows
    if (Math.abs(panX) > 10 || Math.abs(panY) > 10) {
      ctx.save()
      ctx.globalAlpha = 0.5
      const margin = 20
      ctx.fillStyle = meta.ambientColor
      ctx.font = '16px sans-serif'
      ctx.textAlign = 'center'
      if (panX < -10) ctx.fillText('◀', margin,       cssH / 2)
      if (panX > 10)  ctx.fillText('▶', cssW - margin, cssH / 2)
      if (panY < -10) ctx.fillText('▲', cssW / 2,      margin + 8)
      if (panY > 10)  ctx.fillText('▼', cssW / 2,      cssH - margin)
      ctx.restore()
    }

    // Vignette
    const vignette = ctx.createRadialGradient(cssW / 2, cssH / 2, cssH * 0.3, cssW / 2, cssH / 2, cssH * 0.8)
    vignette.addColorStop(0, 'transparent')
    vignette.addColorStop(1, 'rgba(0,0,0,0.2)')
    ctx.fillStyle = vignette
    ctx.fillRect(0, 0, cssW, cssH)

    ctx.restore()
  })

  // ── Render ────────────────────────────────────────────────────
  return (
    <div className="relative w-full h-full">
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{
          cursor: isDraggingRef.current ? 'grabbing' : hoveredBotId ? 'pointer' : 'grab',
          imageRendering: 'pixelated',
          userSelect: 'none',
          touchAction: 'none',
        }}
        onMouseDown={handleMouseDown}
        onMouseUp={handleMouseUp}
        onClick={() => {}}
        onMouseMove={handleMouseMove}
        onMouseLeave={() => { setHoveredBotId(null); isDraggingRef.current = false }}
        onTouchStart={handleTouchStart}
        onTouchMove={handleTouchMove}
        onTouchEnd={() => { touchStartRef.current = null }}
      />

      {/* Location selector */}
      <div
        className="absolute bottom-3 left-0 right-0 flex gap-1 justify-center overflow-x-auto px-2 pb-0.5"
        style={{ scrollbarWidth: 'none' }}
      >
        {SCENE_NAMES.map(loc => (
          <button
            key={loc}
            onClick={() => onLocationClick(loc)}
            className={`px-2 py-0.5 text-xs font-mono border transition-all ${
              loc === activeLocation
                ? 'border-opacity-80 text-white'
                : 'bg-black/50 border-white/15 text-white/50 hover:border-white/40 hover:text-white/80'
            }`}
            style={loc === activeLocation ? {
              background:   meta.ambientColor + '33',
              borderColor:  meta.ambientColor + 'AA',
              color:        meta.ambientColor,
            } : {}}
          >
            {loc}
          </button>
        ))}
      </div>

      <div className="absolute top-3 right-3 text-xs font-mono text-white/30 bg-black/30 px-2 py-0.5 rounded pointer-events-none">
        拖拽平移 · 滚轮缩放
      </div>
    </div>
  )
}
