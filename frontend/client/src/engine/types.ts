/**
 * Shared rendering types for the game engine.
 */

/** A drawable item with a Y-depth value for z-sorting. */
export interface ZDrawable {
  zY: number
  draw: (ctx: CanvasRenderingContext2D) => void
}
