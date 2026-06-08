export interface Station {
  id: string
  name: string
  slug: string
  [key: string]: unknown
}

export interface Line {
  id: string
  name: string
  shortName?: string
  color?: string
  [key: string]: unknown
}

export interface LiveTrip {
  stationId: string
  lineId: string
  direction: 'inbound' | 'outbound'
  [key: string]: unknown
}
