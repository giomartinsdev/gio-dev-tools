import { useEffect, type RefObject } from 'react'

const PALETTE = ['#35E0C7', '#FF3E7F', '#6C3FD1']

interface Blob {
  color: string
  baseX: number
  baseY: number
  r: number
  phase: number
  speed: number
}

/** Soft drifting duotone blobs behind the hero, screen-blended over the ink
 * background. Reacts subtly to pointer position. Respects reduced motion. */
export function useAuroraCanvas(canvasRef: RefObject<HTMLCanvasElement | null>) {
  useEffect(() => {
    const canvas = canvasRef.current
    const parent = canvas?.parentElement
    if (!canvas || !parent) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches
    let w = 0, h = 0, dpr = 1
    let frame = 0

    function resize() {
      dpr = Math.min(window.devicePixelRatio || 1, 2)
      w = parent!.offsetWidth
      h = parent!.offsetHeight
      canvas!.width = w * dpr
      canvas!.height = h * dpr
      canvas!.style.width = w + 'px'
      canvas!.style.height = h + 'px'
      ctx!.setTransform(dpr, 0, 0, dpr, 0, 0)
    }
    resize()
    window.addEventListener('resize', resize)

    const blobs: Blob[] = PALETTE.map((color, i) => ({
      color,
      baseX: 0.22 + i * 0.32,
      baseY: 0.3 + (i % 2) * 0.4,
      r: 0.34 + i * 0.04,
      phase: i * 2.1,
      speed: 0.00008,
    }))

    const pointer = { x: 0.5, y: 0.5 }
    function onPointerMove(e: PointerEvent) {
      const rect = parent!.getBoundingClientRect()
      pointer.x = (e.clientX - rect.left) / rect.width
      pointer.y = (e.clientY - rect.top) / rect.height
    }
    window.addEventListener('pointermove', onPointerMove)

    function draw(t: number) {
      ctx!.clearRect(0, 0, w, h)
      ctx!.fillStyle = '#120A18'
      ctx!.fillRect(0, 0, w, h)

      ctx!.globalCompositeOperation = 'screen'
      for (const b of blobs) {
        const drift = reduceMotion ? 0 : t * b.speed
        const px = pointer.x - 0.5
        const py = pointer.y - 0.5
        const x = (b.baseX + Math.sin(drift + b.phase) * 0.05 + px * 0.03) * w
        const y = (b.baseY + Math.cos(drift * 0.8 + b.phase) * 0.06 + py * 0.03) * h
        const r = b.r * Math.max(w, h)
        const grad = ctx!.createRadialGradient(x, y, 0, x, y, r)
        grad.addColorStop(0, b.color + '3d')
        grad.addColorStop(1, b.color + '00')
        ctx!.fillStyle = grad
        ctx!.beginPath()
        ctx!.arc(x, y, r, 0, Math.PI * 2)
        ctx!.fill()
      }
      ctx!.globalCompositeOperation = 'source-over'

      if (!reduceMotion) frame = requestAnimationFrame(draw)
    }
    frame = requestAnimationFrame(draw)

    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', resize)
      window.removeEventListener('pointermove', onPointerMove)
    }
  }, [canvasRef])
}
