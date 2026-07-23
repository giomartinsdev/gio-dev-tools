import { useEffect, useRef } from 'react'
import lottie, { type AnimationItem } from 'lottie-web'
import pulseData from '@/assets/lottie/pulse.json'

export function LivePulse({ className }: { className?: string }) {
  const containerRef = useRef<HTMLDivElement>(null)
  const animRef = useRef<AnimationItem | null>(null)

  useEffect(() => {
    if (!containerRef.current) return
    animRef.current = lottie.loadAnimation({
      container: containerRef.current,
      renderer: 'svg',
      loop: true,
      autoplay: true,
      animationData: pulseData,
    })
    return () => animRef.current?.destroy()
  }, [])

  return <div ref={containerRef} className={className ?? 'h-3.5 w-3.5'} aria-hidden="true" />
}
