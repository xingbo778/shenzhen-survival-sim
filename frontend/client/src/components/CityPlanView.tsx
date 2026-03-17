/**
 * CityPlanView — 2D top-down plan view of the procedural city.
 *
 * Renders the tilemap as colored pixels and overlays building footprints,
 * furniture markers, and a legend. Useful for inspecting layout quality
 * before switching to the 3D view.
 */

import { useRef, useEffect, useCallback, useState, useMemo } from 'react'
import type { SceneConfig, SceneObject, TileType } from '@/engine/sceneTiles'
import { TILE_COLORS } from '@/engine/sceneTiles'
import { isFurnitureKey } from '@/engine/three/StreetFurniture3D'

// ── Tile color palette (flat hex → CSS) ──────────────────────────────
const tileColor = (t: TileType): string => TILE_COLORS[t]?.base ?? '#222'

// ── Object category colors ───────────────────────────────────────────
const OBJ_COLORS: Record<string, string> = {
  landmark_civic:  '#FF6B6B',
  landmark_pingan: '#FF4444',
  landmark_expo:   '#FF8866',
  landmark_kk100:  '#FF5555',
  office_tower:  '#4488FF',
  cbd_building:  '#3366DD',
  apartment_block: '#88AACC',
  village_building: '#AA8866',
  shop_building: '#FFAA44',
  palm_tree:     '#22CC44',
  street_tree:   '#33AA33',
  traffic_light: '#FF4444',
  street_lamp:   '#FFDD44',
  road_sign:     '#FF8800',
  bench:         '#886644',
  metro_entrance:'#2255CC',
  fountain:      '#44BBFF',
  fire_hydrant:  '#FF2222',
  trash_bin:     '#6688AA',
  bus_stop:      '#FF6600',
  bollard:       '#999999',
  phone_booth:   '#CC4444',
  mailbox:       '#2244AA',
  flower_bed:    '#FF88CC',
  billboard:     '#DDAA00',
}

function objColor(key: string): string {
  for (const [prefix, color] of Object.entries(OBJ_COLORS)) {
    if (key.startsWith(prefix)) return color
  }
  return '#FF00FF'
}

// ── Legend categories ────────────────────────────────────────────────
const LEGEND: { label: string; color: string }[] = [
  { label: '道路', color: '#484848' },
  { label: '人行道', color: '#A09080' },
  { label: '草地', color: '#3A6A28' },
  { label: '广场', color: '#C0B090' },
  { label: '水域', color: '#1A3A5A' },
  { label: '混凝土', color: '#686860' },
  { label: '小巷', color: '#383830' },
  { label: '─────', color: 'transparent' },
  { label: 'CBD/写字楼', color: '#4488FF' },
  { label: '公寓', color: '#88AACC' },
  { label: '城中村', color: '#AA8866' },
  { label: '商铺', color: '#FFAA44' },
  { label: '─────', color: 'transparent' },
  { label: '树木', color: '#33AA33' },
  { label: '红绿灯', color: '#FF4444' },
  { label: '路灯', color: '#FFDD44' },
  { label: '地铁口', color: '#2255CC' },
  { label: '其他设施', color: '#999999' },
]

interface Props {
  sceneConfig: SceneConfig
}

export default function CityPlanView({ sceneConfig }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const containerRef = useRef<HTMLDivElement>(null)

  // Pan & zoom state
  const [zoom, setZoom] = useState(1)
  const [offset, setOffset] = useState({ x: 0, y: 0 })
  const dragging = useRef(false)
  const dragStart = useRef({ x: 0, y: 0, ox: 0, oy: 0 })

  const { cols, rows, tilemap, objects, roadLabels, landmarkLabels } = sceneConfig

  // Separate buildings from furniture (memoized to avoid re-creating arrays on every render)
  const buildings = useMemo(() => objects.filter(o => o.pngKey && !isFurnitureKey(o.pngKey)), [objects])
  const furniture = useMemo(() => objects.filter(o => o.pngKey && isFurnitureKey(o.pngKey)), [objects])

  const draw = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const cw = canvas.clientWidth
    const ch = canvas.clientHeight
    canvas.width = cw * dpr
    canvas.height = ch * dpr
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0)

    // Clear
    ctx.fillStyle = '#0d1117'
    ctx.fillRect(0, 0, cw, ch)

    // Compute pixel size per tile
    const pxPerTile = Math.max(1, zoom * Math.min(cw / cols, ch / rows))
    const totalW = cols * pxPerTile
    const totalH = rows * pxPerTile

    // Center + offset
    const baseX = (cw - totalW) / 2 + offset.x
    const baseY = (ch - totalH) / 2 + offset.y

    // Draw tilemap
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const tile = tilemap[r]?.[c]
        if (!tile) continue
        ctx.fillStyle = tileColor(tile)
        ctx.fillRect(
          baseX + c * pxPerTile,
          baseY + r * pxPerTile,
          pxPerTile + 0.5,
          pxPerTile + 0.5,
        )
      }
    }

    // Draw building footprints
    for (const obj of buildings) {
      const tw = obj.tileW ?? 1
      const th = obj.tileH ?? 1
      const x = baseX + obj.col * pxPerTile
      const y = baseY + obj.row * pxPerTile
      const w = tw * pxPerTile
      const h = th * pxPerTile

      ctx.fillStyle = objColor(obj.pngKey!) + 'CC'
      ctx.fillRect(x, y, w, h)

      // Border
      ctx.strokeStyle = objColor(obj.pngKey!)
      ctx.lineWidth = Math.max(0.5, pxPerTile * 0.08)
      ctx.strokeRect(x, y, w, h)

      // Label if zoomed in enough
      if (pxPerTile > 4) {
        ctx.fillStyle = '#fff'
        ctx.font = `${Math.max(6, pxPerTile * 0.35)}px monospace`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        const label = obj.pngKey!.replace(/_v\d+$/, '').replace(/_/g, ' ')
        ctx.fillText(label, x + w / 2, y + h / 2, w - 2)
      }
    }

    // Draw furniture markers
    for (const obj of furniture) {
      const cx = baseX + (obj.col + 0.5) * pxPerTile
      const cy = baseY + (obj.row + 0.5) * pxPerTile
      const r = Math.max(1, pxPerTile * 0.35)

      ctx.beginPath()
      ctx.arc(cx, cy, r, 0, Math.PI * 2)
      ctx.fillStyle = objColor(obj.pngKey!) + 'DD'
      ctx.fill()
    }

    // Grid lines when zoomed in
    if (pxPerTile > 6) {
      ctx.strokeStyle = 'rgba(255,255,255,0.08)'
      ctx.lineWidth = 0.5
      for (let r = 0; r <= rows; r++) {
        ctx.beginPath()
        ctx.moveTo(baseX, baseY + r * pxPerTile)
        ctx.lineTo(baseX + totalW, baseY + r * pxPerTile)
        ctx.stroke()
      }
      for (let c = 0; c <= cols; c++) {
        ctx.beginPath()
        ctx.moveTo(baseX + c * pxPerTile, baseY)
        ctx.lineTo(baseX + c * pxPerTile, baseY + totalH)
        ctx.stroke()
      }
    }

    // Road name labels
    if (roadLabels && pxPerTile > 2) {
      ctx.font = `bold ${Math.max(9, pxPerTile * 0.7)}px sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      for (const rl of roadLabels) {
        const lx = baseX + rl.col * pxPerTile
        const ly = baseY + rl.row * pxPerTile
        ctx.save()
        if (rl.direction === 'v') {
          ctx.translate(lx, ly)
          ctx.rotate(-Math.PI / 2)
          ctx.fillStyle = 'rgba(0,0,0,0.5)'
          ctx.fillText(rl.name, 1, 1)
          ctx.fillStyle = '#FFD700'
          ctx.fillText(rl.name, 0, 0)
        } else {
          ctx.fillStyle = 'rgba(0,0,0,0.5)'
          ctx.fillText(rl.name, lx + 1, ly + 1)
          ctx.fillStyle = '#FFD700'
          ctx.fillText(rl.name, lx, ly)
        }
        ctx.restore()
      }
    }

    // Landmark labels
    if (landmarkLabels && pxPerTile > 2) {
      for (const lm of landmarkLabels) {
        const lx = baseX + (lm.col + lm.w / 2) * pxPerTile
        const ly = baseY + (lm.row + lm.h / 2) * pxPerTile
        const lw = lm.w * pxPerTile
        const lh = lm.h * pxPerTile

        // Dashed border
        ctx.setLineDash([4, 3])
        ctx.strokeStyle = '#FF6B6B88'
        ctx.lineWidth = 1.5
        ctx.strokeRect(baseX + lm.col * pxPerTile, baseY + lm.row * pxPerTile, lw, lh)
        ctx.setLineDash([])

        // Name
        ctx.font = `bold ${Math.max(10, pxPerTile * 0.8)}px sans-serif`
        ctx.textAlign = 'center'
        ctx.textBaseline = 'middle'
        ctx.fillStyle = 'rgba(0,0,0,0.6)'
        ctx.fillText(lm.name, lx + 1, ly + 1, lw - 4)
        ctx.fillStyle = '#FF6B6B'
        ctx.fillText(lm.name, lx, ly, lw - 4)
      }
    }

    // Stats overlay
    ctx.fillStyle = 'rgba(0,0,0,0.6)'
    ctx.fillRect(8, 8, 180, 60)
    ctx.fillStyle = '#fff'
    ctx.font = '11px monospace'
    ctx.textAlign = 'left'
    ctx.textBaseline = 'top'
    ctx.fillText(`Grid: ${cols} × ${rows}`, 14, 14)
    ctx.fillText(`Buildings: ${buildings.length}`, 14, 28)
    ctx.fillText(`Furniture: ${furniture.length}`, 14, 42)
  }, [cols, rows, tilemap, buildings, furniture, zoom, offset, roadLabels, landmarkLabels])

  // Redraw on any state change
  useEffect(() => { draw() }, [draw])

  // Resize observer
  useEffect(() => {
    const container = containerRef.current
    if (!container) return
    const obs = new ResizeObserver(() => draw())
    obs.observe(container)
    return () => obs.disconnect()
  }, [draw])

  // Mouse handlers
  const onMouseDown = useCallback((e: React.MouseEvent) => {
    dragging.current = true
    dragStart.current = { x: e.clientX, y: e.clientY, ox: offset.x, oy: offset.y }
  }, [offset])

  const onMouseMove = useCallback((e: React.MouseEvent) => {
    if (!dragging.current) return
    setOffset({
      x: dragStart.current.ox + (e.clientX - dragStart.current.x),
      y: dragStart.current.oy + (e.clientY - dragStart.current.y),
    })
  }, [])

  const onMouseUp = useCallback(() => { dragging.current = false }, [])

  const onWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault()
    setZoom(z => Math.max(0.3, Math.min(20, z * (e.deltaY > 0 ? 0.9 : 1.1))))
  }, [])

  return (
    <div ref={containerRef} className="relative w-full h-full" style={{ background: '#0d1117' }}>
      <canvas
        ref={canvasRef}
        className="w-full h-full"
        style={{ cursor: dragging.current ? 'grabbing' : 'grab', display: 'block' }}
        onMouseDown={onMouseDown}
        onMouseMove={onMouseMove}
        onMouseUp={onMouseUp}
        onMouseLeave={onMouseUp}
        onWheel={onWheel}
      />

      {/* Legend */}
      <div
        className="absolute top-3 right-3 bg-black/70 border border-white/10 rounded px-3 py-2 text-xs font-mono"
        style={{ maxHeight: '80%', overflowY: 'auto' }}
      >
        <div className="text-white/80 font-bold mb-1">图例 Legend</div>
        {LEGEND.map((item, i) =>
          item.color === 'transparent' ? (
            <div key={i} className="border-t border-white/10 my-1" />
          ) : (
            <div key={i} className="flex items-center gap-2 py-0.5">
              <span
                className="inline-block w-3 h-3 rounded-sm flex-shrink-0"
                style={{ background: item.color }}
              />
              <span className="text-white/60">{item.label}</span>
            </div>
          ),
        )}
      </div>

      {/* Controls hint */}
      <div className="absolute top-3 left-3 text-xs font-mono text-white/30 bg-black/30 px-2 py-0.5 rounded pointer-events-none">
        俯视规划图 · 拖拽平移 · 滚轮缩放
      </div>
    </div>
  )
}
