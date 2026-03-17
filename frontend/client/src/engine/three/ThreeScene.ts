/**
 * ThreeScene — Three.js scene, orthographic camera, renderers, and lighting.
 *
 * Coordinate system:
 *   X = column × TILE_SIZE
 *   Z = row    × TILE_SIZE
 *   Y = height (0 = ground)
 */

import * as THREE from 'three'
import { CSS2DRenderer } from 'three/addons/renderers/CSS2DRenderer.js'

export const TILE_SIZE   = 1      // 1 Three.js unit per tile
export const CAMERA_DIST = 20     // orthographic half-size

export interface ThreeSceneHandle {
  scene:        THREE.Scene
  camera:       THREE.OrthographicCamera
  renderer:     THREE.WebGLRenderer
  css2d:        CSS2DRenderer
  labelLayer:   HTMLElement
  resize:       (w: number, h: number) => void
  render:       () => void
  dispose:      () => void
}

/** Isometric angle (degrees). 35.264° ≈ true isometric; 30° = classic RPG. */
const ELEV_DEG = 30

export function createThreeScene(
  canvas: HTMLCanvasElement,
  containerEl: HTMLElement,
): ThreeSceneHandle {
  const scene = new THREE.Scene()
  scene.background = new THREE.Color('#0d1117')
  scene.fog = new THREE.Fog('#0d1117', 120, 350)

  // ── Camera ──────────────────────────────────────────────────────
  const aspect = canvas.clientWidth / (canvas.clientHeight || 1)
  const half   = CAMERA_DIST
  const camera = new THREE.OrthographicCamera(
    -half * aspect, half * aspect,
    half, -half,
    0.1, 1000,
  )
  const elevRad = (ELEV_DEG * Math.PI) / 180
  const camDist = 200
  camera.position.set(
    camDist * Math.cos(Math.PI / 4),
    camDist * Math.sin(elevRad),
    camDist * Math.cos(Math.PI / 4),
  )
  camera.lookAt(0, 0, 0)

  // ── Renderer ─────────────────────────────────────────────────────
  const renderer = new THREE.WebGLRenderer({
    canvas,
    antialias: true,
    alpha: false,
    powerPreference: 'high-performance',
  })
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  renderer.shadowMap.enabled = false
  renderer.outputColorSpace = THREE.SRGBColorSpace
  renderer.toneMapping = THREE.ACESFilmicToneMapping
  renderer.toneMappingExposure = 1.1

  // ── CSS2DRenderer (emotion bubbles / labels) ─────────────────────
  const css2d = new CSS2DRenderer()
  css2d.setSize(canvas.clientWidth, canvas.clientHeight)
  css2d.domElement.style.position = 'absolute'
  css2d.domElement.style.top      = '0'
  css2d.domElement.style.left     = '0'
  css2d.domElement.style.pointerEvents = 'none'
  containerEl.appendChild(css2d.domElement)
  const labelLayer = css2d.domElement

  // ── Lighting ─────────────────────────────────────────────────────
  const ambient = new THREE.AmbientLight(0xffffff, 0.6)
  scene.add(ambient)

  const sun = new THREE.DirectionalLight(0xffeedd, 1.2)
  sun.position.set(100, 150, 80)
  scene.add(sun)

  const fill = new THREE.DirectionalLight(0xaaccff, 0.4)
  fill.position.set(-20, 10, -10)
  scene.add(fill)

  // ── Helpers ───────────────────────────────────────────────────────
  function resize(w: number, h: number) {
    const newAspect = w / (h || 1)
    camera.left   = -half * newAspect
    camera.right  =  half * newAspect
    camera.top    =  half
    camera.bottom = -half
    camera.updateProjectionMatrix()
    renderer.setSize(w, h)
    css2d.setSize(w, h)
  }

  function render() {
    renderer.render(scene, camera)
    css2d.render(scene, camera)
  }

  function dispose() {
    scene.traverse(obj => {
      if (obj instanceof THREE.Mesh) {
        obj.geometry?.dispose()
        const mats = Array.isArray(obj.material) ? obj.material : [obj.material]
        mats.forEach((m: THREE.Material) => m.dispose())
      }
    })
    renderer.dispose()
    if (labelLayer.parentElement) {
      labelLayer.parentElement.removeChild(labelLayer)
    }
  }

  return { scene, camera, renderer, css2d, labelLayer, resize, render, dispose }
}

/** Convert tile col/row to Three.js world XZ coords (center of tile). */
export function tileToWorld(col: number, row: number): THREE.Vector3 {
  return new THREE.Vector3(
    (col + 0.5) * TILE_SIZE,
    0,
    (row + 0.5) * TILE_SIZE,
  )
}

/** Convert pixel-space coords (from game entity) to Three.js world XZ. */
export function pixelToWorld(pixelX: number, pixelY: number, tileSize: number): THREE.Vector3 {
  return new THREE.Vector3(
    (pixelX / tileSize) * TILE_SIZE,
    0,
    (pixelY / tileSize) * TILE_SIZE,
  )
}

/** Pan/zoom: offset the camera and its target in the XZ plane. */
export function setCameraTarget(
  camera: THREE.OrthographicCamera,
  centerCol: number,
  centerRow: number,
  zoom: number,
): void {
  const half      = CAMERA_DIST / zoom
  const aspect    = (camera.right - camera.left) / (camera.top - camera.bottom + 0.001)
  camera.left     = -half * aspect
  camera.right    =  half * aspect
  camera.top      =  half
  camera.bottom   = -half

  const targetX   = (centerCol + 0.5) * TILE_SIZE
  const targetZ   = (centerRow + 0.5) * TILE_SIZE
  const elevRad   = (ELEV_DEG * Math.PI) / 180
  const camDist   = 200
  camera.position.set(
    targetX + camDist * Math.cos(Math.PI / 4),
    camDist * Math.sin(elevRad),
    targetZ + camDist * Math.cos(Math.PI / 4),
  )
  camera.lookAt(targetX, 0, targetZ)
  camera.updateProjectionMatrix()
}
