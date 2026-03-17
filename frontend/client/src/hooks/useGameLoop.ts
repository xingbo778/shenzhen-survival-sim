/**
 * useGameLoop — drives a requestAnimationFrame render loop.
 *
 * The callback receives pre-computed dt (seconds), tick count, and a
 * sin-based pulse value so callers don't need to maintain their own timers.
 */

import { useRef, useEffect } from 'react'

type FrameCallback = (dt: number, tick: number, pulse: number) => void

export function useGameLoop(callback: FrameCallback): void {
  const callbackRef = useRef<FrameCallback>(callback)
  callbackRef.current = callback  // always up-to-date without re-subscribing

  const animFrameRef = useRef<number>(0)
  const lastTimeRef  = useRef<number>(0)
  const tickRef      = useRef<number>(0)
  const pulseRef     = useRef<number>(0)

  useEffect(() => {
    lastTimeRef.current = performance.now()

    const frame = (timestamp: number) => {
      const dt = Math.min((timestamp - lastTimeRef.current) / 1000, 0.05)
      lastTimeRef.current = timestamp
      tickRef.current  += 1
      pulseRef.current  = (pulseRef.current + dt * 1.5) % (Math.PI * 2)
      callbackRef.current(dt, tickRef.current, Math.sin(pulseRef.current))
      animFrameRef.current = requestAnimationFrame(frame)
    }

    animFrameRef.current = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(animFrameRef.current)
  }, []) // intentionally stable — callback updates via ref
}
