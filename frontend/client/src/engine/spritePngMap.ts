/**
 * Sprite → PNG key registry.
 *
 * Maps SpriteData object-references (defined in spriteSystem.ts / sceneTiles.ts)
 * to their corresponding key in the objects_manifest.json.
 * This lets renderSceneObjects upgrade any registered sprite to a PNG without
 * touching the hundreds of individual SceneObject entries in sceneTiles.ts.
 */

import type { SpriteData } from './spriteSystem'

const _map = new Map<SpriteData, string>()

export function registerSpritePngKey(sprite: SpriteData, key: string): void {
  _map.set(sprite, key)
}

export function getSpritePngKey(sprite: SpriteData): string | undefined {
  return _map.get(sprite)
}
