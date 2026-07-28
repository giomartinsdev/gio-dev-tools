import { useCallback, useEffect, useRef, useState } from 'react'
import { Bus, Check, Loader2, Plus, Trash2 } from 'lucide-react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { Skeleton } from 'boneyard-js/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

// OpenFreeMap — free, no API key, no rate limits. `demotiles` (the previous
// style) has no streets/labels, just country borders, which is why the map
// looked empty/useless; these are full street-level styles. The style JSON
// can 503 on a cold cache hit (observed live) — MapLibre retries it on its
// own, so this doesn't need special handling here.
const MAP_STYLE_LIGHT = 'https://tiles.openfreemap.org/styles/liberty'
const MAP_STYLE_DARK = 'https://tiles.openfreemap.org/styles/dark'
const RIO_CENTER: [number, number] = [-43.2, -22.9]
const DEFAULT_MARKER_COLOR = '#6366f1'

function isDarkMode(): boolean {
  return document.documentElement.classList.contains('dark')
}

const MODES = ['sppo', 'brt'] as const
type Mode = typeof MODES[number]
const MODE_LABEL: Record<Mode, string> = { sppo: 'Ônibus (SPPO)', brt: 'BRT' }

interface TrackedLine {
  id: string
  line_code: string
  mode: Mode
  label: string | null
  active: boolean
}

interface Position {
  mode: Mode
  line_code: string
  vehicle_id: string
  latitude: number
  longitude: number
  speed_kmh: number
  color_hex: string | null
  captured_at: string
}

interface SelectedLine {
  code: string
  mode: Mode
}

function emptyDraft() {
  return { line_code: '', mode: 'sppo' as Mode, label: '' }
}

export function BusTrackerModule() {
  const [lines, setLines] = useState<TrackedLine[]>([])
  const [loadingLines, setLoadingLines] = useState(true)
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState(emptyDraft())
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [selectedLine, setSelectedLine] = useState<SelectedLine | null>(null)
  const [positionsByVehicle, setPositionsByVehicle] = useState<Record<string, Position>>({})
  const [positionsSettled, setPositionsSettled] = useState(false)

  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<Map<string, maplibregl.Marker>>(new Map())
  const hasFitBoundsRef = useRef(false)

  const loadLines = useCallback(async () => {
    setLoadingLines(true)
    try {
      const res = await fetch(`${GATEWAY}/bus-tracker/lines`)
      if (res.ok) {
        const data: TrackedLine[] = await res.json()
        setLines(data)
        setSelectedLine(prev => prev ?? (
          data.find(l => l.active)
            ? { code: data.find(l => l.active)!.line_code, mode: data.find(l => l.active)!.mode }
            : null
        ))
      }
    } finally {
      setLoadingLines(false)
    }
  }, [])

  useEffect(() => { loadLines() }, [loadLines])

  async function submitCreate() {
    if (!draft.line_code.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${GATEWAY}/bus-tracker/lines`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || 'Falha ao cadastrar linha')
      }
      setDraft(emptyDraft())
      setCreating(false)
      await loadLines()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao cadastrar linha')
    } finally {
      setSubmitting(false)
    }
  }

  async function remove(id: string) {
    setDeletingId(id)
    try {
      await fetch(`${GATEWAY}/bus-tracker/lines/${id}`, { method: 'DELETE' })
      await loadLines()
    } finally {
      setDeletingId(null)
    }
  }

  // Reset markers and load the latest snapshot whenever the selected line changes.
  useEffect(() => {
    if (!selectedLine) {
      setPositionsByVehicle({})
      return
    }
    let cancelled = false
    setPositionsByVehicle({})
    setPositionsSettled(false)
    hasFitBoundsRef.current = false
    const params = `line=${encodeURIComponent(selectedLine.code)}&mode=${selectedLine.mode}`
    fetch(`${GATEWAY}/bus-tracker/positions/latest?${params}`)
      .then(r => (r.ok ? r.json() : []))
      .then((rows: Position[]) => {
        if (cancelled) return
        const byVehicle: Record<string, Position> = {}
        for (const row of rows) byVehicle[row.vehicle_id] = row
        setPositionsByVehicle(byVehicle)
      })
      .finally(() => { if (!cancelled) setPositionsSettled(true) })
      .catch(() => { /* ignore — SSE will still bring live updates */ })
    return () => { cancelled = true }
  }, [selectedLine])

  // Live updates via SSE — one push per captured position for the selected line.
  useEffect(() => {
    if (!selectedLine) return
    const params = `line=${encodeURIComponent(selectedLine.code)}&mode=${selectedLine.mode}`
    const es = new EventSource(`${GATEWAY}/bus-tracker/positions/events?${params}`)
    es.onmessage = (e) => {
      try {
        const position = JSON.parse(e.data as string) as Position
        setPositionsByVehicle(prev => ({ ...prev, [position.vehicle_id]: position }))
      } catch { /* ignore malformed */ }
    }
    return () => es.close()
  }, [selectedLine])

  // Map lifecycle — created once, torn down on unmount.
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: isDarkMode() ? MAP_STYLE_DARK : MAP_STYLE_LIGHT,
      center: RIO_CENTER,
      zoom: 11,
    })
    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    mapRef.current = map
    return () => {
      map.remove()
      mapRef.current = null
    }
  }, [])

  // Follow the app's light/dark toggle (a `dark` class on <html>) so the
  // basemap always matches the rest of the dashboard.
  useEffect(() => {
    const observer = new MutationObserver(() => {
      mapRef.current?.setStyle(isDarkMode() ? MAP_STYLE_DARK : MAP_STYLE_LIGHT)
    })
    observer.observe(document.documentElement, { attributes: true, attributeFilter: ['class'] })
    return () => observer.disconnect()
  }, [])

  function busMarkerEl(color: string): HTMLDivElement {
    const el = document.createElement('div')
    el.className = 'flex h-7 w-7 items-center justify-center rounded-full ring-2 ring-white shadow-md'
    el.style.backgroundColor = color
    el.innerHTML = `
      <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24"
           fill="none" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M8 6v6"/><path d="M15 6v6"/><path d="M2 12h19.6"/>
        <path d="M18 18h3s.5-1.7.8-2.8c.1-.4.2-.8.2-1.2 0-.4-.1-.8-.2-1.2l-1.4-5C20.1 6.8 19.1 6 18 6H4a2 2 0 0 0-2 2v10h3"/>
        <circle cx="7" cy="18" r="2"/><path d="M9 18h5"/><circle cx="16" cy="18" r="2"/>
      </svg>`
    return el
  }

  // Sync markers with the current position set, and keep the map framed on
  // whatever is currently visible instead of leaving the user to hunt for it.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const markers = markersRef.current
    const seen = new Set<string>()
    const bounds = new maplibregl.LngLatBounds()

    for (const position of Object.values(positionsByVehicle)) {
      seen.add(position.vehicle_id)
      const lngLat: [number, number] = [position.longitude, position.latitude]
      bounds.extend(lngLat)
      const color = position.color_hex || DEFAULT_MARKER_COLOR
      const popupHtml = `
        <div class="text-xs">
          <div class="font-semibold">${position.vehicle_id}</div>
          <div>${position.speed_kmh.toFixed(0)} km/h</div>
        </div>`
      const existing = markers.get(position.vehicle_id)
      if (existing) {
        existing.setLngLat(lngLat)
        existing.getElement().style.backgroundColor = color
        existing.setPopup(new maplibregl.Popup({ offset: 16 }).setHTML(popupHtml))
        continue
      }
      const marker = new maplibregl.Marker({ element: busMarkerEl(color) })
        .setLngLat(lngLat)
        .setPopup(new maplibregl.Popup({ offset: 16 }).setHTML(popupHtml))
        .addTo(map)
      markers.set(position.vehicle_id, marker)
    }

    for (const [vehicleId, marker] of markers) {
      if (!seen.has(vehicleId)) {
        marker.remove()
        markers.delete(vehicleId)
      }
    }

    if (!bounds.isEmpty() && !hasFitBoundsRef.current) {
      map.fitBounds(bounds, { padding: 80, maxZoom: 15, duration: 600 })
      hasFitBoundsRef.current = true
    }
  }, [positionsByVehicle])

  const vehicleCount = Object.keys(positionsByVehicle).length

  return (
    <div className="flex h-full gap-4">
      <aside className="flex w-72 shrink-0 flex-col gap-3 overflow-y-auto rounded-[14px] border bg-sidebar p-3 shadow-[var(--shadow-card)]">
        <div className="flex items-center justify-between">
          <span className="text-sm font-medium text-sidebar-foreground">Linhas</span>
          {!creating && (
            <Button size="icon" variant="ghost" onClick={() => setCreating(true)}>
              <Plus className="h-4 w-4" />
            </Button>
          )}
        </div>

        {error && (
          <div className="rounded-md border border-destructive/30 bg-destructive/10 px-2.5 py-1.5 text-xs text-destructive">
            {error}
          </div>
        )}

        {creating && (
          <div className="flex flex-col gap-2 rounded-[10px] border bg-card p-3">
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Modal</Label>
              <Select value={draft.mode} onValueChange={v => setDraft(d => ({ ...d, mode: v as Mode }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {MODES.map(m => <SelectItem key={m} value={m}>{MODE_LABEL[m]}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Código da linha</Label>
              <Input
                value={draft.line_code}
                onChange={e => setDraft(d => ({ ...d, line_code: e.target.value }))}
                placeholder="ex: 483"
                autoFocus
              />
            </div>
            <div className="flex flex-col gap-1">
              <Label className="text-xs">Rótulo (opcional)</Label>
              <Input
                value={draft.label}
                onChange={e => setDraft(d => ({ ...d, label: e.target.value }))}
                placeholder="ex: Rocinha - Leblon"
              />
            </div>
            <div className="flex justify-end gap-2 pt-1">
              <Button variant="outline" size="sm" onClick={() => { setCreating(false); setDraft(emptyDraft()); setError(null) }}>
                Cancelar
              </Button>
              <Button size="sm" onClick={submitCreate} disabled={submitting || !draft.line_code.trim()}>
                {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                Salvar
              </Button>
            </div>
          </div>
        )}

        <Skeleton name="bus-tracker-lines" loading={loadingLines} className="flex-1">
          <div className="flex flex-col gap-1.5">
            {lines.length === 0 && (
              <div className="rounded-[10px] border border-dashed p-4 text-center text-xs text-muted-foreground">
                Nenhuma linha cadastrada ainda.
              </div>
            )}
            {lines.map(line => (
              <button
                key={line.id}
                onClick={() => setSelectedLine({ code: line.line_code, mode: line.mode })}
                className={cn(
                  'flex w-full items-center justify-between gap-2 rounded-[10px] border px-3 py-2 text-left transition-colors',
                  selectedLine?.code === line.line_code && selectedLine?.mode === line.mode
                    ? 'bg-sidebar-accent border-primary/40'
                    : 'hover:bg-sidebar-accent/50',
                )}
              >
                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-sm font-medium">{line.line_code}</span>
                    <span className="rounded-md border px-1.5 py-0.5 text-[10px] text-muted-foreground">
                      {MODE_LABEL[line.mode]}
                    </span>
                    {!line.active && (
                      <span className="rounded-full bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground">
                        inativa
                      </span>
                    )}
                  </div>
                  {line.label && <span className="truncate text-xs text-muted-foreground">{line.label}</span>}
                </div>
                <span
                  role="button"
                  tabIndex={-1}
                  onClick={e => { e.stopPropagation(); remove(line.id) }}
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                >
                  {deletingId === line.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                </span>
              </button>
            ))}
          </div>
        </Skeleton>
      </aside>

      <div className="relative flex-1 overflow-hidden rounded-[14px] border shadow-[var(--shadow-card)]">
        {!selectedLine ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
            <Bus className="h-10 w-10 opacity-20" />
            <p className="text-sm">Cadastre ou selecione uma linha para acompanhar</p>
          </div>
        ) : (
          <div className="absolute left-3 top-3 z-10 flex flex-col gap-1.5">
            <div className="rounded-full bg-card/90 px-3 py-1.5 text-xs font-medium shadow-sm backdrop-blur">
              {MODE_LABEL[selectedLine.mode]} {selectedLine.code} — {vehicleCount} {vehicleCount === 1 ? 'veículo' : 'veículos'} em tempo real
            </div>
            {positionsSettled && vehicleCount === 0 && (
              <div className="max-w-72 rounded-[10px] bg-card/90 px-3 py-2 text-xs text-muted-foreground shadow-sm backdrop-blur">
                Nenhum veículo reportando posição agora. A fonte de dados
                (dados.mobilidade.rio) às vezes fica sem atualização ao vivo
                para {MODE_LABEL[selectedLine.mode]} — a tela atualiza
                automaticamente assim que houver dados.
              </div>
            )}
          </div>
        )}
        <div ref={mapContainerRef} className="h-full w-full" />
      </div>
    </div>
  )
}

export const busTrackerMeta = {
  id: 'bus-tracker' as const,
  label: 'Ônibus (Rio)',
  description: 'Cadastro de linhas e rastreamento de posição em tempo real via dados.mobilidade.rio',
  icon: Bus,
}
