import { useEffect, useState } from 'react'
import { X, ArrowRight, ArrowLeft, Clock } from 'lucide-react'
import type { Line, LiveTrip, Station } from '../types'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

function getStationLineIds(station: Station): string[] {
  if (Array.isArray(station.lines)) {
    return (station.lines as Array<{ id: string } | string>).map(l =>
      typeof l === 'string' ? l : l.id
    )
  }
  if (typeof station.lineId === 'string') return [station.lineId]
  return []
}

function formatTrip(trip: LiveTrip): string {
  const t = trip as Record<string, unknown>
  if (typeof t.estimatedTime === 'string') return t.estimatedTime
  if (typeof t.estimatedArrival === 'string') return t.estimatedArrival
  if (typeof t.time === 'string') return t.time
  if (typeof t.nextDeparture === 'string') return t.nextDeparture
  return '—'
}

interface LineTripState {
  lineId: string
  lineName: string
  lineColor?: string
  inbound?: LiveTrip
  outbound?: LiveTrip
  loading: boolean
  error?: string
}

interface Props {
  station: Station
  selectedLineId: string
  lines: Line[]
  onClose: () => void
}

export function LiveTripPanel({ station, selectedLineId, lines, onClose }: Props) {
  const [tripStates, setTripStates] = useState<LineTripState[]>([])

  useEffect(() => {
    const stationLineIds = getStationLineIds(station)
    const lineIds = stationLineIds.length > 0 ? stationLineIds : [selectedLineId]

    const initial: LineTripState[] = lineIds.map(id => {
      const line = lines.find(l => l.id === id)
      return {
        lineId: id,
        lineName: line?.name ?? id,
        lineColor: line?.color as string | undefined,
        loading: true,
      }
    })
    setTripStates(initial)

    lineIds.forEach((lineId, idx) => {
      const params = (dir: string) =>
        new URLSearchParams({ stationId: station.id, lineId, direction: dir }).toString()

      Promise.all([
        fetch(`${GATEWAY}/fn/trains/live?${params('inbound')}`).then(r => r.ok ? r.json() : null),
        fetch(`${GATEWAY}/fn/trains/live?${params('outbound')}`).then(r => r.ok ? r.json() : null),
      ]).then(([inbound, outbound]) => {
        setTripStates(prev =>
          prev.map((s, i) =>
            i === idx ? { ...s, loading: false, inbound: inbound ?? undefined, outbound: outbound ?? undefined } : s
          )
        )
      }).catch(() => {
        setTripStates(prev =>
          prev.map((s, i) =>
            i === idx ? { ...s, loading: false, error: 'Failed to load' } : s
          )
        )
      })
    })
  }, [station.id, selectedLineId, lines])

  return (
    <div className="w-72 shrink-0 rounded-lg border bg-card p-4 flex flex-col gap-4">
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-semibold text-base leading-tight">{station.name}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">{station.slug as string}</p>
        </div>
        <button
          onClick={onClose}
          className="rounded-md p-1 hover:bg-accent transition-colors"
          aria-label="Close"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-col gap-3">
        {tripStates.map(state => (
          <div key={state.lineId} className="rounded-md border p-3 flex flex-col gap-2">
            <div className="flex items-center gap-2">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full shrink-0"
                style={{ backgroundColor: state.lineColor ?? '#6B7280' }}
              />
              <span className="text-sm font-medium">{state.lineName}</span>
            </div>

            {state.loading ? (
              <p className="text-xs text-muted-foreground animate-pulse">Loading...</p>
            ) : state.error ? (
              <p className="text-xs text-destructive">{state.error}</p>
            ) : (
              <div className="flex flex-col gap-1.5">
                <TripRow
                  direction="inbound"
                  trip={state.inbound}
                />
                <TripRow
                  direction="outbound"
                  trip={state.outbound}
                />
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

function TripRow({ direction, trip }: { direction: string; trip?: LiveTrip }) {
  const Icon = direction === 'inbound' ? ArrowRight : ArrowLeft
  return (
    <div className="flex items-center gap-2 text-xs">
      <Icon className="h-3 w-3 text-muted-foreground shrink-0" />
      <span className="capitalize text-muted-foreground">{direction}</span>
      {trip ? (
        <span className="ml-auto flex items-center gap-1 font-medium tabular-nums">
          <Clock className="h-3 w-3 text-muted-foreground" />
          {formatTrip(trip)}
        </span>
      ) : (
        <span className="ml-auto text-muted-foreground">—</span>
      )}
    </div>
  )
}
