/**
 * Character sprite system — sheet mapping, bot drawing, and emotion bubbles.
 */

import { getImage, isImageLoaded, preloadImage } from './imageCache'
import type { ZDrawable } from './types'
import type { GameEntity, Facing } from './gameEntity'
import type { WorldState } from '@/types/world'
import { BOT_COLORS } from '@/types/world'

// ── Sprite sheet registry ────────────────────────────────────────

export const CHAR_SHEETS: Record<string, string> = {
  waimai:   '/sprites/characters/waimai.png',
  coder:    '/sprites/characters/coder.png',
  uncle:    '/sprites/characters/uncle.png',
  trader:   '/sprites/characters/trader.png',
  office:   '/sprites/characters/office.png',
  runner:   '/sprites/characters/runner.png',
  startup:  '/sprites/characters/startup.png',
  drifter:  '/sprites/characters/drifter.png',
  dancer:   '/sprites/characters/dancer.png',
  guard:    '/sprites/characters/guard.png',
  reporter: '/sprites/characters/reporter.png',
}

export const CHAR_CELL_W  = 256
export const CHAR_CELL_H  = 256

// 8-frame layout: front, back, left, right, front_left, back_left, front_right, back_right
const FACING_TO_FRAME: Record<Facing, number> = {
  front: 0, back: 1, left: 2, right: 3,
  front_left: 4, back_left: 5, front_right: 6, back_right: 7,
}

const TARGET_CHAR_H = 55
export const CHAR_SCALE    = TARGET_CHAR_H / CHAR_CELL_H
export const CHAR_OFFSET_Y = 0.88

const OCC_TO_SHEET: Record<string, string> = {
  '外卖骑手': 'waimai',
  '程序员':   'coder',
  '城中村大叔': 'uncle',
  '华强北商人': 'trader',
  '白领':     'office',
  '跑步者':   'runner',
  '创业者':   'startup',
  '深漂青年': 'drifter',
  '广场舞大妈': 'dancer',
  '保安':     'guard',
  '金融人':   'trader',
  '工人':     'uncle',
  '设计师':   'coder',
  '富二代':   'office',
  '商人':     'trader',
  '餐馆老板': 'uncle',
  '音乐人':   'drifter',
  '网红':     'startup',
  '记者':     'reporter',
}

const FALLBACK_SHEET_KEYS = [
  'startup', 'office', 'drifter', 'coder', 'guard',
  'trader', 'dancer', 'uncle', 'runner', 'waimai',
]

export function getCharSheetKey(occupation: string | undefined, paletteIndex: number): string {
  if (occupation && OCC_TO_SHEET[occupation]) return OCC_TO_SHEET[occupation]
  return FALLBACK_SHEET_KEYS[paletteIndex % FALLBACK_SHEET_KEYS.length]
}

export function preloadAllCharSheets(): void {
  Object.values(CHAR_SHEETS).forEach(url => preloadImage(url))
}

// ── Emotion bubbles ──────────────────────────────────────────────

export interface EmotionBubble {
  botId: string
  emoji: string
  x: number
  y: number
  alpha: number
  timer: number
}

/**
 * Advance all bubbles by dt, collect their drawables, and return only the
 * surviving (timer > 0) bubbles so the caller can replace the array.
 */
export function tickAndCollectBubbleDrawables(
  bubbles: EmotionBubble[],
  entities: Record<string, GameEntity>,
  dt: number,
  worldX: number,
  worldY: number,
  drawables: ZDrawable[],
): EmotionBubble[] {
  const renderH = Math.round(CHAR_CELL_H * CHAR_SCALE)
  const alive: EmotionBubble[] = []

  for (const bubble of bubbles) {
    bubble.timer -= dt
    if (bubble.timer <= 0) continue
    alive.push(bubble)
    bubble.alpha = Math.min(1, bubble.timer / 0.5)

    const entity = entities[bubble.botId]
    if (!entity) continue

    const bx = worldX + entity.pixelX
    const by = worldY + entity.pixelY - renderH * CHAR_OFFSET_Y - 30
    const snap = { emoji: bubble.emoji, alpha: bubble.alpha }

    drawables.push({
      zY: worldY + entity.pixelY - 200,
      draw: (c) => {
        c.save()
        c.globalAlpha = snap.alpha
        c.fillStyle = 'rgba(30,30,40,0.85)'
        c.beginPath()
        c.roundRect(bx - 14, by - 14, 28, 24, 6)
        c.fill()
        c.beginPath()
        c.moveTo(bx - 4, by + 10)
        c.lineTo(bx + 4, by + 10)
        c.lineTo(bx, by + 16)
        c.closePath()
        c.fill()
        c.font = '14px sans-serif'
        c.textAlign = 'center'
        c.fillText(snap.emoji, bx, by + 4)
        c.restore()
      },
    })
  }

  return alive
}

// ── Bot character drawables ──────────────────────────────────────

/**
 * Collect shadow, selection ring, sprite, and name-label drawables for one bot.
 * Call once per bot per frame, before z-sorting.
 */
export function collectBotDrawables(
  botId: string,
  entity: GameEntity,
  world: WorldState | null,
  paletteIndex: number,
  worldX: number,
  worldY: number,
  selectedBotId: string | null,
  hoveredBotId: string | null,
  pulse: number,
  cssW: number,
  cssH: number,
  drawables: ZDrawable[],
): void {
  const renderH = Math.round(CHAR_CELL_H * CHAR_SCALE)
  const renderW = Math.round(CHAR_CELL_W * CHAR_SCALE)

  const cx = worldX + entity.pixelX
  const cy = worldY + entity.pixelY
  const zY = cy

  if (cx < -renderW || cx > cssW + renderW || cy < -renderH || cy > cssH + renderH) return

  const isSelected = selectedBotId === botId
  const isHovered  = hoveredBotId === botId
  const botData    = world?.bots[botId]
  const botColor   = BOT_COLORS[botId] || '#4d96ff'

  // Shadow
  drawables.push({
    zY: zY - 0.3,
    draw: (c) => {
      c.save()
      c.beginPath()
      c.ellipse(cx, cy + 2, renderW * 0.35, renderW * 0.12, 0, 0, Math.PI * 2)
      c.fillStyle = 'rgba(0,0,0,0.35)'
      c.fill()
      c.restore()
    },
  })

  // Selection ring
  if (isSelected) {
    drawables.push({
      zY: zY - 0.2,
      draw: (c) => {
        c.save()
        c.beginPath()
        c.ellipse(cx, cy + 2, renderW * 0.45, renderW * 0.15, 0, 0, Math.PI * 2)
        c.strokeStyle = botColor
        c.lineWidth = 2.5
        c.globalAlpha = 0.7 + pulse * 0.3
        c.stroke()
        c.restore()
      },
    })
  }

  // Hover ring
  if (isHovered && !isSelected) {
    drawables.push({
      zY: zY - 0.15,
      draw: (c) => {
        c.save()
        c.beginPath()
        c.ellipse(cx, cy + 2, renderW * 0.4, renderW * 0.13, 0, 0, Math.PI * 2)
        c.strokeStyle = 'rgba(255,255,255,0.6)'
        c.lineWidth = 1.5
        c.stroke()
        c.restore()
      },
    })
  }

  // Character sprite — select frame based on 8-direction facing
  const frameIdx = FACING_TO_FRAME[entity.facing] ?? 0

  const sheetKey = getCharSheetKey(botData?.occupation, paletteIndex)
  const sheetUrl = CHAR_SHEETS[sheetKey]

  drawables.push({
    zY,
    draw: (c) => {
      const sheet = sheetUrl ? getImage(sheetUrl) : null
      if (!sheet || !isImageLoaded(sheetUrl)) {
        c.save()
        c.beginPath()
        c.arc(cx, cy - renderH * 0.5, renderW * 0.3, 0, Math.PI * 2)
        c.fillStyle = botColor
        c.fill()
        c.restore()
        return
      }
      const sx  = frameIdx * CHAR_CELL_W
      const ddx = cx - renderW / 2
      const ddy = cy - renderH * CHAR_OFFSET_Y
      c.save()
      c.globalAlpha = isSelected ? 1.0 : (isHovered ? 0.95 : 0.92)
      c.imageSmoothingEnabled = true
      c.imageSmoothingQuality = 'high'
      c.drawImage(sheet, sx, 0, CHAR_CELL_W, CHAR_CELL_H, ddx, ddy, renderW, renderH)
      if (isSelected) {
        c.globalAlpha = 0.4
        c.globalCompositeOperation = 'screen'
        c.drawImage(sheet, sx, 0, CHAR_CELL_W, CHAR_CELL_H, ddx, ddy, renderW, renderH)
        c.globalCompositeOperation = 'source-over'
      }
      c.restore()
    },
  })

  // Name label
  const botName  = world?.bots[botId]?.name?.slice(0, 4) ?? botId
  const labelY   = cy - renderH * CHAR_OFFSET_Y - 6

  drawables.push({
    zY: zY + 1,
    draw: (c) => {
      c.save()
      c.font = `bold 10px 'Noto Sans SC', monospace`
      c.textAlign = 'center'
      const lw  = c.measureText(botName).width
      const lx  = cx - lw / 2 - 4
      const ly  = labelY - 11
      const lrw = lw + 8
      const lrh = 13
      const r   = 3
      c.fillStyle = 'rgba(0,0,0,0.75)'
      c.beginPath()
      c.moveTo(lx + r, ly)
      c.lineTo(lx + lrw - r, ly)
      c.arcTo(lx + lrw, ly, lx + lrw, ly + r, r)
      c.lineTo(lx + lrw, ly + lrh - r)
      c.arcTo(lx + lrw, ly + lrh, lx + lrw - r, ly + lrh, r)
      c.lineTo(lx + r, ly + lrh)
      c.arcTo(lx, ly + lrh, lx, ly + lrh - r, r)
      c.lineTo(lx, ly + r)
      c.arcTo(lx, ly, lx + r, ly, r)
      c.closePath()
      c.fill()
      c.fillStyle = botColor
      c.globalAlpha = 0.95
      c.fillText(botName, cx, labelY)
      c.restore()
    },
  })
}
