import type { Line, Station } from '../types'

const FALLBACK_COLORS = [
  '#8B5CF6', '#3B82F6', '#10B981', '#F59E0B',
  '#EF4444', '#EC4899', '#06B6D4', '#84CC16',
]

const LINE_HEIGHT = 90
const STATION_RADIUS = 7
const PAD_X = 120
const PAD_Y = 50
const STATION_SPACING = 80

function extractLineIds(station: Station): string[] {
  // Try common field names for line association
  for (const key of ['lineId', 'line_id', 'ramalId', 'ramal_id']) {
    if (typeof station[key] === 'string') return [station[key] as string]
  }
  for (const key of ['lines', 'ramais']) {
    const val = station[key]
    if (Array.isArray(val) && val.length > 0) {
      return val.map((l: unknown) =>
        typeof l === 'string' ? l : (l as Record<string, string>)?.id ?? ''
      ).filter(Boolean)
    }
  }
  for (const key of ['line', 'ramal']) {
    const val = station[key]
    if (val && typeof val === 'object') return [(val as Record<string, string>).id ?? ''].filter(Boolean)
    if (typeof val === 'string') return [val]
  }
  return []
}

export function buildStationLineMap(stations: Station[], lines: Line[]): Map<string, string[]> {
  const map = new Map<string, string[]>()

  // Forward: station → lines via station fields
  stations.forEach(s => {
    const ids = extractLineIds(s)
    if (ids.length > 0) map.set(s.id, ids)
  })

  // Reverse: line → stations via line.stations (entry.stationId or entry.station.id or entry.id)
  lines.forEach(line => {
    const val = line['stations']
    if (!Array.isArray(val)) return
    val.forEach((entry: unknown) => {
      const e = entry as Record<string, unknown>
      const stId = (typeof e?.stationId === 'string' ? e.stationId : null)
        ?? (typeof (e?.station as Record<string, unknown>)?.id === 'string' ? (e.station as Record<string, string>).id : null)
        ?? (typeof e?.id === 'string' ? e.id : null)
        ?? ''
      if (!stId) return
      const existing = map.get(stId) ?? []
      if (!existing.includes(line.id)) map.set(stId, [...existing, line.id])
    })
  })

  return map
}

function groupByLine(
  stations: Station[],
  lines: Line[],
  stationLineMap: Map<string, string[]>,
): Array<{ line: Line; stations: Station[] }> {
  const groups = new Map<string, Station[]>(lines.map(l => [l.id, []]))

  stations.forEach(station => {
    const lineIds = stationLineMap.get(station.id) ?? []
    if (lineIds.length === 0) {
      if (!groups.has('__unknown__')) groups.set('__unknown__', [])
      groups.get('__unknown__')!.push(station)
    } else {
      lineIds.forEach(id => {
        if (!groups.has(id)) groups.set(id, [])
        const list = groups.get(id)!
        if (!list.find(s => s.id === station.id)) list.push(station)
      })
    }
  })

  const result: Array<{ line: Line; stations: Station[] }> = []
  lines.forEach(line => {
    const sts = groups.get(line.id) ?? []
    if (sts.length > 0) result.push({ line, stations: sts })
  })

  const unknown = groups.get('__unknown__') ?? []
  if (unknown.length > 0) {
    result.push({ line: { id: '__unknown__', name: 'Stations' }, stations: unknown })
  }

  return result
}

interface Props {
  stations: Station[]
  lines: Line[]
  stationLineMap: Map<string, string[]>
  selectedId?: string
  onSelect: (station: Station, lineId: string) => void
}

export function StationMap({ stations, lines, stationLineMap, selectedId, onSelect }: Props) {
  const groups = groupByLine(stations, lines, stationLineMap)

  if (groups.length === 0) {
    return <p className="text-sm text-muted-foreground">No stations found.</p>
  }

  const maxStations = Math.max(...groups.map(g => g.stations.length))
  const svgWidth = PAD_X + maxStations * STATION_SPACING + 40
  const svgHeight = PAD_Y * 2 + groups.length * LINE_HEIGHT

  return (
    <div className="overflow-x-auto">
      <svg width={svgWidth} height={svgHeight} className="select-none">
        {groups.map(({ line, stations: lineStations }, lineIdx) => {
          const y = PAD_Y + lineIdx * LINE_HEIGHT
          const rawColor = line.color as string | undefined
          const color = rawColor
            ? (rawColor.startsWith('#') ? rawColor : `#${rawColor}`)
            : FALLBACK_COLORS[lineIdx % FALLBACK_COLORS.length]
          const label = (line.shortName as string | undefined) ?? line.name

          return (
            <g key={line.id}>
              {/* Line track */}
              <line
                x1={PAD_X}
                y1={y}
                x2={PAD_X + (lineStations.length - 1) * STATION_SPACING}
                y2={y}
                stroke={color}
                strokeWidth={4}
                strokeLinecap="round"
              />

              {/* Line name label */}
              <text
                x={PAD_X - 12}
                y={y + 4}
                textAnchor="end"
                fontSize={11}
                fill={color}
                fontWeight={600}
              >
                {label}
              </text>

              {lineStations.map((station, stIdx) => {
                const x = PAD_X + stIdx * STATION_SPACING
                const isSelected = station.id === selectedId

                return (
                  <g
                    key={station.id + line.id}
                    onClick={() => onSelect(station, line.id)}
                    className="cursor-pointer"
                  >
                    {/* Invisible larger hit target */}
                    <circle cx={x} cy={y} r={STATION_RADIUS + 6} fill="transparent" />

                    <circle
                      cx={x}
                      cy={y}
                      r={STATION_RADIUS}
                      fill={isSelected ? color : 'white'}
                      stroke={color}
                      strokeWidth={isSelected ? 3 : 2}
                      className="transition-all duration-150"
                    />
                    {isSelected && (
                      <circle
                        cx={x}
                        cy={y}
                        r={STATION_RADIUS + 5}
                        fill="none"
                        stroke={color}
                        strokeWidth={1.5}
                        opacity={0.4}
                      />
                    )}
                    <text
                      x={x}
                      y={y + STATION_RADIUS + 4}
                      textAnchor="start"
                      fontSize={10}
                      fill="currentColor"
                      className="fill-foreground"
                      transform={`rotate(-40, ${x}, ${y + STATION_RADIUS + 4})`}
                      pointerEvents="none"
                    >
                      {station.name}
                    </text>
                  </g>
                )
              })}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
