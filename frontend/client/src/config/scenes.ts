/**
 * Scene registry — single source of truth for all scene metadata,
 * zoom/pan constants, and the overview-key → scene-name mapping.
 */

export interface SceneMeta {
  /** Accent colour used for UI highlights in this scene. */
  ambientColor: string
  name: string
}

export const SCENE_META: Record<string, SceneMeta> = {
  '宝安城中村': { ambientColor: '#C4956A', name: '宝安城中村' },
  '南山科技园': { ambientColor: '#4D96FF', name: '南山科技园' },
  '福田CBD':    { ambientColor: '#FFD700', name: '福田CBD'    },
  '华强北':     { ambientColor: '#FF4DC8', name: '华强北'     },
  '东门老街':   { ambientColor: '#FF6B6B', name: '东门老街'   },
  '南山公寓':   { ambientColor: '#69DB7C', name: '南山公寓'   },
  '深圳湾公园': { ambientColor: '#74C0FC', name: '深圳湾公园' },
}

export const SCENE_NAMES = Object.keys(SCENE_META)

/** Maps CityOverviewMap location keys → PixelCityMap scene names. */
export const OVERVIEW_TO_SCENE_KEY: Record<string, string> = {
  baoan_urban_village: '宝安城中村',
  nanshan_tech_park:   '南山科技园',
  futian_cbd:          '福田CBD',
  huaqiangbei:         '华强北',
  dongmen_oldstreet:   '东门老街',
  nanshan_apartments:  '南山公寓',
  shenzhen_bay_park:   '深圳湾公园',
}

export const MAP_SCALE = 2.0
export const ZOOM_MIN  = 0.15
export const ZOOM_MAX  = 4.0
export const ZOOM_STEP = 0.15
