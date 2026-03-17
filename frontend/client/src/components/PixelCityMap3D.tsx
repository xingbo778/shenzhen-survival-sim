/**
 * PixelCityMap3D — Three.js-powered city map.
 *
 * Rendering layers:
 *  1. TileGrid3D    — flat ground plane (PlaneGeometry per tile type, instanced)
 *  2. Buildings3D   — textured BoxGeometry buildings (AI-generated facade/roof textures)
 *  3. CharacterSprites3D — THREE.Sprite billboards (always face camera)
 *  4. CSS2DRenderer — emotion bubble DOM labels
 *
 * All existing game logic (pathfinding, A*, vehicles, activity mapping) is
 * reused unchanged from the 2D engine.
 */

import { useRef, useEffect, useCallback, useState } from 'react'
import type { WorldState } from '@/types/world'
import { getDominantEmotion } from '@/types/world'
import { SCENE_META, SCENE_NAMES, ZOOM_MIN, ZOOM_MAX, ZOOM_STEP } from '@/config/scenes'
import { SCENE_CONFIGS } from '@/engine/sceneTiles'
import { buildNavMesh, randomWalkableTile, findPath } from '@/engine/pathfinder'
import { createEntity, tickEntity, assignActivityPath } from '@/engine/gameEntity'
import type { GameEntity } from '@/engine/gameEntity'
import {
  preloadAllCharSheets,
} from '@/engine/charSprites'
import {
  preloadVehicleSheets, initVehicles,
} from '@/engine/vehicleSystem'
import type { VehicleState } from '@/engine/vehicleSystem'
import { useGameLoop } from '@/hooks/useGameLoop'

import { createThreeScene, setCameraTarget } from '@/engine/three/ThreeScene'
import type { ThreeSceneHandle }   from '@/engine/three/ThreeScene'
import { buildTileGrid3D }         from '@/engine/three/TileGrid3D'
import type { TileGrid3DHandle }   from '@/engine/three/TileGrid3D'
import { buildBuildings3D, preloadBuildings } from '@/engine/three/Buildings3D'
import type { Buildings3DHandle }  from '@/engine/three/Buildings3D'
import { buildStreetFurniture3D, clearFurnitureCache }  from '@/engine/three/StreetFurniture3D'
import type { StreetFurniture3DHandle } from '@/engine/three/StreetFurniture3D'
import {
  createCharacterSprites3D,
  createBubbleLabel,
  tickBubbleLabels,
} from '@/engine/three/CharacterSprites3D'
import type { CharacterSprites3DHandle, BubbleLabel } from '@/engine/three/CharacterSprites3D'
import { buildVehicles3D, clearVehicleCache } from '@/engine/three/Vehicles3D'
import type { Vehicles3DHandle } from '@/engine/three/Vehicles3D'
import { TILE_SIZE } from '@/engine/three/ThreeScene'
import CityPlanView from './CityPlanView'
import { Button } from '@/components/ui/button'

// ── Constants ──────────────────────────────────────────────────────────
// Approximate game-loop tile size in CSS pixels (used for entity <-> world mapping)
const VIRTUAL_TILE_PX = 32

interface Props {
  world: WorldState | null
  selectedBotId: string | null
  onBotClick: (botId: string) => void
  onLocationClick: (location: string) => void
  currentLocation?: string
}

type NavMeshCache = { loc: string; ped: boolean[][]; boat: boolean[][] } | null

export default function PixelCityMap3D({
  world, selectedBotId, onBotClick, onLocationClick, currentLocation,
}: Props) {
  const containerRef  = useRef<HTMLDivElement>(null)
  const canvasRef     = useRef<HTMLCanvasElement>(null)

  // Three.js handles
  const threeRef      = useRef<ThreeSceneHandle | null>(null)
  const tileGridRef   = useRef<TileGrid3DHandle | null>(null)
  const buildingsRef  = useRef<Buildings3DHandle | null>(null)
  const furnitureRef  = useRef<StreetFurniture3DHandle | null>(null)
  const charRef       = useRef<CharacterSprites3DHandle | null>(null)
  const vehicles3DRef = useRef<Vehicles3DHandle | null>(null)
  const bubblesRef    = useRef<BubbleLabel[]>([])

  // Game logic refs (reused from PixelCityMap)
  const entitiesRef   = useRef<Record<string, GameEntity>>({})
  const vehiclesRef   = useRef<VehicleState[]>([])
  const navMeshRef    = useRef<NavMeshCache>(null)

  // Camera pan / zoom
  const zoomRef       = useRef(1.0)
  const panColRef     = useRef(0)
  const panRowRef     = useRef(0)
  const isDraggingRef = useRef(false)
  const dragStartRef  = useRef({ x: 0, y: 0, panX: 0, panY: 0 })

  const [viewMode, setViewMode] = useState<'3d' | 'plan'>('3d')

  const activeLocation = currentLocation || SCENE_NAMES[0]
  const meta           = SCENE_META[activeLocation] || SCENE_META['南山科技园']
  const sceneConfig    = SCENE_CONFIGS[activeLocation]

  // ── Nav mesh ──────────────────────────────────────────────────────
  if (!navMeshRef.current || navMeshRef.current.loc !== activeLocation) {
    if (sceneConfig) {
      navMeshRef.current = {
        loc:  activeLocation,
        ped:  buildNavMesh(sceneConfig.tilemap, 'pedestrian'),
        boat: buildNavMesh(sceneConfig.tilemap, 'boat'),
      }
    }
  }

  // ── Three.js scene init ────────────────────────────────────────────
  useEffect(() => {
    const canvas    = canvasRef.current
    const container = containerRef.current
    if (!canvas || !container) return

    const three = createThreeScene(canvas, container)
    threeRef.current = three

    const w = container.clientWidth
    const h = container.clientHeight
    three.resize(w, h)

    return () => {
      three.dispose()
      threeRef.current = null
    }
  }, [])

  // ── Rebuild tile grid + buildings on location change ───────────────
  useEffect(() => {
    if (!threeRef.current || !sceneConfig) return
    const { scene } = threeRef.current

    // Remove old grid / buildings
    if (tileGridRef.current) {
      scene.remove(tileGridRef.current.group)
      tileGridRef.current.dispose()
      tileGridRef.current = null
    }
    if (buildingsRef.current) {
      scene.remove(buildingsRef.current.group)
      buildingsRef.current.dispose()
      buildingsRef.current = null
    }
    if (furnitureRef.current) {
      scene.remove(furnitureRef.current.group)
      furnitureRef.current.dispose()
      furnitureRef.current = null
      clearFurnitureCache()
    }
    if (vehicles3DRef.current) {
      scene.remove(vehicles3DRef.current.group)
      vehicles3DRef.current.dispose()
      vehicles3DRef.current = null
      clearVehicleCache()
    }

    // Create sprites handle if needed
    if (!charRef.current) {
      charRef.current = createCharacterSprites3D()
      scene.add(charRef.current.group)
    }

    // Tile grid
    const tileGrid = buildTileGrid3D(sceneConfig.tilemap)
    scene.add(tileGrid.group)
    tileGridRef.current = tileGrid

    // Buildings (async)
    const allKeys = sceneConfig.objects.map(o => o.pngKey).filter((k): k is string => !!k)
    const keys = Array.from(new Set(allKeys))
    preloadBuildings(keys)

    buildBuildings3D(sceneConfig.objects).then(bldgs => {
      if (!threeRef.current) return
      threeRef.current.scene.add(bldgs.group)
      buildingsRef.current = bldgs
    })

    // Street furniture (trees, traffic lights, signs, etc.)
    buildStreetFurniture3D(sceneConfig.objects).then(furn => {
      if (!threeRef.current) return
      threeRef.current.scene.add(furn.group)
      furnitureRef.current = furn
    })

    // 3D vehicles on roads (async — loads GLB models)
    buildVehicles3D(sceneConfig.tilemap, 120).then(v3d => {
      if (!threeRef.current) return
      threeRef.current.scene.add(v3d.group)
      vehicles3DRef.current = v3d
    })

    // Reset camera to map centre
    const cols = sceneConfig.cols
    const rows = sceneConfig.rows
    panColRef.current = cols / 2
    panRowRef.current = rows / 2
    zoomRef.current   = 1.0

    // Reset entities for new location
    entitiesRef.current = {}
    demoSpawnedRef.current = false

    // Vehicles
    const botCount = world
      ? Object.keys(world.bots).filter(id => world.bots[id].status === 'alive').length
      : 10
    vehiclesRef.current = initVehicles(activeLocation, botCount)

  }, [activeLocation])   // eslint-disable-line react-hooks/exhaustive-deps

  // ── Entity sync (real bots + demo fallback) ─────────────────────────
  const demoSpawnedRef = useRef(false)

  useEffect(() => {
    if (!sceneConfig || !navMeshRef.current) return
    const tilemap = sceneConfig.tilemap
    const navMesh = navMeshRef.current.ped
    const rows    = tilemap.length

    // Real bots from world engine
    if (world) {
      const aliveBotIds = Object.keys(world.bots).filter(id => world.bots[id].status === 'alive')

      aliveBotIds.forEach(botId => {
        const bot = world.bots[botId]
        if (!bot) return

        if (!entitiesRef.current[botId]) {
          const spawn  = randomWalkableTile(navMesh, Math.floor(rows * 0.5))
          const entity = createEntity(botId, spawn[0], spawn[1], VIRTUAL_TILE_PX)
          assignActivityPath(entity, bot.current_activity || bot.occupation || '', tilemap, navMesh)
          entitiesRef.current[botId] = entity
        } else {
          const entity   = entitiesRef.current[botId]
          const activity = bot.current_activity || bot.occupation || ''
          if (entity.activity !== activity || entity.pathIdx >= entity.path.length) {
            assignActivityPath(entity, activity, tilemap, navMesh)
          }
        }

        if (Math.random() < 0.006) {
          const emotion = getDominantEmotion(bot.emotions)
          const entity  = entitiesRef.current[botId]
          if (entity && threeRef.current) {
            const label  = createBubbleLabel(emotion.emoji)
            threeRef.current.scene.add(label)
            bubblesRef.current.push({ id: botId, obj: label, timer: 2.5, alpha: 1 })
          }
        }
      })

      Object.keys(entitiesRef.current).forEach(id => {
        if (!aliveBotIds.includes(id)) delete entitiesRef.current[id]
      })
    }

    // Demo fallback: spawn wandering NPCs when no world data
    if (!world && !demoSpawnedRef.current) {
      demoSpawnedRef.current = true
      const DEMO_COUNT = 30
      const occupations = ['walk_around', '散步', '逛街', 'work', 'rest', 'exercise']
      for (let i = 0; i < DEMO_COUNT; i++) {
        const demoId = `demo_${i}`
        // Spread across the map
        const targetRow = Math.floor(rows * (0.1 + (i / DEMO_COUNT) * 0.8))
        const spawn = randomWalkableTile(navMesh, targetRow, 15)
        const entity = createEntity(demoId, spawn[0], spawn[1], VIRTUAL_TILE_PX)
        entity.activity = occupations[i % occupations.length]
        // Use nearby destination (rowRange=20) to keep A* fast
        const dest = randomWalkableTile(navMesh, spawn[1], 20)
        const path = findPath(navMesh, [spawn[0], spawn[1]], dest)
        if (path.length > 1) {
          entity.path = path
          entity.pathIdx = 1
        }
        entitiesRef.current[demoId] = entity
      }
    }
  }, [world, activeLocation, sceneConfig])

  // ── Resize handler ────────────────────────────────────────────────
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const obs = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      threeRef.current?.resize(width, height)
    })
    obs.observe(container)
    return () => obs.disconnect()
  }, [])

  // ── Mouse interactions ────────────────────────────────────────────
  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    isDraggingRef.current = true
    dragStartRef.current  = {
      x: e.clientX, y: e.clientY,
      panX: panColRef.current, panY: panRowRef.current,
    }
  }, [])

  const handleMouseMove = useCallback((e: React.MouseEvent) => {
    if (!isDraggingRef.current) return
    const cols = sceneConfig?.cols ?? 36
    const rows = sceneConfig?.rows ?? 24
    const dx = (e.clientX - dragStartRef.current.x) / (containerRef.current?.clientWidth ?? 800)
    const dy = (e.clientY - dragStartRef.current.y) / (containerRef.current?.clientHeight ?? 600)
    panColRef.current = dragStartRef.current.panX - dx * cols * 0.8
    panRowRef.current = dragStartRef.current.panY - dy * rows * 0.8
  }, [sceneConfig])

  const handleMouseUp = useCallback(() => {
    isDraggingRef.current = false
  }, [])

  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    const delta = e.deltaY > 0 ? -ZOOM_STEP : ZOOM_STEP
    zoomRef.current = Math.max(ZOOM_MIN, Math.min(ZOOM_MAX, zoomRef.current + delta))
  }, [])

  // ── Game + render loop ────────────────────────────────────────────
  useGameLoop((dt) => {
    const three      = threeRef.current
    const sc         = sceneConfig
    const navMesh    = navMeshRef.current?.ped
    if (!three || !sc) return

    // Tick entities — throttle A* to max 2 per frame to avoid hitching
    let pathsThisFrame = 0
    Object.entries(entitiesRef.current).forEach(([botId, entity]) => {
      tickEntity(entity, dt, VIRTUAL_TILE_PX)

      if (entity.pathIdx >= entity.path.length && navMesh && pathsThisFrame < 2) {
        pathsThisFrame++
        if (botId.startsWith('demo_')) {
          const dest = randomWalkableTile(navMesh, entity.row, 25)
          const path = findPath(navMesh, [entity.col, entity.row], dest)
          if (path.length > 1) {
            entity.path = path
            entity.pathIdx = 1
          }
        } else {
          const bot      = world?.bots[botId]
          const activity = bot?.current_activity || bot?.occupation || ''
          assignActivityPath(entity, activity, sc.tilemap, navMesh)
        }
      }
    })

    // Tick 3D vehicles + building LOD
    vehicles3DRef.current?.tick(dt)
    buildingsRef.current?.updateLOD(three.camera)

    // Bubble labels
    bubblesRef.current = tickBubbleLabels(
      bubblesRef.current,
      entitiesRef.current,
      VIRTUAL_TILE_PX,
      dt,
      three.scene,
    )

    // Sync character sprites
    charRef.current?.sync(entitiesRef.current, world, VIRTUAL_TILE_PX, selectedBotId, three.camera)

    // Update camera
    const cols = sc.cols
    const rows = sc.rows
    const col  = Math.max(0, Math.min(cols - 1, panColRef.current))
    const row  = Math.max(0, Math.min(rows - 1, panRowRef.current))
    setCameraTarget(three.camera, col, row, zoomRef.current)

    three.render()
  })

  // ── Preload assets ─────────────────────────────────────────────────
  useEffect(() => {
    preloadAllCharSheets()
    preloadVehicleSheets()
  }, [])

  return (
    <div
      ref={containerRef}
      className="relative w-full h-full"
      style={{ background: '#0d1117' }}
    >
      {viewMode === 'plan' && sceneConfig ? (
        <CityPlanView sceneConfig={sceneConfig} />
      ) : (
        <canvas
          ref={canvasRef}
          className="w-full h-full"
          style={{
            cursor: isDraggingRef.current ? 'grabbing' : 'grab',
            display: 'block',
          }}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
          onWheel={handleWheel}
        />
      )}

      {/* View mode toggle */}
      <div className="absolute top-3 left-3 flex gap-1">
        <Button
          onClick={() => setViewMode('3d')}
          variant={viewMode === '3d' ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2.5 text-xs font-mono backdrop-blur-sm"
        >
          3D
        </Button>
        <Button
          onClick={() => setViewMode('plan')}
          variant={viewMode === 'plan' ? 'secondary' : 'ghost'}
          size="sm"
          className="h-7 px-2.5 text-xs font-mono backdrop-blur-sm"
        >
          俯视图
        </Button>
      </div>

      {/* Location selector */}
      <div
        className="absolute bottom-3 left-0 right-0 flex gap-1.5 justify-center overflow-x-auto px-2 pb-0.5"
        style={{ scrollbarWidth: 'none' }}
      >
        {SCENE_NAMES.map(loc => (
          <Button
            key={loc}
            onClick={() => onLocationClick(loc)}
            variant={loc === activeLocation ? 'secondary' : 'ghost'}
            size="sm"
            className="h-7 px-2.5 text-xs font-mono backdrop-blur-sm"
            style={loc === activeLocation ? {
              background:  meta.ambientColor + '33',
              borderColor: meta.ambientColor + 'AA',
              color:       meta.ambientColor,
            } : {}}
          >
            {loc}
          </Button>
        ))}
      </div>

      {viewMode === '3d' && (
        <div className="absolute top-3 right-3 text-xs text-muted-foreground backdrop-blur-sm bg-black/20 px-2.5 py-1 rounded-md pointer-events-none">
          拖拽平移 · 滚轮缩放 · 3D
        </div>
      )}
    </div>
  )
}
