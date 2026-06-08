import { useState, useEffect, useCallback, useMemo } from 'react'
import { Landmark, Trash2, Loader2, Plus, Pencil, Check, X, TrendingUp, TrendingDown, RefreshCw } from 'lucide-react'
import { cn } from '@/lib/utils'
import {
  PieChart, Pie, Cell, Tooltip, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
} from 'recharts'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

const ASSET_TYPES = ['CDB', 'FII', 'Stock', 'Treasury', 'Savings', 'Crypto', 'Other'] as const
type AssetType = typeof ASSET_TYPES[number]

interface Quote {
  price: string
  daily_change: string | null
  daily_change_pct: string | null
  current_value: string
  gain_loss: string
  gain_loss_pct: string
  last_dividend: string | null
  last_dividend_date: string | null
  recorded_at: string | null
}

interface Asset {
  id: string
  name: string
  type: AssetType
  institution: string
  quantity: string
  purchase_price: string
  total_value: string
  currency: string
  ticker: string | null
  quote: Quote | null
}

interface Draft {
  name: string
  type: AssetType
  institution: string
  quantity: string
  purchase_price: string
  ticker: string
}

const TYPE_COLORS: Record<AssetType, string> = {
  'CDB':      '#3b82f6',
  'FII':      '#f97316',
  'Stock':    '#22c55e',
  'Treasury': '#a855f7',
  'Savings':  '#06b6d4',
  'Crypto':   '#f59e0b',
  'Other':    '#9ca3af',
}

function emptyDraft(): Draft {
  return { name: '', type: 'CDB', institution: '', quantity: '', purchase_price: '', ticker: '' }
}

function formatBRL(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatQty(value: string) {
  const n = parseFloat(value)
  return Number.isInteger(n) ? n.toString() : n.toFixed(4).replace(/\.?0+$/, '')
}

function formatPct(value: string | null) {
  if (value === null) return null
  const n = parseFloat(value)
  return `${n >= 0 ? '+' : ''}${n.toFixed(2)}%`
}

const cellInput = 'w-full rounded border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground'

export function PortfolioModule() {
  const [assets, setAssets] = useState<Asset[]>([])
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<Draft | null>(null)
  const [saving, setSaving] = useState(false)
  const [syncing, setSyncing] = useState(false)
  const [syncResult, setSyncResult] = useState<{ updated: string[]; failed: string[] } | null>(null)

  const fetchAssets = useCallback(async () => {
    setLoading(true)
    const res = await fetch(`${GATEWAY}/fn/portfolio`)
    if (res.ok) setAssets(await res.json())
    setLoading(false)
  }, [])

  useEffect(() => { fetchAssets() }, [fetchAssets])

  async function submit() {
    if (!draft.name || !draft.institution || !draft.quantity || !draft.purchase_price) return
    setSubmitting(true)
    try {
      const res = await fetch(`${GATEWAY}/fn/portfolio`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })
      if (res.ok) { await fetchAssets(); setDraft(emptyDraft()) }
    } finally { setSubmitting(false) }
  }

  async function remove(id: string) {
    setDeletingId(id)
    try {
      const res = await fetch(`${GATEWAY}/fn/portfolio`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      })
      if (res.ok) await fetchAssets()
    } finally { setDeletingId(null) }
  }

  function startEdit(asset: Asset) {
    setEditingId(asset.id)
    setEditDraft({
      name: asset.name,
      type: asset.type,
      institution: asset.institution,
      quantity: asset.quantity,
      purchase_price: asset.purchase_price,
      ticker: asset.ticker ?? '',
    })
  }

  function cancelEdit() { setEditingId(null); setEditDraft(null) }

  function setEdit<K extends keyof Draft>(field: K, value: Draft[K]) {
    setEditDraft(d => d ? { ...d, [field]: value } : d)
  }

  async function saveEdit() {
    if (!editDraft || !editingId) return
    setSaving(true)
    try {
      const res = await fetch(`${GATEWAY}/fn/portfolio`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id: editingId, ...editDraft }),
      })
      if (res.ok) { await fetchAssets(); cancelEdit() }
    } finally { setSaving(false) }
  }

  async function syncQuotes() {
    setSyncing(true)
    setSyncResult(null)
    try {
      const res = await fetch(`${GATEWAY}/fn/asset-quotes`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        setSyncResult(data)
        await fetchAssets()
      }
    } finally {
      setSyncing(false)
    }
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); submit() }
  }

  function onEditKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); saveEdit() }
    if (e.key === 'Escape') cancelEdit()
  }

  // Use current_value from quote when available, fall back to total_value
  const total = useMemo(
    () => assets.reduce((s, a) => s + parseFloat(a.quote?.current_value ?? a.total_value), 0),
    [assets]
  )

  const byType = useMemo(() => {
    const map: Record<string, number> = {}
    for (const a of assets) {
      const val = parseFloat(a.quote?.current_value ?? a.total_value)
      map[a.type] = (map[a.type] || 0) + val
    }
    return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
  }, [assets])

  const byInstitution = useMemo(() => {
    const map: Record<string, number> = {}
    for (const a of assets) {
      const val = parseFloat(a.quote?.current_value ?? a.total_value)
      map[a.institution] = (map[a.institution] || 0) + val
    }
    return Object.entries(map).map(([name, value]) => ({ name, value })).sort((a, b) => b.value - a.value)
  }, [assets])

  const fiiWithDividend = useMemo(
    () => assets.filter(a => a.quote?.last_dividend),
    [assets]
  )

  const monthlyIncome = useMemo(
    () => fiiWithDividend.reduce((s, a) => s + parseFloat(a.quantity) * parseFloat(a.quote!.last_dividend!), 0),
    [fiiWithDividend]
  )

  const editValid = editDraft && editDraft.name && editDraft.institution && editDraft.quantity && editDraft.purchase_price
  const addValid = draft.name && draft.institution && draft.quantity && draft.purchase_price

  const hasQuotes = assets.some(a => a.quote)

  return (
    <div className="flex flex-col gap-6">

      {/* Total card */}
      <div className="rounded-lg border bg-card px-5 py-4 flex items-center justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Total Portfolio</p>
          <p className="text-2xl font-bold tabular-nums text-foreground mt-0.5">{formatBRL(total)}</p>
          <div className="flex items-center gap-2 mt-0.5">
            {hasQuotes && <p className="text-xs text-muted-foreground">com cotação atualizada</p>}
            {syncResult && (
              <p className="text-xs text-muted-foreground">
                {syncResult.updated.length > 0 && <span className="text-green-600 dark:text-green-400">{syncResult.updated.length} atualizados</span>}
                {syncResult.failed.length > 0 && <span className="text-red-500 dark:text-red-400 ml-1">{syncResult.failed.length} falhou</span>}
              </p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-3">
        <button
          onClick={syncQuotes}
          disabled={syncing}
          title="Sincronizar cotações agora"
          className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs font-medium text-muted-foreground hover:text-foreground hover:bg-muted transition-colors disabled:opacity-40"
        >
          {syncing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <RefreshCw className="h-3.5 w-3.5" />}
          {syncing ? 'Sincronizando…' : 'Sync cotações'}
        </button>
        <div className="flex gap-2 flex-wrap justify-end">
          {byType.map(({ name, value }) => (
            <div key={name} className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium">
              <span className="h-2 w-2 rounded-full shrink-0" style={{ background: TYPE_COLORS[name as AssetType] ?? '#9ca3af' }} />
              <span className="text-muted-foreground">{name}</span>
              <span className="tabular-nums">{formatBRL(value)}</span>
            </div>
          ))}
        </div>
        </div>
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <Th>Nome</Th>
              <Th className="w-28">Tipo</Th>
              <Th className="w-32">Instituição</Th>
              <Th className="w-20">Ticker</Th>
              <Th className="w-24 text-right">Qtd</Th>
              <Th className="w-32 text-right">Preço Compra</Th>
              <Th className="w-32 text-right">Cotação</Th>
              <Th className="w-32 text-right">Total</Th>
              <Th className="w-32 text-right">Ganho/Perda</Th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={10} className="py-16 text-center"><Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" /></td></tr>
            ) : assets.length === 0 ? (
              <tr><td colSpan={10} className="py-10 text-center text-sm text-muted-foreground">Nenhum ativo. Adicione um abaixo.</td></tr>
            ) : assets.map(asset => {
              const isEditing = editingId === asset.id
              if (isEditing && editDraft) {
                return (
                  <tr key={asset.id} className="border-b bg-amber-50/40 dark:bg-amber-950/20">
                    <td className="px-1.5 py-1.5">
                      <input type="text" value={editDraft.name} onChange={e => setEdit('name', e.target.value)} onKeyDown={onEditKeyDown} placeholder="Nome..." className={cellInput} />
                    </td>
                    <td className="px-1.5 py-1.5">
                      <select value={editDraft.type} onChange={e => setEdit('type', e.target.value as AssetType)} className={cellInput}>
                        {ASSET_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                    <td className="px-1.5 py-1.5">
                      <input type="text" value={editDraft.institution} onChange={e => setEdit('institution', e.target.value)} onKeyDown={onEditKeyDown} placeholder="Instituição..." className={cellInput} />
                    </td>
                    <td className="px-1.5 py-1.5">
                      <input type="text" value={editDraft.ticker} onChange={e => setEdit('ticker', e.target.value.toUpperCase())} onKeyDown={onEditKeyDown} placeholder="MXRF11" className={cellInput} />
                    </td>
                    <td className="px-1.5 py-1.5">
                      <input type="number" min="0" step="any" value={editDraft.quantity} onChange={e => setEdit('quantity', e.target.value)} onKeyDown={onEditKeyDown} placeholder="0" className={cn(cellInput, 'text-right')} />
                    </td>
                    <td className="px-1.5 py-1.5">
                      <input type="number" min="0" step="0.01" value={editDraft.purchase_price} onChange={e => setEdit('purchase_price', e.target.value)} onKeyDown={onEditKeyDown} placeholder="0.00" className={cn(cellInput, 'text-right')} />
                    </td>
                    <td className="px-3 py-1.5 text-right text-xs text-muted-foreground">—</td>
                    <td className="px-3 py-1.5 text-right text-xs text-muted-foreground tabular-nums">
                      {editDraft.quantity && editDraft.purchase_price
                        ? formatBRL(parseFloat(editDraft.quantity) * parseFloat(editDraft.purchase_price))
                        : '—'}
                    </td>
                    <td className="px-3 py-1.5 text-right text-xs text-muted-foreground">—</td>
                    <td className="px-1.5 py-1.5 flex items-center gap-1">
                      <button onClick={saveEdit} disabled={saving || !editValid} className="rounded p-1 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30">
                        {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                      </button>
                      <button onClick={cancelEdit} className="rounded p-1 text-muted-foreground hover:text-destructive transition-colors">
                        <X className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                )
              }

              const q = asset.quote
              const changePct = q ? parseFloat(q.daily_change_pct ?? '0') : null
              const gainLoss = q ? parseFloat(q.gain_loss) : null
              const gainLossPct = q ? parseFloat(q.gain_loss_pct) : null

              return (
                <tr key={asset.id} className="border-b group hover:bg-muted/30 transition-colors">
                  <Td className="font-medium">{asset.name}</Td>
                  <Td>
                    <span className="inline-flex items-center gap-1.5 rounded-full px-2 py-0.5 text-xs font-medium" style={{ background: `${TYPE_COLORS[asset.type]}20`, color: TYPE_COLORS[asset.type] }}>
                      <span className="h-1.5 w-1.5 rounded-full" style={{ background: TYPE_COLORS[asset.type] }} />
                      {asset.type}
                    </span>
                  </Td>
                  <Td className="text-muted-foreground">{asset.institution}</Td>
                  <Td>
                    {asset.ticker ? (
                      <span className="font-mono text-xs font-semibold text-foreground/80">{asset.ticker}</span>
                    ) : (
                      <span className="text-muted-foreground/40 text-xs">—</span>
                    )}
                  </Td>
                  <Td className="text-right tabular-nums">{formatQty(asset.quantity)}</Td>
                  <Td className="text-right tabular-nums">{formatBRL(parseFloat(asset.purchase_price))}</Td>
                  <Td className="text-right">
                    {q ? (
                      <div className="flex flex-col items-end gap-0.5">
                        <span className="tabular-nums font-medium">{formatBRL(parseFloat(q.price))}</span>
                        {changePct !== null && (
                          <span className={cn('text-xs tabular-nums flex items-center gap-0.5', changePct >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400')}>
                            {changePct >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                            {formatPct(q.daily_change_pct)}
                          </span>
                        )}
                      </div>
                    ) : (
                      <span className="text-muted-foreground/40 text-xs">—</span>
                    )}
                  </Td>
                  <Td className="text-right font-semibold tabular-nums">
                    {formatBRL(parseFloat(q?.current_value ?? asset.total_value))}
                  </Td>
                  <Td className="text-right">
                    {gainLoss !== null && gainLossPct !== null ? (
                      <div className="flex flex-col items-end gap-0.5">
                        <span className={cn('tabular-nums font-medium text-sm', gainLoss >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400')}>
                          {gainLoss >= 0 ? '+' : ''}{formatBRL(gainLoss)}
                        </span>
                        <span className={cn('text-xs tabular-nums', gainLossPct >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-500 dark:text-red-400')}>
                          {formatPct(q!.gain_loss_pct)}
                        </span>
                      </div>
                    ) : (
                      <span className="text-muted-foreground/40 text-xs">—</span>
                    )}
                  </Td>
                  <td className="px-1.5">
                    <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                      <button onClick={() => startEdit(asset)} disabled={!!editingId} className="rounded p-1 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30">
                        <Pencil className="h-3.5 w-3.5" />
                      </button>
                      <button onClick={() => remove(asset.id)} disabled={deletingId === asset.id} className="rounded p-1 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-30">
                        {deletingId === asset.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                      </button>
                    </div>
                  </td>
                </tr>
              )
            })}

            {/* Input row */}
            <tr className="border-b bg-blue-50/30 dark:bg-blue-950/20">
              <td className="px-1.5 py-1.5">
                <input type="text" value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))} onKeyDown={onKeyDown} placeholder="Nome..." className={cellInput} />
              </td>
              <td className="px-1.5 py-1.5">
                <select value={draft.type} onChange={e => setDraft(d => ({ ...d, type: e.target.value as AssetType }))} className={cellInput}>
                  {ASSET_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </td>
              <td className="px-1.5 py-1.5">
                <input type="text" value={draft.institution} onChange={e => setDraft(d => ({ ...d, institution: e.target.value }))} onKeyDown={onKeyDown} placeholder="Instituição..." className={cellInput} />
              </td>
              <td className="px-1.5 py-1.5">
                <input type="text" value={draft.ticker} onChange={e => setDraft(d => ({ ...d, ticker: e.target.value.toUpperCase() }))} onKeyDown={onKeyDown} placeholder="MXRF11" className={cellInput} />
              </td>
              <td className="px-1.5 py-1.5">
                <input type="number" min="0" step="any" value={draft.quantity} onChange={e => setDraft(d => ({ ...d, quantity: e.target.value }))} onKeyDown={onKeyDown} placeholder="0" className={cn(cellInput, 'text-right')} />
              </td>
              <td className="px-1.5 py-1.5">
                <input type="number" min="0" step="0.01" value={draft.purchase_price} onChange={e => setDraft(d => ({ ...d, purchase_price: e.target.value }))} onKeyDown={onKeyDown} placeholder="0.00" className={cn(cellInput, 'text-right')} />
              </td>
              <td colSpan={3} className="px-3 py-1.5 text-right text-xs text-muted-foreground tabular-nums">
                {draft.quantity && draft.purchase_price
                  ? formatBRL(parseFloat(draft.quantity) * parseFloat(draft.purchase_price))
                  : '—'}
              </td>
              <td className="px-1.5 py-1.5">
                <button onClick={submit} disabled={submitting || !addValid} className="rounded p-1 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30">
                  {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Rendimentos section */}
      {fiiWithDividend.length > 0 && (
        <div className="rounded-lg border bg-card p-4 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Rendimentos</p>
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground">Renda mensal estimada:</span>
              <span className="text-sm font-bold text-green-600 dark:text-green-400 tabular-nums">{formatBRL(monthlyIncome)}</span>
            </div>
          </div>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b">
                <Th>Ativo</Th>
                <Th>Ticker</Th>
                <Th className="text-right">Cotação Atual</Th>
                <Th className="text-right">Último Rendimento</Th>
                <Th className="text-right">Data Pagamento</Th>
                <Th className="text-right">Yield Mensal</Th>
                <Th className="text-right">Renda (sua qtd)</Th>
              </tr>
            </thead>
            <tbody>
              {fiiWithDividend.map(a => {
                const q = a.quote!
                const price = parseFloat(q.price)
                const dividend = parseFloat(q.last_dividend!)
                const yieldPct = price > 0 ? (dividend / price * 100) : 0
                const income = parseFloat(a.quantity) * dividend
                return (
                  <tr key={a.id} className="border-b last:border-0 hover:bg-muted/30">
                    <Td className="font-medium">{a.name}</Td>
                    <Td><span className="font-mono text-xs font-semibold">{a.ticker}</span></Td>
                    <Td className="text-right tabular-nums">{formatBRL(price)}</Td>
                    <Td className="text-right tabular-nums text-green-600 dark:text-green-400 font-medium">
                      {formatBRL(dividend)}
                    </Td>
                    <Td className="text-right text-muted-foreground text-xs">
                      {q.last_dividend_date ? new Date(q.last_dividend_date + 'T12:00:00').toLocaleDateString('pt-BR') : '—'}
                    </Td>
                    <Td className="text-right tabular-nums text-xs font-medium">
                      {yieldPct.toFixed(2)}%
                    </Td>
                    <Td className="text-right tabular-nums font-semibold text-green-600 dark:text-green-400">
                      {formatBRL(income)}
                    </Td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Charts */}
      {assets.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="rounded-lg border bg-card p-4 flex flex-col gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Distribuição por Tipo</p>
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={byType} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={85} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                  {byType.map(entry => (
                    <Cell key={entry.name} fill={TYPE_COLORS[entry.name as AssetType] ?? '#9ca3af'} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatBRL(Number(v))} />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="rounded-lg border bg-card p-4 flex flex-col gap-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">Distribuição por Instituição</p>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={byInstitution} layout="vertical" margin={{ left: 8, right: 16 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
                <XAxis type="number" tickFormatter={v => formatBRL(v)} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
                <Tooltip formatter={(v) => formatBRL(Number(v))} />
                <Bar dataKey="value" name="Total" radius={[0, 4, 4, 0]}>
                  {byInstitution.map((_, i) => (
                    <Cell key={i} fill={Object.values(TYPE_COLORS)[i % Object.values(TYPE_COLORS).length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
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

function Td({ children, className }: { children?: React.ReactNode; className?: string }) {
  return <td className={cn('px-3 py-2.5', className)}>{children}</td>
}

export const portfolioMeta = {
  id: 'portfolio' as const,
  label: 'Portfolio',
  description: 'Track your investments and assets',
  icon: Landmark,
}
