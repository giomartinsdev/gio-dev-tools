import { useEffect, type RefObject } from 'react'

const RADIUS = 130
const STRENGTH = 34

interface Letter {
  el: HTMLElement
  restX: number
  restY: number
  x: number
  y: number
  vx: number
  vy: number
}

/** Splits the hero name into per-letter spans and makes them nudge away from
 * the cursor with spring physics — the page's one signature interaction,
 * on the content itself rather than a decorative shape. Runs once on mount;
 * the name never re-renders afterward, so direct DOM ownership here is safe. */
export function useMagneticName(
  nameRef: RefObject<HTMLHeadingElement | null>,
  stageRef: RefObject<HTMLDivElement | null>,
) {
  useEffect(() => {
    const heroName = nameRef.current
    const stage = stageRef.current
    if (!heroName || !stage) return

    function splitIntoLetters(node: Node) {
      node.childNodes.forEach((child) => {
        if (child.nodeType === Node.TEXT_NODE) {
          const frag = document.createDocumentFragment()
          for (const ch of child.textContent ?? '') {
            if (ch === ' ') {
              frag.appendChild(document.createTextNode(' '))
              continue
            }
            const span = document.createElement('span')
            span.className = 'letter'
            span.textContent = ch
            frag.appendChild(span)
          }
          child.replaceWith(frag)
        } else if (child.nodeType === Node.ELEMENT_NODE) {
          splitIntoLetters(child)
        }
      })
    }
    splitIntoLetters(heroName)

    // Give the gradient on the italic word one continuous sweep across the
    // whole word instead of restarting inside every single letter span.
    const emEl = heroName.querySelector('em')
    function layoutGradient() {
      if (!emEl) return
      const emRect = emEl.getBoundingClientRect()
      emEl.querySelectorAll<HTMLElement>('.letter').forEach((span) => {
        const r = span.getBoundingClientRect()
        span.style.backgroundSize = emRect.width + 'px 100%'
        span.style.backgroundPosition = `${-(r.left - emRect.left)}px 0`
      })
    }
    layoutGradient()

    const reduceMotion = matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) return

    const letters: Letter[] = Array.from(heroName.querySelectorAll<HTMLElement>('.letter')).map((el) => ({
      el, restX: 0, restY: 0, x: 0, y: 0, vx: 0, vy: 0,
    }))

    function measure() {
      const stageRect = stage!.getBoundingClientRect()
      for (const l of letters) {
        l.el.style.transform = 'translate(0px, 0px)'
        const r = l.el.getBoundingClientRect()
        l.restX = r.left + r.width / 2 - stageRect.left
        l.restY = r.top + r.height / 2 - stageRect.top
      }
      layoutGradient()
    }
    measure()
    window.addEventListener('resize', measure)

    const pointer = { x: -9999, y: -9999 }
    function onPointerMove(e: PointerEvent) {
      const r = stage!.getBoundingClientRect()
      pointer.x = e.clientX - r.left
      pointer.y = e.clientY - r.top
    }
    function onPointerLeave() {
      pointer.x = pointer.y = -9999
    }
    stage.addEventListener('pointermove', onPointerMove)
    stage.addEventListener('pointerleave', onPointerLeave)

    let frame = 0
    function magnetTick() {
      for (const l of letters) {
        const dx = l.restX - pointer.x
        const dy = l.restY - pointer.y
        const dist = Math.hypot(dx, dy)
        let tx = 0, ty = 0
        if (dist < RADIUS) {
          const push = (1 - dist / RADIUS) * STRENGTH
          const ux = dist === 0 ? 0 : dx / dist
          const uy = dist === 0 ? 0 : dy / dist
          tx = ux * push
          ty = uy * push
        }
        l.vx = (l.vx + (tx - l.x) * 0.18) * 0.72
        l.vy = (l.vy + (ty - l.y) * 0.18) * 0.72
        l.x += l.vx
        l.y += l.vy
        l.el.style.transform = `translate(${l.x.toFixed(1)}px, ${l.y.toFixed(1)}px)`
      }
      frame = requestAnimationFrame(magnetTick)
    }
    frame = requestAnimationFrame(magnetTick)

    return () => {
      cancelAnimationFrame(frame)
      window.removeEventListener('resize', measure)
      stage.removeEventListener('pointermove', onPointerMove)
      stage.removeEventListener('pointerleave', onPointerLeave)
    }
  }, [nameRef, stageRef])
}
