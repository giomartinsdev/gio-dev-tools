import { Line, Station } from '../types'

const FALLBACK_COLORS = [
  '#8B5CF6', '#3B82F6', '#10B981', '#F59E0B',
  '#EF4444', '#EC4899', '#06B6D4', '#84CC16',
]

const LINE_HEIGHT = 90
const STATION_RADIUS = 7
const PAD_X = 60
const PAD_Y = 50
const STATION_SPACING = 80

function getStationLineIds(station: Station): string[] {
  if (Array.isArray(station.lines)) {
    return (station.lines as Array<{ id: string } | string>).map(l =>
      typeof l === 'string' ? l : l.id
    )
  }
  if (typeof station.lineId === 'string') return [station.lineId]
  return []
}

function groupStationsByLine(stations: Station[], lines: Line[]): Array<{ line: Line; stations: Station[] }> {
  const groups = new Map<string, Station[]>()
  lines.forEach(l => groups.set(l.id, []))

  stations.forEach(station => {
    const lineIds = getStationLineIds(station)
    if (lineIds.length === 0) {
      if (!groups.has('__unknown__')) groups.set('__unknown__', [])
      groups.get('__unknown__')!.push(station)
    } else {
      lineIds.forEach(id => {
        if (!groups.has(id)) groups.set(id, [])
        groups.get(id)!.push(station)
      })
    }
  })

  const result: Array<{ line: Line; stations: Station[] }> = []
  lines.forEach(line => {
    const sts = groups.get(line.id) ?? []
    if (sts.length > 0) result.push({ line, stations: sts })
  })

  const unknown = groups.get('__unknown__')
  if (unknown && unknown.length > 0) {
    result.push({ line: { id: '__unknown__', name: 'Stations' }, stations: unknown })
  }

  return result
}

interface Props {
  stations: Station[]
  lines: Line[]
  selectedId?: string
  onSelect: (station: Station, lineId: string) => void
}

export function StationMap({ stations, lines, selectedId, onSelect }: Props) {
  const groups = groupStationsByLine(stations, lines)

  if (groups.length === 0) {
    return <p className="text-sm text-muted-foreground">No stations found.</p>
  }

  const maxStations = Math.max(...groups.map(g => g.stations.length))
  const svgWidth = PAD_X * 2 + maxStations * STATION_SPACING
  const svgHeight = PAD_Y * 2 + groups.length * LINE_HEIGHT

  return (
    <div className="overflow-x-auto">
      <svg width={svgWidth} height={svgHeight} className="select-none">
        {groups.map(({ line, stations: lineStations }, lineIdx) => {
          const y = PAD_Y + lineIdx * LINE_HEIGHT
          const color = (line.color as string | undefined)
            ?? FALLBACK_COLORS[lineIdx % FALLBACK_COLORS.length]

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

              {/* Line label */}
              <text
                x={PAD_X - 12}
                y={y + 4}
                textAnchor="end"
                fontSize={11}
                fill={color}
                fontWeight={600}
              >
                {line.name}
              </text>

              {/* Station nodes */}
              {lineStations.map((station, stIdx) => {
                const x = PAD_X + stIdx * STATION_SPACING
                const isSelected = station.id === selectedId

                return (
                  <g
                    key={station.id + line.id}
                    onClick={() => onSelect(station, line.id)}
                    className="cursor-pointer"
                  >
                    <circle
                      cx={x}
                      cy={y}
                      r={STATION_RADIUS + 4}
                      fill="transparent"
                    />
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
