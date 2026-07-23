import { useState, useEffect, useCallback, useMemo } from 'react'
import { Trophy, Loader2, RefreshCw, Database, TrendingUp } from 'lucide-react'
import { cn } from '@/lib/utils'
import { ValueBetsReportModule } from '@/modules/value-bets-report/ValueBetsReportModule'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

interface OverviewRow {
  table: string
  rows: number
  most_recent: string | null
}

interface Match {
  match_id: string
  status: string
  home_score: number | null
  away_score: number | null
  minute: number | null
  kickoff_at: string | null
  venue: string | null
  home_team_name: string | null
  away_team_name: string | null
}

interface ValueBet {
  match_id: string
  market: string
  outcome: string
  model_probability: string
  bookmaker: string
  best_odds: string
  implied_probability: string
  edge: string
  detected_at: string
  kickoff_at: string | null
  status: string | null
  home_team_name: string | null
  away_team_name: string | null
}

interface MatchValueBets {
  match_id: string
  home_team_name: string | null
  away_team_name: string | null
  kickoff_at: string | null
  status: string | null
  bets: ValueBet[]
}

function groupValueBetsByMatch(valueBets: ValueBet[]): MatchValueBets[] {
  const groups = new Map<string, MatchValueBets>()
  for (const vb of valueBets) {
    let group = groups.get(vb.match_id)
    if (!group) {
      group = {
        match_id: vb.match_id,
        home_team_name: vb.home_team_name,
        away_team_name: vb.away_team_name,
        kickoff_at: vb.kickoff_at,
        status: vb.status,
        bets: [],
      }
      groups.set(vb.match_id, group)
    }
    group.bets.push(vb)
  }
  // Backend already orders by kickoff_at asc then edge desc, insertion
  // order into the Map preserves that — no re-sort needed here.
  return [...groups.values()]
}

interface OutcomeSummary {
  total: number
  won: number
  lost: number
  win_rate: number | null
}

interface Insight {
  id: string
  match_id: string
  market: string
  recommendation: string
  confidence: string
  rationale: string
  model: string
  generated_at: string
  home_team_name: string | null
  away_team_name: string | null
}

const STATUS_LABELS: Record<string, { label: string; className: string }> = {
  notstarted: { label: 'Agendado', className: 'text-muted-foreground' },
  inprogress: { label: 'Ao vivo', className: 'text-success' },
  '1st_half': { label: '1º tempo', className: 'text-success' },
  '2nd_half': { label: '2º tempo', className: 'text-success' },
  halftime: { label: 'Intervalo', className: 'text-warning' },
  finished: { label: 'Encerrado', className: 'text-muted-foreground' },
  postponed: { label: 'Adiado', className: 'text-destructive' },
  cancelled: { label: 'Cancelado', className: 'text-destructive' },
}

function statusBadge(status: string | null) {
  if (!status) return { label: '—', className: 'text-muted-foreground/40' }
  return STATUS_LABELS[status] ?? { label: status, className: 'text-muted-foreground' }
}

// Market/outcome codes are bzzoiro's own vocabulary (see value_bet_detector.py's
// _MARKET_MAP and value_bet_outcome_resolver.py's _did_outcome_hit) — translated
// here purely for display, the API keeps sending the raw codes.
const MARKET_LABELS: Record<string, string> = {
  '1x2': 'Resultado final',
  match_result: 'Resultado final',
  over_under_15: 'Mais/menos 1.5 gols',
  over_under_25: 'Mais/menos 2.5 gols',
  over_under_35: 'Mais/menos 3.5 gols',
  over_under: 'Mais/menos gols',
  btts: 'Ambos marcam (BTTS)',
}

const OUTCOME_LABELS: Record<string, string> = {
  HOME: 'Casa',
  DRAW: 'Empate',
  AWAY: 'Fora',
  over: 'Mais (over)',
  under: 'Menos (under)',
  yes: 'Sim',
  no: 'Não',
}

const FAVORITE_LETTER_LABELS: Record<string, string> = { H: 'Casa', D: 'Empate', A: 'Fora' }

function translateMarket(market: string) {
  return MARKET_LABELS[market] ?? market
}

function translateOutcome(outcome: string) {
  return OUTCOME_LABELS[outcome] ?? outcome
}

function translateRecommendation(recommendation: string) {
  const [key, value] = recommendation.split(':')
  if (key === 'favorite' && value && FAVORITE_LETTER_LABELS[value]) {
    return `Favorito: ${FAVORITE_LETTER_LABELS[value]}`
  }
  return recommendation
}

function teamNames(homeName: string | null, awayName: string | null) {
  return `${homeName ?? '?'} vs ${awayName ?? '?'}`
}

function formatDateTime(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('pt-BR', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function timeAgo(iso: string | null) {
  if (!iso) return 'sem dados'
  const diffMs = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diffMs / 60000)
  if (mins < 1) return 'agora'
  if (mins < 60) return `${mins}min atrás`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h atrás`
  return `${Math.floor(hours / 24)}d atrás`
}

function formatPct(value: number | null) {
  if (value === null) return '—'
  return `${(value * 100).toFixed(1)}%`
}

function formatEdge(value: string) {
  const n = parseFloat(value)
  return `${(n * 100).toFixed(1)}%`
}

export function DomainInsightsModule() {
  const [overview, setOverview] = useState<OverviewRow[]>([])
  const [matches, setMatches] = useState<Match[]>([])
  const [valueBets, setValueBets] = useState<ValueBet[]>([])
  const [summary, setSummary] = useState<OutcomeSummary | null>(null)
  const [insights, setInsights] = useState<Insight[]>([])
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const fetchAll = useCallback(async () => {
    const [ov, m, vb, s, ins] = await Promise.all([
      fetch(`${GATEWAY}/domain-data-insights/overview`).then(r => r.ok ? r.json() : []),
      fetch(`${GATEWAY}/domain-data-insights/matches?limit=20`).then(r => r.ok ? r.json() : []),
      fetch(`${GATEWAY}/domain-data-insights/value-bets?limit=200`).then(r => r.ok ? r.json() : []),
      fetch(`${GATEWAY}/domain-data-insights/value-bets/outcomes/summary`).then(r => r.ok ? r.json() : null),
      fetch(`${GATEWAY}/domain-data-insights/insights?limit=20`).then(r => r.ok ? r.json() : []),
    ])
    setOverview(ov)
    setMatches(m)
    setValueBets(vb)
    setSummary(s)
    setInsights(ins)
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchAll().finally(() => setLoading(false))
  }, [fetchAll])

  async function refresh() {
    setRefreshing(true)
    try { await fetchAll() } finally { setRefreshing(false) }
  }

  const winRate = summary?.win_rate ?? null
  const valueBetsByMatch = useMemo(() => groupValueBetsByMatch(valueBets), [valueBets])

  return (
    <div className="flex flex-col gap-6">

      {/* Header + win rate card */}
      <div className="rounded-[14px] border bg-card shadow-[var(--shadow-card)] px-5 py-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Value bets resolvidos</p>
          <div className="flex items-baseline gap-2 mt-0.5">
            <p className="text-2xl font-bold tabular-nums text-foreground">{formatPct(winRate)}</p>
            <p className="text-xs text-muted-foreground">
              {summary ? `${summary.won}/${summary.total} ganhos` : '—'}
            </p>
          </div>
        </div>
        <button
          onClick={refresh}
          disabled={refreshing}
          className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40"
        >
          {refreshing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          {refreshing ? 'Atualizando…' : 'Atualizar'}
        </button>
      </div>

      {/* Overview grid */}
      <div className="rounded-[14px] border bg-card shadow-[var(--shadow-card)] p-4 flex flex-col gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground flex items-center gap-1.5">
          <Database className="h-3.5 w-3.5" /> bzzoiro_data — visão geral
        </p>
        {loading ? (
          <Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground my-4" />
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2">
            {overview.map(row => (
              <div key={row.table} className="rounded-md border px-2.5 py-2 flex flex-col gap-0.5">
                <span className="text-xs font-medium truncate" title={row.table}>{row.table}</span>
                <span className="text-lg font-bold tabular-nums">{row.rows}</span>
                <span className="text-[10px] text-muted-foreground">{timeAgo(row.most_recent)}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Value bets grouped by match — every row already cleared the edge
          threshold, so this is exactly "every match that makes sense to
          bet on right now", grouped so all of a match's markets show
          together instead of scattered across one long flat table. */}
      <div className="flex flex-col gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground px-1">
          Value bets por partida{valueBetsByMatch.length > 0 && ` (${valueBetsByMatch.length})`}
        </p>
        {loading ? (
          <div className="rounded-[14px] border bg-card shadow-[var(--shadow-card)] py-10">
            <Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" />
          </div>
        ) : valueBetsByMatch.length === 0 ? (
          <div className="rounded-[14px] border bg-card shadow-[var(--shadow-card)] py-8 text-center text-sm text-muted-foreground">
            Nenhum value bet em aberto no momento.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {valueBetsByMatch.map(group => {
              const badge = statusBadge(group.status)
              return (
                <div key={group.match_id} className="rounded-[14px] border bg-card shadow-[var(--shadow-card)] overflow-hidden">
                  <div className="px-4 py-2.5 border-b bg-muted/30 flex items-center justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-medium text-sm truncate">{teamNames(group.home_team_name, group.away_team_name)}</p>
                      <p className="text-xs text-muted-foreground">{formatDateTime(group.kickoff_at)}</p>
                    </div>
                    <span className={cn('text-xs font-medium shrink-0', badge.className)}>{badge.label}</span>
                  </div>
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b bg-muted/20">
                        <Th className="text-xs">Mercado</Th>
                        <Th className="text-xs">Resultado</Th>
                        <Th className="text-xs text-right">Edge</Th>
                        <Th className="text-xs">Casa</Th>
                        <Th className="text-xs text-right">Odds</Th>
                      </tr>
                    </thead>
                    <tbody>
                      {group.bets.map((vb, i) => (
                        <tr key={`${vb.market}-${vb.outcome}-${i}`} className="border-b last:border-0">
                          <Td className="text-xs" title={vb.market}>{translateMarket(vb.market)}</Td>
                          <Td className="text-xs" title={vb.outcome}>{translateOutcome(vb.outcome)}</Td>
                          <Td className="text-right tabular-nums font-semibold text-success">
                            <span className="inline-flex items-center gap-1"><TrendingUp className="h-3.5 w-3.5" />{formatEdge(vb.edge)}</span>
                          </Td>
                          <Td className="text-muted-foreground text-xs">{vb.bookmaker}</Td>
                          <Td className="text-right tabular-nums">{vb.best_odds}</Td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )
            })}
          </div>
        )}
      </div>

      {/* Matches + Insights side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="rounded-[14px] border bg-card shadow-[var(--shadow-card)] overflow-auto">
          <div className="px-4 py-2.5 border-b bg-muted/30">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Partidas recentes</p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <Th>Partida</Th>
                <Th className="w-20 text-center">Placar</Th>
                <Th className="w-24">Status</Th>
                <Th className="w-28">Data</Th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} className="py-10 text-center"><Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" /></td></tr>
              ) : matches.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-sm text-muted-foreground">Nenhuma partida encontrada.</td></tr>
              ) : matches.map(m => {
                const badge = statusBadge(m.status)
                return (
                  <tr key={m.match_id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                    <Td className="font-medium">{teamNames(m.home_team_name, m.away_team_name)}</Td>
                    <Td className="text-center tabular-nums">
                      {m.home_score !== null && m.away_score !== null ? `${m.home_score} - ${m.away_score}` : '—'}
                    </Td>
                    <Td><span className={cn('text-xs font-medium', badge.className)}>{badge.label}</span></Td>
                    <Td className="text-xs text-muted-foreground">{formatDateTime(m.kickoff_at)}</Td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>

        <div className="rounded-[14px] border bg-card shadow-[var(--shadow-card)] overflow-auto">
          <div className="px-4 py-2.5 border-b bg-muted/30">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Insights recentes (ML)</p>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b bg-muted/50">
                <Th>Partida</Th>
                <Th className="w-24">Mercado</Th>
                <Th className="w-24">Favorito</Th>
                <Th className="w-20 text-right">Conf.</Th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={4} className="py-10 text-center"><Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" /></td></tr>
              ) : insights.length === 0 ? (
                <tr><td colSpan={4} className="py-8 text-center text-sm text-muted-foreground">Nenhum insight encontrado.</td></tr>
              ) : insights.map(ins => (
                <tr key={ins.id} className="border-b last:border-0 hover:bg-muted/30 transition-colors">
                  <Td className="font-medium">{teamNames(ins.home_team_name, ins.away_team_name)}</Td>
                  <Td className="text-xs" title={ins.market}>{translateMarket(ins.market)}</Td>
                  <Td className="text-xs">{translateRecommendation(ins.recommendation)}</Td>
                  <Td className="text-right tabular-nums">{(parseFloat(ins.confidence) * 100).toFixed(0)}%</Td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Relatório diário de value bets no WhatsApp — folded in here since
          it's the same domain (bzzoiro value bets), just a delivery channel
          for it rather than a separate top-level app. */}
      <div className="flex flex-col gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground px-1">
          Relatório no WhatsApp
        </p>
        <ValueBetsReportModule />
      </div>
    </div>
  )
}

function Th({ children, className }: { children?: React.ReactNode; className?: string }) {
  return (
    <th className={cn('px-3 py-2.5 text-left text-xs font-semibold uppercase tracking-wide text-muted-foreground', className)}>
      {children}
    </th>
  )
}

function Td({ children, className, title }: { children?: React.ReactNode; className?: string; title?: string }) {
  return <td className={cn('px-3 py-2.5', className)} title={title}>{children}</td>
}

export const domainInsightsMeta = {
  id: 'domain-insights' as const,
  label: 'Sports Data',
  description: 'bzzoiro pipeline — matches, value bets and ML insights',
  icon: Trophy,
}
