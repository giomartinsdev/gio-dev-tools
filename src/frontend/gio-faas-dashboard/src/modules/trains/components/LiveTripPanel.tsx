import { useEffect, useState } from 'react'
import { X, ArrowRight, ArrowLeft, Clock, CalendarDays } from 'lucide-react'
import type { Line, LiveTrip, Station } from '../types'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

function todayStr() {
  return new Date().toISOString().slice(0, 10)
}

function nowTimeStr() {
  return new Date().toTimeString().slice(0, 5)
}

function formatTrip(trip: LiveTrip): string {
  const t = trip as Record<string, unknown>
  for (const key of ['estimatedTime', 'estimatedArrival', 'time', 'nextDeparture', 'horario', 'hora']) {
    if (typeof t[key] === 'string') return t[key] as string
  }
  return '—'
}

interface TripResult {
  data?: LiveTrip
  noService?: string  // message from NO_SERVICE
}

interface LineTripState {
  lineId: string
  lineName: string
  lineColor?: string
  inbound?: TripResult
  outbound?: TripResult
  loading: boolean
}

interface Props {
  station: Station
  lineIds: string[]
  lines: Line[]
  onClose: () => void
}

export function LiveTripPanel({ station, lineIds, lines, onClose }: Props) {
  const [useSchedule, setUseSchedule] = useState(false)
  const [date, setDate] = useState(todayStr)
  const [time, setTime] = useState(nowTimeStr)
  const [tripStates, setTripStates] = useState<LineTripState[]>([])

  async function fetchDirection(lineId: string, direction: string): Promise<TripResult> {
    const params = new URLSearchParams({ stationId: station.id, lineId, direction })
    if (useSchedule) {
      params.set('date', date)
      params.set('time', time)
    }
    try {
      const r = await fetch(`${GATEWAY}/fn/trains/live?${params}`)
      const json = await r.json()
      if (!r.ok) {
        return { noService: json.message ?? 'Sem serviço' }
      }
      return { data: json }
    } catch {
      return { noService: 'Falha na requisição' }
    }
  }

  useEffect(() => {
    if (lineIds.length === 0) { setTripStates([]); return }

    const initial: LineTripState[] = lineIds.map(id => {
      const line = lines.find(l => l.id === id)
      return { lineId: id, lineName: line?.name ?? id, lineColor: line?.color as string | undefined, loading: true }
    })
    setTripStates(initial)

    lineIds.forEach((lineId, idx) => {
      Promise.all([
        fetchDirection(lineId, 'inbound'),
        fetchDirection(lineId, 'outbound'),
      ]).then(([inbound, outbound]) => {
        setTripStates(prev =>
          prev.map((s, i) => i === idx ? { ...s, loading: false, inbound, outbound } : s)
        )
      })
    })
  }, [station.id, lineIds.join(','), useSchedule, date, time])

  return (
    <div className="w-72 shrink-0 rounded-lg border bg-card p-4 flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <h2 className="font-semibold text-base leading-tight">{station.name}</h2>
          <p className="text-xs text-muted-foreground mt-0.5">{station.slug as string}</p>
        </div>
        <button onClick={onClose} className="rounded-md p-1 hover:bg-accent transition-colors" aria-label="Close">
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Schedule picker */}
      <div className="flex flex-col gap-2">
        <label className="flex items-center gap-2 text-xs cursor-pointer select-none">
          <input
            type="checkbox"
            checked={useSchedule}
            onChange={e => setUseSchedule(e.target.checked)}
            className="rounded"
          />
          <CalendarDays className="h-3.5 w-3.5 text-muted-foreground" />
          Consultar por data e hora
        </label>

        {useSchedule && (
          <div className="flex gap-2">
            <input
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
              className="flex-1 rounded-md border bg-background px-2 py-1 text-xs"
            />
            <input
              type="time"
              value={time}
              onChange={e => setTime(e.target.value)}
              className="w-24 rounded-md border bg-background px-2 py-1 text-xs"
            />
          </div>
        )}
      </div>

      {/* Trip results */}
      {lineIds.length === 0 ? (
        <p className="text-sm text-muted-foreground">Linha não identificada para esta estação.</p>
      ) : (
        <div className="flex flex-col gap-3">
          {tripStates.map(state => {
            const rawColor = state.lineColor
            const color = rawColor
              ? (rawColor.startsWith('#') ? rawColor : `#${rawColor}`)
              : '#6B7280'
            return (
              <div key={state.lineId} className="rounded-md border p-3 flex flex-col gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-block h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
                  <span className="text-sm font-medium">{state.lineName}</span>
                </div>

                {state.loading ? (
                  <p className="text-xs text-muted-foreground animate-pulse">Carregando...</p>
                ) : (
                  <div className="flex flex-col gap-1.5">
                    <TripRow direction="inbound" result={state.inbound} />
                    <TripRow direction="outbound" result={state.outbound} />
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

function TripRow({ direction, result }: { direction: string; result?: TripResult }) {
  const Icon = direction === 'inbound' ? ArrowRight : ArrowLeft

  return (
    <div className="flex flex-col gap-0.5">
      <div className="flex items-center gap-2 text-xs">
        <Icon className="h-3 w-3 text-muted-foreground shrink-0" />
        <span className="capitalize text-muted-foreground">{direction}</span>
        {result?.data ? (
          <span className="ml-auto flex items-center gap-1 font-medium tabular-nums">
            <Clock className="h-3 w-3 text-muted-foreground" />
            {formatTrip(result.data)}
          </span>
        ) : (
          <span className="ml-auto text-muted-foreground">—</span>
        )}
      </div>
      {result?.noService && (
        <p className="text-xs text-muted-foreground pl-5 italic">{result.noService}</p>
      )}
    </div>
  )
}
