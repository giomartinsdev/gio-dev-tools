import { useEffect, useState } from 'react'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

export interface ModuleSummary {
  finance: { balance: number; count: number } | null
  portfolio: { count: number; changePct: number | null } | null
  whatsapp: { chatCount: number } | null
  sportsData: { valueBetCount: number } | null
  settingsCount: number | null
}

export interface ActivityItem {
  time: string
  moduleLabel: string
  event: string
}

async function safeJson<T>(url: string): Promise<T | null> {
  try {
    const res = await fetch(url)
    if (!res.ok) return null
    return (await res.json()) as T
  } catch {
    return null
  }
}

function fmtTime(iso: string | null | undefined) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

export function useHomeSummary() {
  const [summary, setSummary] = useState<ModuleSummary | null>(null)
  const [activity, setActivity] = useState<ActivityItem[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false

    async function load() {
      const now = new Date()
      const month = now.getMonth() + 1
      const year = now.getFullYear()

      const [transactions, assets, chats, valueBets, services] = await Promise.all([
        safeJson<{ amount: { amount: string }; type: string; description: string; date: string }[]>(
          `${GATEWAY}/finance/transactions?month=${month}&year=${year}`
        ),
        safeJson<{ quote: { gain_loss_pct: string } | null }[]>(`${GATEWAY}/portfolio/assets`),
        safeJson<{ name?: string; last_message_at?: string }[]>(`${GATEWAY}/whatsapp/chats`),
        safeJson<{ match?: string; created_at?: string }[]>(`${GATEWAY}/domain-data-insights/value-bets?limit=200`),
        safeJson<{ name: string }[]>(`${GATEWAY}/settings/services`),
      ])

      if (cancelled) return

      const balance = transactions
        ? transactions.reduce((sum, t) => sum + (t.type === 'income' ? 1 : -1) * Number(t.amount.amount), 0)
        : null

      const avgChange = assets && assets.length
        ? assets.reduce((sum, a) => sum + Number(a.quote?.gain_loss_pct ?? 0), 0) / assets.length
        : null

      setSummary({
        finance: transactions ? { balance: balance ?? 0, count: transactions.length } : null,
        portfolio: assets ? { count: assets.length, changePct: avgChange } : null,
        whatsapp: chats ? { chatCount: chats.length } : null,
        sportsData: valueBets ? { valueBetCount: valueBets.length } : null,
        settingsCount: services ? services.length : null,
      })

      const items: ActivityItem[] = []
      if (transactions?.length) {
        const last = [...transactions].sort((a, b) => b.date.localeCompare(a.date))[0]
        items.push({ time: fmtTime(last.date), moduleLabel: 'Finance', event: last.description || 'Novo lançamento registrado' })
      }
      if (valueBets?.length) {
        const last = valueBets[0]
        items.push({ time: fmtTime(last.created_at), moduleLabel: 'Sports Data', event: last.match ? `Value bet: ${last.match}` : 'Novo value bet identificado' })
      }
      if (chats?.length) {
        items.push({ time: fmtTime(chats[0].last_message_at), moduleLabel: 'WhatsApp', event: chats[0].name ? `Nova mensagem de ${chats[0].name}` : 'Nova mensagem recebida' })
      }
      setActivity(items)
      setLoading(false)
    }

    load()
    return () => { cancelled = true }
  }, [])

  return { summary, activity, loading }
}
