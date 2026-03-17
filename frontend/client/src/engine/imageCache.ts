/**
 * Centralized image preloading and caching for the game engine.
 * Prevents duplicate network requests across components.
 */

const _cache: Record<string, HTMLImageElement | null> = {}
const _loaded: Record<string, boolean> = {}

export function preloadImage(url: string): HTMLImageElement {
  if (!_cache[url]) {
    const img = new Image()
    img.onload  = () => { _loaded[url] = true }
    img.onerror = () => { _loaded[url] = false }
    img.src = url
    _cache[url] = img
    _loaded[url] = false
  }
  return _cache[url]!
}

export function getImage(url: string): HTMLImageElement | null {
  return _cache[url] ?? null
}

export function isImageLoaded(url: string): boolean {
  return _loaded[url] === true
}
