import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
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
// Guanabara Bay / central Rio — a sane default before any line has vehicles.
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

interface UserLocation {
  lat: number
  lon: number
}

interface Stop {
  stop_id: string
  name: string | null
  lat: number
  lon: number
}

interface Direction {
  direction_id: number
  headsign: string | null
}

interface ShapePoint {
  lat: number
  lon: number
}

// Nearest-vertex distance from a point to a GTFS shape polyline — used to
// classify which travel direction a live bus is on, since the real-time GPS
// feed carries no direction field of its own.
function nearestShapeDistanceKm(lat: number, lon: number, shape: ShapePoint[]): number {
  let best = Infinity
  for (const p of shape) {
    const d = haversineKm(lat, lon, p.lat, p.lon)
    if (d < best) best = d
  }
  return best
}

function emptyDraft() {
  return { line_code: '', mode: 'sppo' as Mode, label: '' }
}

// Straight-line (haversine) distance in km — not real street routing, just
// enough for a rough "how far is it" estimate without needing a paid
// routing API.
function haversineKm(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371
  const toRad = (d: number) => (d * Math.PI) / 180
  const dLat = toRad(lat2 - lat1)
  const dLon = toRad(lon2 - lon1)
  const a =
    Math.sin(dLat / 2) ** 2 +
    Math.cos(toRad(lat1)) * Math.cos(toRad(lat2)) * Math.sin(dLon / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

// A stopped/very slow bus (traffic light, terminal) would otherwise imply an
// infinite ETA — floor the speed used for the estimate so "0 km/h right now"
// still gives a sane (if rougher) number instead of "∞ min".
const MIN_ETA_SPEED_KMH = 15

function etaMinutes(distanceKm: number, speedKmh: number): number {
  return (distanceKm / Math.max(speedKmh, MIN_ETA_SPEED_KMH)) * 60
}

// OSRM's free public demo server — no API key, real street-network routing
// (walking and driving profiles), but fair-use capped at ~1 req/sec and no
// live traffic data. Calls are throttled client-side to stay well under that.
const OSRM_URL = 'https://router.project-osrm.org'

async function fetchRouteMinutes(profile: 'foot' | 'car', from: [number, number], to: [number, number]): Promise<number | null> {
  try {
    const coords = `${from[0]},${from[1]};${to[0]},${to[1]}`
    const res = await fetch(`${OSRM_URL}/route/v1/${profile}/${coords}?overview=false`)
    if (!res.ok) return null
    const data = await res.json()
    const duration = data?.routes?.[0]?.duration
    return typeof duration === 'number' ? duration / 60 : null
  } catch {
    return null
  }
}

const ROUTE_ETA_THROTTLE_MS = 4000

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
  const [userLocation, setUserLocation] = useState<UserLocation | null>(null)
  const [locatingUser, setLocatingUser] = useState(false)
  const [locationError, setLocationError] = useState<string | null>(null)
  const [stops, setStops] = useState<Stop[]>([])
  const [routeEta, setRouteEta] = useState<{ stopName: string; walkMinutes: number; driveMinutes: number } | null>(null)
  const [directions, setDirections] = useState<Direction[]>([])
  const [selectedDirection, setSelectedDirection] = useState<number | null>(null)
  const [shapesByDirection, setShapesByDirection] = useState<Record<number, ShapePoint[]>>({})

  const mapContainerRef = useRef<HTMLDivElement>(null)
  const mapRef = useRef<maplibregl.Map | null>(null)
  const markersRef = useRef<Map<string, maplibregl.Marker>>(new Map())
  const userMarkerRef = useRef<maplibregl.Marker | null>(null)
  const stopMarkersRef = useRef<maplibregl.Marker[]>([])
  const hasFitBoundsRef = useRef(false)
  const lastRouteFetchRef = useRef(0)

  // Continuously watch the user's position so the map + nearest-bus summary
  // update on their own as new fixes arrive, with no button to press.
  useEffect(() => {
    if (!navigator.geolocation) {
      setLocationError('Geolocalização não suportada neste navegador')
      return
    }
    setLocatingUser(true)
    const watchId = navigator.geolocation.watchPosition(
      pos => {
        setUserLocation({ lat: pos.coords.latitude, lon: pos.coords.longitude })
        setLocatingUser(false)
        setLocationError(null)
      },
      err => {
        setLocationError(
          err.code === err.PERMISSION_DENIED
            ? 'Permissão de localização negada'
            : 'Não foi possível obter sua localização',
        )
        setLocatingUser(false)
      },
      { enableHighAccuracy: true, timeout: 10000, maximumAge: 5000 },
    )
    return () => navigator.geolocation.clearWatch(watchId)
  }, [])

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

  // GTFS travel directions for the selected line (e.g. "→ Candelária" vs
  // "→ Campo Grande") — picking one scopes stops and live buses to that
  // direction instead of mixing both ways of the route together.
  useEffect(() => {
    setDirections([])
    setSelectedDirection(null)
    setShapesByDirection({})
    if (!selectedLine) return
    let cancelled = false
    const params = `line=${encodeURIComponent(selectedLine.code)}&mode=${selectedLine.mode}`
    fetch(`${GATEWAY}/bus-tracker/lines/directions?${params}`)
      .then(r => (r.ok ? r.json() : []))
      .then((rows: Direction[]) => {
        if (cancelled) return
        setDirections(rows)
        if (rows.length > 0) setSelectedDirection(rows[0].direction_id)
      })
      .catch(() => { /* ignore — falls back to showing both directions mixed */ })
    return () => { cancelled = true }
  }, [selectedLine])

  // Each direction's route shape — needed to tell which direction a live bus
  // is currently on, since the real-time GPS feed has no direction field.
  useEffect(() => {
    if (!selectedLine || directions.length < 2) return
    let cancelled = false
    Promise.all(directions.map(d => {
      const params = `line=${encodeURIComponent(selectedLine.code)}&mode=${selectedLine.mode}&direction=${d.direction_id}`
      return fetch(`${GATEWAY}/bus-tracker/lines/shape?${params}`)
        .then(r => (r.ok ? r.json() : []))
        .then((shape: ShapePoint[]) => [d.direction_id, shape] as const)
    }))
      .then(entries => { if (!cancelled) setShapesByDirection(Object.fromEntries(entries)) })
      .catch(() => { /* ignore — falls back to showing both directions mixed */ })
    return () => { cancelled = true }
  }, [selectedLine, directions])

  // GTFS bus stops for the selected line + direction — the fixed points a
  // route-aware ETA routes through, instead of a straight line to wherever
  // the bus currently is.
  useEffect(() => {
    setStops([])
    setRouteEta(null)
    if (!selectedLine || selectedDirection === null) return
    let cancelled = false
    const params = `line=${encodeURIComponent(selectedLine.code)}&mode=${selectedLine.mode}&direction=${selectedDirection}`
    fetch(`${GATEWAY}/bus-tracker/lines/stops?${params}`)
      .then(r => (r.ok ? r.json() : []))
      .then((rows: Stop[]) => { if (!cancelled) setStops(rows) })
      .catch(() => { /* ignore — falls back to straight-line estimate */ })
    return () => { cancelled = true }
  }, [selectedLine, selectedDirection])

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

  // Keep a "you are here" marker in sync with the requested browser location.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    if (!userLocation) {
      userMarkerRef.current?.remove()
      userMarkerRef.current = null
      return
    }
    const lngLat: [number, number] = [userLocation.lon, userLocation.lat]
    if (userMarkerRef.current) {
      userMarkerRef.current.setLngLat(lngLat)
      return
    }
    const el = document.createElement('div')
    el.className = 'h-4 w-4 rounded-full bg-blue-500 ring-[6px] ring-blue-500/25 shadow-md'
    userMarkerRef.current = new maplibregl.Marker({ element: el })
      .setLngLat(lngLat)
      .setPopup(new maplibregl.Popup({ offset: 12 }).setText('Você está aqui'))
      .addTo(map)
  }, [userLocation])

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

  // Classify each live bus by which direction's route shape it's closest to,
  // and keep only the ones on the selected direction — the real-time feed
  // has no direction field, so this is the only way to tell "→ Candelária"
  // buses apart from "→ Campo Grande" ones without waiting on OSRM.
  const filteredPositions = useMemo(() => {
    const shapeEntries = Object.entries(shapesByDirection)
    if (selectedDirection === null || shapeEntries.length < 2) return positionsByVehicle
    const result: Record<string, Position> = {}
    for (const [vehicleId, position] of Object.entries(positionsByVehicle)) {
      let bestDirection: number | null = null
      let bestDistanceKm = Infinity
      for (const [directionIdStr, shape] of shapeEntries) {
        if (shape.length === 0) continue
        const d = nearestShapeDistanceKm(position.latitude, position.longitude, shape)
        if (d < bestDistanceKm) {
          bestDistanceKm = d
          bestDirection = Number(directionIdStr)
        }
      }
      if (bestDirection === null || bestDirection === selectedDirection) result[vehicleId] = position
    }
    return result
  }, [positionsByVehicle, shapesByDirection, selectedDirection])

  // Sync markers with the current position set, and keep the map framed on
  // whatever is currently visible instead of leaving the user to hunt for it.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    const markers = markersRef.current
    const seen = new Set<string>()
    const bounds = new maplibregl.LngLatBounds()

    for (const position of Object.values(filteredPositions)) {
      seen.add(position.vehicle_id)
      const lngLat: [number, number] = [position.longitude, position.latitude]
      bounds.extend(lngLat)
      const color = position.color_hex || DEFAULT_MARKER_COLOR
      const etaLine = userLocation
        ? (() => {
            const distanceKm = haversineKm(userLocation.lat, userLocation.lon, position.latitude, position.longitude)
            const eta = etaMinutes(distanceKm, position.speed_kmh)
            return `<div>${distanceKm.toFixed(1)} km — ~${Math.round(eta)} min de você</div>`
          })()
        : ''
      const popupHtml = `
        <div class="text-xs">
          <div class="font-semibold">${position.vehicle_id}</div>
          <div>${position.speed_kmh.toFixed(0)} km/h</div>
          ${etaLine}
        </div>`
      const existing = markers.get(position.vehicle_id)
      if (existing) {
        existing.setLngLat(lngLat)
        existing.getElement().style.backgroundColor = color
        // Mutate the existing Popup's content instead of attaching a new
        // Popup instance — MapLibre only live-updates a popup that's
        // currently open in the DOM when you call .setHTML() on that same
        // instance; swapping in a brand-new Popup via .setPopup() leaves an
        // already-open popup showing its stale content until closed and
        // reopened (confirmed live: this is why distance/ETA didn't show up
        // on a popup opened before location permission was granted).
        const popup = existing.getPopup()
        if (popup) {
          popup.setHTML(popupHtml)
        } else {
          existing.setPopup(new maplibregl.Popup({ offset: 16 }).setHTML(popupHtml))
        }
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
  }, [filteredPositions, userLocation])

  const vehicleCount = Object.keys(filteredPositions).length

  const nearestBus = useMemo(() => {
    if (!userLocation) return null
    const withDistance = Object.values(filteredPositions).map(p => ({
      position: p,
      distanceKm: haversineKm(userLocation.lat, userLocation.lon, p.latitude, p.longitude),
    }))
    if (withDistance.length === 0) return null
    return withDistance.reduce((a, b) => (b.distanceKm < a.distanceKm ? b : a))
  }, [userLocation, filteredPositions])

  // The stop closest to the user, among the ones this line actually serves —
  // the point both the user's walk and the bus's road route are computed to.
  const nearestStop = useMemo(() => {
    if (!userLocation || stops.length === 0) return null
    return stops.reduce((a, b) =>
      haversineKm(userLocation.lat, userLocation.lon, b.lat, b.lon) <
      haversineKm(userLocation.lat, userLocation.lon, a.lat, a.lon) ? b : a,
    )
  }, [userLocation, stops])

  // Small dots for the line's GTFS stops — the nearest one to the user (the
  // routing target) is highlighted so it's clear which stop the ETA refers to.
  useEffect(() => {
    const map = mapRef.current
    if (!map) return
    for (const marker of stopMarkersRef.current) marker.remove()
    stopMarkersRef.current = []
    for (const stop of stops) {
      const isNearest = stop.stop_id === nearestStop?.stop_id
      const el = document.createElement('div')
      el.className = isNearest
        ? 'h-3.5 w-3.5 rounded-full bg-amber-400 ring-2 ring-white shadow-md'
        : 'h-2 w-2 rounded-full bg-neutral-400/80 ring-1 ring-white/70 dark:bg-neutral-300/70'
      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([stop.lon, stop.lat])
        .setPopup(new maplibregl.Popup({ offset: 10 }).setText(stop.name || 'Parada'))
        .addTo(map)
      stopMarkersRef.current.push(marker)
    }
    return () => {
      for (const marker of stopMarkersRef.current) marker.remove()
      stopMarkersRef.current = []
    }
  }, [stops, nearestStop])

  // Real street-network ETA: user walking to the nearest stop vs. the nearest
  // bus driving there along roads — replaces the old straight-line guess.
  // Throttled so live position updates (every few seconds via SSE) don't spam
  // OSRM's free demo server past its ~1 req/sec fair-use limit.
  useEffect(() => {
    if (!userLocation || !nearestStop || !nearestBus) {
      setRouteEta(null)
      return
    }
    const elapsed = Date.now() - lastRouteFetchRef.current
    const delay = Math.max(0, ROUTE_ETA_THROTTLE_MS - elapsed)
    let cancelled = false
    const timer = setTimeout(async () => {
      lastRouteFetchRef.current = Date.now()
      const [walkMinutes, driveMinutes] = await Promise.all([
        fetchRouteMinutes('foot', [userLocation.lon, userLocation.lat], [nearestStop.lon, nearestStop.lat]),
        fetchRouteMinutes('car', [nearestBus.position.longitude, nearestBus.position.latitude], [nearestStop.lon, nearestStop.lat]),
      ])
      if (cancelled || walkMinutes === null || driveMinutes === null) return
      setRouteEta({ stopName: nearestStop.name || 'parada mais próxima', walkMinutes, driveMinutes })
    }, delay)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [userLocation, nearestStop, nearestBus])

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
            <div className="flex items-center gap-1.5">
              <div className="rounded-full bg-card/90 px-3 py-1.5 text-xs font-medium shadow-sm backdrop-blur">
                {MODE_LABEL[selectedLine.mode]} {selectedLine.code} — {vehicleCount} {vehicleCount === 1 ? 'veículo' : 'veículos'} em tempo real
              </div>
              {locatingUser && (
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-card/90 shadow-sm backdrop-blur" title="Obtendo sua localização">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                </div>
              )}
            </div>

            {directions.length > 1 && (
              <div className="flex gap-1.5">
                {directions.map(d => (
                  <button
                    key={d.direction_id}
                    onClick={() => setSelectedDirection(d.direction_id)}
                    className={cn(
                      'rounded-full px-2.5 py-1 text-[11px] font-medium shadow-sm backdrop-blur transition-colors',
                      selectedDirection === d.direction_id
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-card/90 text-muted-foreground hover:text-foreground',
                    )}
                  >
                    → {d.headsign || `Sentido ${d.direction_id}`}
                  </button>
                ))}
              </div>
            )}

            {locationError && (
              <div className="max-w-72 rounded-[10px] bg-destructive/90 px-3 py-2 text-xs text-destructive-foreground shadow-sm backdrop-blur">
                {locationError}
              </div>
            )}

            {nearestBus && (
              <div className="rounded-[10px] bg-card/90 px-3 py-2 text-xs shadow-sm backdrop-blur">
                {routeEta ? (
                  <>
                    <div>
                      <span className="font-medium">Parada mais próxima:</span> {routeEta.stopName}
                    </div>
                    <div>
                      A pé: ~{Math.round(routeEta.walkMinutes)} min — ônibus chega lá em ~{Math.round(routeEta.driveMinutes)} min
                    </div>
                    <span className="text-muted-foreground">(rota real por ruas, sem trânsito ao vivo)</span>
                  </>
                ) : nearestStop ? (
                  <span className="text-muted-foreground">Calculando rota até a parada mais próxima…</span>
                ) : (
                  <>
                    <span className="font-medium">Ônibus mais próximo:</span>{' '}
                    {nearestBus.distanceKm.toFixed(1)} km — ~
                    {Math.round(etaMinutes(nearestBus.distanceKm, nearestBus.position.speed_kmh))} min
                    <span className="text-muted-foreground"> (linha reta — sem paradas cadastradas para esta linha)</span>
                  </>
                )}
              </div>
            )}

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
