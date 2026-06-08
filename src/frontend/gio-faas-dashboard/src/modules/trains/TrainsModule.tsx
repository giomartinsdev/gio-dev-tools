import { useEffect, useState } from 'react'
import { Train } from 'lucide-react'
import { StationMap } from './components/StationMap'
import { LiveTripPanel } from './components/LiveTripPanel'
import { Line, Station } from './types'

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
  const [selectedLineId, setSelectedLineId] = useState<string>('')

  useEffect(() => {
    Promise.all([
      fetch(`${GATEWAY}/fn/trains/stations`).then(r => {
        if (!r.ok) throw new Error('Failed to load stations')
        return r.json()
      }),
      fetch(`${GATEWAY}/fn/trains/lines`).then(r => {
        if (!r.ok) throw new Error('Failed to load lines')
        return r.json()
      }),
    ])
      .then(([stationsData, linesData]) => {
        setStations(Array.isArray(stationsData) ? stationsData : [])
        setLines(Array.isArray(linesData) ? linesData : [])
        setLoading(false)
      })
      .catch(err => {
        setError(err.message ?? 'Failed to load train data')
        setLoading(false)
      })
  }, [])

  function handleSelect(station: Station, lineId: string) {
    setSelectedStation(station)
    setSelectedLineId(lineId)
  }

  return (
    <div className="flex gap-4 h-full">
      <div className="flex-1 min-w-0">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Train className="h-4 w-4 animate-pulse" />
            Loading station map...
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">{error}</p>
        ) : (
          <StationMap
            stations={stations}
            lines={lines}
            selectedId={selectedStation?.id}
            onSelect={handleSelect}
          />
        )}
      </div>

      {selectedStation && (
        <LiveTripPanel
          station={selectedStation}
          selectedLineId={selectedLineId}
          lines={lines}
          onClose={() => setSelectedStation(null)}
        />
      )}
    </div>
  )
}
