import { useEffect, useMemo, useState } from 'react'
import { Train } from 'lucide-react'
import { StationMap, buildStationLineMap } from './components/StationMap'
import { LiveTripPanel } from './components/LiveTripPanel'
import type { Line, Station } from './types'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

export const trainsMeta = {
  id: 'trains' as const,
  label: 'Trains',
  description: 'Rio de Janeiro urban rail',
  icon: Train,
}

export function TrainsModule() {
  const [stations, setStations] = useState<Station[]>([])
  const [lines, setLines] = useState<Line[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedStation, setSelectedStation] = useState<Station | null>(null)

  useEffect(() => {
    Promise.all([
      fetch(`${GATEWAY}/fn/trains/stations`).then(r => { if (!r.ok) throw new Error('Falha ao carregar estações'); return r.json() }),
      fetch(`${GATEWAY}/fn/trains/lines`).then(r => { if (!r.ok) throw new Error('Falha ao carregar linhas'); return r.json() }),
    ])
      .then(([stationsData, linesData]) => {
        setStations(Array.isArray(stationsData) ? stationsData : [])
        setLines(Array.isArray(linesData) ? linesData : [])
        setLoading(false)
      })
      .catch(err => {
        setError(err.message ?? 'Falha ao carregar dados')
        setLoading(false)
      })
  }, [])

  const stationLineMap = useMemo(
    () => buildStationLineMap(stations, lines),
    [stations, lines]
  )

  const selectedLineIds = useMemo(() => {
    if (!selectedStation) return []
    return (stationLineMap.get(selectedStation.id) ?? []).filter(id => id !== '__unknown__')
  }, [selectedStation, stationLineMap])

  return (
    <div className="flex gap-4 h-full">
      <div className="flex-1 min-w-0">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Train className="h-4 w-4 animate-pulse" />
            Carregando mapa de estações...
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <StationMap
            stations={stations}
            lines={lines}
            stationLineMap={stationLineMap}
            selectedId={selectedStation?.id}
            onSelect={station => setSelectedStation(station)}
          />
        )}
      </div>

      {selectedStation && (
        <LiveTripPanel
          station={selectedStation}
          lineIds={selectedLineIds}
          lines={lines}
          onClose={() => setSelectedStation(null)}
        />
      )}
    </div>
  )
}
