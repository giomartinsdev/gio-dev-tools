import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { Skeleton } from 'boneyard-js/react'
import { appsNav } from '@/nav'
import { LivePulse } from '@/components/LivePulse'
import { useHomeSummary } from './useHomeSummary'

const currency = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

function greeting() {
  const h = new Date().getHours()
  if (h < 5) return 'Boa madrugada'
  if (h < 12) return 'Bom dia'
  if (h < 18) return 'Boa tarde'
  return 'Boa noite'
}

export default function HomeScreen() {
  const { summary, activity, loading } = useHomeSummary()
  const [clock, setClock] = useState(() => new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' }))

  useEffect(() => {
    const id = setInterval(() => setClock(new Date().toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })), 15000)
    return () => clearInterval(id)
  }, [])

  function metricFor(path: string): { value: string; label: string } {
    if (!summary) return { value: '—', label: '' }
    switch (path) {
      case '/finance':
        return summary.finance
          ? { value: currency.format(summary.finance.balance), label: 'saldo do mês' }
          : { value: '—', label: 'indisponível' }
      case '/portfolio':
        return summary.portfolio
          ? {
              value: summary.portfolio.changePct === null ? `${summary.portfolio.count}` : `${summary.portfolio.changePct >= 0 ? '+' : ''}${summary.portfolio.changePct.toFixed(1)}%`,
              label: summary.portfolio.changePct === null ? 'ativos' : 'variação média',
            }
          : { value: '—', label: 'indisponível' }
      case '/whatsapp':
        return summary.whatsapp ? { value: `${summary.whatsapp.chatCount}`, label: 'conversas' } : { value: '—', label: 'indisponível' }
      case '/sports-data':
        return summary.sportsData ? { value: `${summary.sportsData.valueBetCount}`, label: 'value bets' } : { value: '—', label: 'indisponível' }
      case '/settings':
        return { value: summary.settingsCount === null ? '—' : `${summary.settingsCount}`, label: 'serviços cadastrados' }
      default:
        return { value: '—', label: '' }
    }
  }

  return (
    <div className="mx-auto w-full max-w-[1680px] px-6 py-8 md:px-10">
      <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-balance">
            {greeting()}, Gio <span className="font-mono text-muted-foreground">{clock}</span>
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">5 apps · resumo atualizado agora</p>
        </div>
      </div>

      <SectionHeader title="Apps" />
      <div className="grid grid-cols-1 gap-3.5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        {appsNav.map(item => {
          const m = metricFor(item.path)
          return (
            <Link
              key={item.path}
              to={item.path}
              className="group flex flex-col gap-3 rounded-[14px] border bg-card p-4 shadow-[var(--shadow-card)] transition-transform hover:-translate-y-0.5"
            >
              <div className="flex items-center justify-between">
                <div className="flex h-8 w-8 items-center justify-center rounded-[9px] border bg-muted">
                  <item.icon className="h-4 w-4 text-foreground/80" />
                </div>
                {item.live ? (
                  <span className="flex items-center gap-1 text-[10.5px] font-semibold text-muted-foreground">
                    <LivePulse />
                    live
                  </span>
                ) : (
                  <span className="text-[10.5px] font-semibold text-muted-foreground">config</span>
                )}
              </div>
              <div>
                <div className="text-[14.5px] font-semibold tracking-tight">{item.label}</div>
                <div className="-mt-0.5 text-xs text-muted-foreground">{item.description}</div>
              </div>
              <div className="flex items-baseline justify-between border-t pt-2.5">
                <div>
                  <div className="font-mono text-lg font-semibold tabular-nums">{loading ? '···' : m.value}</div>
                  <div className="text-[10.5px] uppercase tracking-wide text-muted-foreground">{m.label}</div>
                </div>
              </div>
            </Link>
          )
        })}
      </div>

      <SectionHeader title="Resumo" />
      <Skeleton name="home-kpis" loading={loading}>
        <div className="grid grid-cols-2 gap-0 rounded-[14px] border bg-card p-5 shadow-[var(--shadow-card)] sm:grid-cols-4">
          <Kpi label="Value bets hoje" value={summary?.sportsData ? `${summary.sportsData.valueBetCount}` : '—'} first />
          <Kpi label="Conversas no WhatsApp" value={summary?.whatsapp ? `${summary.whatsapp.chatCount}` : '—'} />
          <Kpi label="Lançamentos no Finance" value={summary?.finance ? `${summary.finance.count}` : '—'} />
          <Kpi label="Serviços conectados" value={summary?.settingsCount !== null && summary?.settingsCount !== undefined ? `${summary.settingsCount}` : '—'} />
        </div>
      </Skeleton>

      <SectionHeader title="Atividade recente" />
      <Skeleton name="home-activity" loading={loading}>
        <div className="overflow-x-auto rounded-[14px] border bg-card shadow-[var(--shadow-card)]">
          <table className="w-full min-w-[560px] border-collapse">
            <thead>
              <tr>
                <Th>Horário</Th>
                <Th>App</Th>
                <Th>Evento</Th>
              </tr>
            </thead>
            <tbody>
              {activity.length === 0 ? (
                <tr>
                  <td colSpan={3} className="px-4 py-6 text-center text-sm text-muted-foreground">
                    Sem atividade recente pra mostrar.
                  </td>
                </tr>
              ) : (
                activity.map((item, i) => (
                  <tr key={i} className="border-t hover:bg-muted/50">
                    <td className="whitespace-nowrap px-4 py-2.5 font-mono text-xs text-muted-foreground">{item.time}</td>
                    <td className="px-4 py-2.5">
                      <span className="inline-flex items-center rounded-full border bg-muted px-2 py-0.5 text-[11px] font-semibold">
                        {item.moduleLabel}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-[12.5px]">{item.event}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Skeleton>
    </div>
  )
}

function SectionHeader({ title }: { title: string }) {
  return (
    <div className="mb-3 mt-8 flex items-baseline justify-between first:mt-0">
      <h2 className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</h2>
    </div>
  )
}

function Kpi({ label, value, first }: { label: string; value: string; first?: boolean }) {
  return (
    <div className={`flex flex-col-reverse gap-1 px-5 first:pl-0 first:border-l-0 border-l ${first ? 'border-l-0 pl-0' : ''}`}>
      <div className="text-xs text-muted-foreground">{label}</div>
      <div className="font-mono text-[22px] font-semibold tracking-tight tabular-nums">{value}</div>
    </div>
  )
}

function Th({ children }: { children: React.ReactNode }) {
  return (
    <th className="border-b px-4 py-3 text-left text-[10.5px] font-semibold uppercase tracking-wide text-muted-foreground">
      {children}
    </th>
  )
}
