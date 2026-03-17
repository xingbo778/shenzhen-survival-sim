/**
 * useCanvasResize — keeps a canvas's pixel dimensions in sync with its
 * CSS layout size, accounting for devicePixelRatio.
 */

import { useEffect, type RefObject } from 'react'

export function useCanvasResize(canvasRef: RefObject<HTMLCanvasElement | null>): void {
  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const resize = () => {
      const rect = canvas.getBoundingClientRect()
      const dpr  = window.devicePixelRatio || 1
      canvas.width  = Math.floor(rect.width  * dpr)
      canvas.height = Math.floor(rect.height * dpr)
    }

    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(canvas)
    return () => ro.disconnect()
  }, [canvasRef])
}
