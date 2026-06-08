import { useEffect, useState } from 'react'
import { X, ArrowRight, ArrowLeft, Clock } from 'lucide-react'
import type { Line, LiveTrip, Station } from '../types'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

function formatTrip(trip: LiveTrip): string {
  const t = trip as Record<string, unknown>
  for (const key of ['estimatedTime', 'estimatedArrival', 'time', 'nextDeparture', 'horario', 'hora']) {
    if (typeof t[key] === 'string') return t[key] as string
  }
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
  lineIds: string[]  // real line IDs for this station (no __unknown__)
  lines: Line[]
  onClose: () => void
}

export function LiveTripPanel({ station, lineIds, lines, onClose }: Props) {
  const [tripStates, setTripStates] = useState<LineTripState[]>([])

  useEffect(() => {
    if (lineIds.length === 0) {
      setTripStates([])
      return
    }

    const initial: LineTripState[] = lineIds.map(id => {
      const line = lines.find(l => l.id === id)
      return { lineId: id, lineName: line?.name ?? id, lineColor: line?.color as string | undefined, loading: true }
    })
    setTripStates(initial)

    lineIds.forEach((lineId, idx) => {
      const params = (dir: string) =>
        new URLSearchParams({ stationId: station.id, lineId, direction: dir }).toString()

      Promise.all([
        fetch(`${GATEWAY}/fn/trains/live?${params('inbound')}`).then(r => r.ok ? r.json() : null).catch(() => null),
        fetch(`${GATEWAY}/fn/trains/live?${params('outbound')}`).then(r => r.ok ? r.json() : null).catch(() => null),
      ]).then(([inbound, outbound]) => {
        setTripStates(prev =>
          prev.map((s, i) => i === idx ? { ...s, loading: false, inbound: inbound ?? undefined, outbound: outbound ?? undefined } : s)
        )
      })
    })
  }, [station.id, lineIds.join(','), lines])

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

      {lineIds.length === 0 ? (
        <p className="text-sm text-muted-foreground">Linha não identificada para esta estação.</p>
      ) : (
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
                <p className="text-xs text-muted-foreground animate-pulse">Carregando...</p>
              ) : (
                <div className="flex flex-col gap-1.5">
                  <TripRow direction="inbound" trip={state.inbound} />
                  <TripRow direction="outbound" trip={state.outbound} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
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
