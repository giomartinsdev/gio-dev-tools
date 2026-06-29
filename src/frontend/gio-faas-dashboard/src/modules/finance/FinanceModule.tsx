import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { DollarSign, Trash2, Loader2, Plus, ChevronLeft, ChevronRight, ScanLine, Pencil, Check, X } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  PieChart, Pie, Cell, Tooltip, Legend, ResponsiveContainer,
  BarChart, Bar, XAxis, YAxis, CartesianGrid,
  LineChart, Line,
} from 'recharts'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

type TransactionType = 'income' | 'expense'
type ChartPeriod = 'month' | '6m' | '1y'

interface Transaction {
  id: string
  amount: { amount: string; currency: string }
  type: TransactionType
  category: string
  description: string
  date: string
}

interface Draft {
  date: string
  description: string
  category: string
  type: TransactionType
  amount: string
}

interface MonthData {
  label: string
  month: number
  year: number
  income: number
  expenses: number
  balance: number
  byCategory: Record<string, number>
}

const CATEGORIES: Record<TransactionType, string[]> = {
  income: ['Transaction', 'Food', 'Health', 'Entertainment', 'Education', 'Shopping', 'Other'],
  expense: ['Transaction', 'Food', 'Health', 'Entertainment', 'Education', 'Shopping', 'Other'],
}

const CATEGORY_COLORS: Record<string, string> = {
  Transaction: '#64748b',
  Food:        '#f97316',
  Health:      '#ec4899',
  Entertainment:'#a855f7',
  Education:   '#06b6d4',
  Shopping:    '#f59e0b',
  Other:       '#9ca3af',
}

const INCOME_COLOR   = '#22c55e'
const EXPENSE_COLOR  = '#ef4444'
const BALANCE_COLOR  = '#3b82f6'

function toYearMonth(d: Date) {
  return { year: d.getFullYear(), month: d.getMonth() + 1 }
}

function defaultDate(year: number, month: number) {
  const now = new Date()
  const isCurrentMonth = now.getFullYear() === year && now.getMonth() + 1 === month
  if (isCurrentMonth) return now.toISOString().split('T')[0]
  return new Date(year, month - 1, 1).toISOString().split('T')[0]
}

function emptyDraft(year: number, month: number): Draft {
  return { date: defaultDate(year, month), description: '', category: 'Transaction', type: 'expense', amount: '' }
}

function formatBRL(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

function aggregateMonth(txs: Transaction[]): Omit<MonthData, 'label' | 'month' | 'year'> {
  let income = 0, expenses = 0
  const byCategory: Record<string, number> = {}
  for (const tx of txs) {
    const amt = parseFloat(tx.amount.amount)
    if (tx.type === 'income') {
      income += amt
    } else {
      expenses += amt
      byCategory[tx.category] = (byCategory[tx.category] || 0) + Math.abs(amt)
    }
  }
  return { income: Math.abs(income), expenses: Math.abs(expenses), balance: income - expenses, byCategory }
}

const cellInput = 'w-full rounded border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground'

export function FinanceModule() {
  const [cursor, setCursor] = useState(() => new Date())
  const { year, month } = toYearMonth(cursor)

  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState<Draft>(() => emptyDraft(year, month))
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [ocrState, setOcrState] = useState<'idle' | 'uploading' | 'processing'>('idle')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<Draft | null>(null)
  const [saving, setSaving] = useState(false)

  const [chartPeriod, setChartPeriod] = useState<ChartPeriod>('month')
  const [rangeData, setRangeData] = useState<MonthData[]>([])
  const [rangeLoading, setRangeLoading] = useState(false)

  const dateRef = useRef<HTMLInputElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const monthLabel = cursor.toLocaleDateString('en-US', { month: 'long', year: 'numeric' })

  const totals = useMemo(() => {
    const draftAmt = parseFloat(draft.amount) || 0
    let income = 0, expenses = 0
    for (const t of transactions) {
      const amt = parseFloat(t.amount.amount)
      t.type === 'income' ? (income += amt) : (expenses += amt)
    }
    if (draftAmt > 0) {
      draft.type === 'income' ? (income += draftAmt) : (expenses += draftAmt)
    }
    return { income, expenses, balance: income - expenses }
  }, [transactions, draft.amount, draft.type])

  const fetchTransactions = useCallback(async (y: number, m: number) => {
    setLoading(true)
    const res = await fetch(`${GATEWAY}/finance/transactions?month=${m}&year=${y}`)
    if (res.ok) setTransactions(await res.json())
    setLoading(false)
  }, [])

  const fetchRange = useCallback(async (months: number) => {
    setRangeLoading(true)
    const promises = Array.from({ length: months }, (_, i) => {
      const d = new Date(year, month - 1 - (months - 1 - i), 1)
      const m = d.getMonth() + 1
      const y = d.getFullYear()
      const label = d.toLocaleDateString('en-US', { month: 'short', year: '2-digit' })
      return fetch(`${GATEWAY}/finance/transactions?month=${m}&year=${y}`)
        .then(r => r.ok ? r.json() : [])
        .then((txs: Transaction[]): MonthData => {
          const agg = aggregateMonth(txs)
          return { ...agg, label, month: m, year: y }
        })
    })
    const results = await Promise.all(promises)
    setRangeData(results)
    setRangeLoading(false)
  }, [year, month])

  useEffect(() => {
    fetchTransactions(year, month)
    setDraft(emptyDraft(year, month))
  }, [year, month, fetchTransactions])

  useEffect(() => {
    if (chartPeriod === '6m') fetchRange(6)
    else if (chartPeriod === '1y') fetchRange(12)
  }, [chartPeriod, year, month, fetchRange])

  function prevMonth() { setCursor(d => new Date(d.getFullYear(), d.getMonth() - 1, 1)) }
  function nextMonth() { setCursor(d => new Date(d.getFullYear(), d.getMonth() + 1, 1)) }

  function set<K extends keyof Draft>(field: K, value: Draft[K]) {
    setDraft(d => ({ ...d, [field]: value }))
  }

  function toggleType() {
    const next: TransactionType = draft.type === 'income' ? 'expense' : 'income'
    setDraft(d => ({ ...d, type: next, category: CATEGORIES[next][0] }))
  }

  async function submit() {
    if (!draft.amount || !draft.description || !draft.category) return
    setSubmitting(true)
    try {
      const res = await fetch(`${GATEWAY}/finance/transactions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })
      if (res.ok) {
        await fetchTransactions(year, month)
        setDraft(emptyDraft(year, month))
        setTimeout(() => dateRef.current?.focus(), 0)
      }
    } finally { setSubmitting(false) }
  }

  async function remove(id: string) {
    setDeletingId(id)
    try {
      const res = await fetch(`${GATEWAY}/finance/transactions/${id}`, {
        method: 'DELETE',
      })
      if (res.ok) await fetchTransactions(year, month)
    } finally { setDeletingId(null) }
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); submit() }
  }

  function startEdit(tx: Transaction) {
    setEditingId(tx.id)
    setEditDraft({
      date: tx.date.split('T')[0],
      description: tx.description,
      category: tx.category,
      type: tx.type,
      amount: tx.amount.amount,
    })
  }

  function cancelEdit() { setEditingId(null); setEditDraft(null) }

  function setEdit<K extends keyof Draft>(field: K, value: Draft[K]) {
    setEditDraft(d => d ? { ...d, [field]: value } : d)
  }

  function toggleEditType() {
    if (!editDraft) return
    const next: TransactionType = editDraft.type === 'income' ? 'expense' : 'income'
    setEditDraft(d => d ? { ...d, type: next, category: CATEGORIES[next][0] } : d)
  }

  async function saveEdit() {
    if (!editDraft || !editingId) return
    setSaving(true)
    try {
      const res = await fetch(`${GATEWAY}/finance/transactions/${editingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editDraft),
      })
      if (res.ok) { await fetchTransactions(year, month); cancelEdit() }
    } finally { setSaving(false) }
  }

  function onEditKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); saveEdit() }
    if (e.key === 'Escape') cancelEdit()
  }

  async function uploadReceipt(file: File) {
    setOcrState('uploading')
    try {
      const formData = new FormData()
      formData.append('file', file)
      setOcrState('processing')
      const res = await fetch(`${GATEWAY}/finance-ocr/ocr`, { method: 'POST', body: formData })
      if (!res.ok) throw new Error(`OCR failed: ${res.status}`)
      await fetchTransactions(year, month)
    } catch {
      await fetchTransactions(year, month)
    } finally { setOcrState('idle') }
  }

  function onFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) uploadReceipt(file)
    e.target.value = ''
  }

  // Pie data from current month transactions
  const pieData = useMemo(() => {
    const map: Record<string, number> = {}
    for (const tx of transactions) {
      if (tx.type === 'expense') {
        const amt = Math.abs(parseFloat(tx.amount.amount))
        map[tx.category] = (map[tx.category] || 0) + amt
      }
    }
    return Object.entries(map)
      .filter(([, v]) => v > 0)
      .map(([name, value]) => ({ name, value }))
      .sort((a, b) => b.value - a.value)
  }, [transactions])

  return (
    <div className="flex flex-col gap-6">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/jpeg,image/png,image/gif,image/webp"
        className="hidden"
        onChange={onFileChange}
      />

      {/* Month navigator */}
      <div className="flex items-center justify-between">
        <button onClick={prevMonth} className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-semibold">{monthLabel}</span>
        <div className="flex items-center gap-1">
          {ocrState !== 'idle' && (
            <span className="text-xs text-muted-foreground flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin" />
              {ocrState === 'uploading' ? 'Sending...' : 'Processing receipt...'}
            </span>
          )}
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={ocrState !== 'idle'}
            title="Import receipt via OCR"
            className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors disabled:opacity-40"
          >
            <ScanLine className="h-4 w-4" />
          </button>
          <button onClick={nextMonth} className="rounded-md p-1.5 text-muted-foreground hover:bg-accent hover:text-accent-foreground transition-colors">
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Totals */}
      <div className="grid grid-cols-3 gap-4">
        <TotalCard label="Income" value={totals.income} color="green" />
        <TotalCard label="Expenses" value={Math.abs(totals.expenses)} color="red" />
        <TotalCard label="Balance" value={totals.balance} color={totals.balance >= 0 ? 'green' : 'red'} />
      </div>

      {/* Table */}
      <div className="rounded-lg border bg-card overflow-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b bg-muted/50">
              <Th className="w-32">Date</Th>
              <Th>Description</Th>
              <Th className="w-36">Category</Th>
              <Th className="w-24">Type</Th>
              <Th className="w-36 text-right">Amount</Th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr><td colSpan={6} className="py-16 text-center"><Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" /></td></tr>
            ) : transactions.length === 0 ? (
              <tr><td colSpan={6} className="py-10 text-center text-sm text-muted-foreground">No transactions in {monthLabel}.</td></tr>
            ) : (
              transactions.map(tx => {
                const isReversal = tx.description.startsWith('[reversal]')
                const rawAmt = parseFloat(tx.amount.amount)
                const isEditing = editingId === tx.id

                if (isEditing && editDraft) {
                  return (
                    <tr key={tx.id} className="border-b bg-amber-50/40 dark:bg-amber-950/20">
                      <td className="px-1.5 py-1.5">
                        <input type="date" value={editDraft.date} onChange={e => setEdit('date', e.target.value)} onKeyDown={onEditKeyDown} className={cellInput} />
                      </td>
                      <td className="px-1.5 py-1.5">
                        <input type="text" value={editDraft.description} onChange={e => setEdit('description', e.target.value)} onKeyDown={onEditKeyDown} placeholder="Description..." className={cellInput} />
                      </td>
                      <td className="px-1.5 py-1.5">
                        <select value={editDraft.category} onChange={e => setEdit('category', e.target.value)} onKeyDown={onEditKeyDown} className={cellInput}>
                          {CATEGORIES[editDraft.type].map(c => <option key={c} value={c}>{c}</option>)}
                        </select>
                      </td>
                      <td className="px-1.5 py-1.5">
                        <button type="button" onClick={toggleEditType} className={cn(
                          'w-full rounded px-2 py-1 text-xs font-medium border transition-colors',
                          editDraft.type === 'income'
                            ? 'border-green-500 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300'
                            : 'border-red-500 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300'
                        )}>
                          {editDraft.type === 'income' ? 'Income' : 'Expense'}
                        </button>
                      </td>
                      <td className="px-1.5 py-1.5">
                        <input type="number" min="0.01" step="0.01" value={editDraft.amount} onChange={e => setEdit('amount', e.target.value)} onKeyDown={onEditKeyDown} placeholder="0.00" className={cn(cellInput, 'text-right')} />
                      </td>
                      <td className="px-1.5 py-1.5 flex items-center gap-1">
                        <button onClick={saveEdit} disabled={saving || !editDraft.amount || !editDraft.description} className="rounded p-1 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30">
                          {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Check className="h-3.5 w-3.5" />}
                        </button>
                        <button onClick={cancelEdit} className="rounded p-1 text-muted-foreground hover:text-destructive transition-colors">
                          <X className="h-3.5 w-3.5" />
                        </button>
                      </td>
                    </tr>
                  )
                }

                return (
                  <tr key={tx.id} className={cn('border-b group hover:bg-muted/30 transition-colors', isReversal && 'opacity-50')}>
                    <Td className="tabular-nums text-muted-foreground">{formatDate(tx.date)}</Td>
                    <Td className={cn('font-medium', isReversal && 'italic text-muted-foreground')}>{tx.description}</Td>
                    <Td className="text-muted-foreground">{tx.category}</Td>
                    <Td><TypePill type={tx.type} /></Td>
                    <Td className={cn(
                      'text-right font-semibold tabular-nums',
                      isReversal ? 'text-muted-foreground'
                        : tx.type === 'income' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                    )}>
                      {isReversal
                        ? `(${formatBRL(Math.abs(rawAmt))})`
                        : `${tx.type === 'income' ? '+' : '−'}${formatBRL(rawAmt)}`}
                    </Td>
                    <td className="px-1.5">
                      <div className="opacity-0 group-hover:opacity-100 flex items-center gap-0.5 transition-opacity">
                        {!isReversal && (
                          <button onClick={() => startEdit(tx)} disabled={!!editingId} className="rounded p-1 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30">
                            <Pencil className="h-3.5 w-3.5" />
                          </button>
                        )}
                        <button onClick={() => remove(tx.id)} disabled={deletingId === tx.id} className="rounded p-1 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-30">
                          {deletingId === tx.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}

            {/* Input row */}
            <tr className="border-b bg-blue-50/30 dark:bg-blue-950/20">
              <td className="px-1.5 py-1.5">
                <input ref={dateRef} type="date" value={draft.date} onChange={e => set('date', e.target.value)} onKeyDown={onKeyDown} className={cellInput} />
              </td>
              <td className="px-1.5 py-1.5">
                <input type="text" value={draft.description} onChange={e => set('description', e.target.value)} onKeyDown={onKeyDown} placeholder="Description..." className={cellInput} />
              </td>
              <td className="px-1.5 py-1.5">
                <select value={draft.category} onChange={e => set('category', e.target.value)} onKeyDown={onKeyDown} className={cellInput}>
                  {CATEGORIES[draft.type].map(c => <option key={c} value={c}>{c}</option>)}
                </select>
              </td>
              <td className="px-1.5 py-1.5">
                <button type="button" onClick={toggleType} className={cn(
                  'w-full rounded px-2 py-1 text-xs font-medium border transition-colors',
                  draft.type === 'income'
                    ? 'border-green-500 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300'
                    : 'border-red-500 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300'
                )}>
                  {draft.type === 'income' ? 'Income' : 'Expense'}
                </button>
              </td>
              <td className="px-1.5 py-1.5">
                <input type="number" min="0.01" step="0.01" value={draft.amount} onChange={e => set('amount', e.target.value)} onKeyDown={onKeyDown} placeholder="0.00" className={cn(cellInput, 'text-right')} />
              </td>
              <td className="px-1.5 py-1.5">
                <button onClick={submit} disabled={submitting || !draft.amount || !draft.description} className="rounded p-1 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30">
                  {submitting ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Plus className="h-3.5 w-3.5" />}
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      {/* Charts section */}
      <div className="rounded-lg border bg-card p-4 flex flex-col gap-4">
        {/* Period tabs */}
        <div className="flex items-center gap-1 self-start rounded-lg bg-muted p-1">
          {(['month', '6m', '1y'] as ChartPeriod[]).map(p => (
            <button
              key={p}
              onClick={() => setChartPeriod(p)}
              className={cn(
                'rounded-md px-3 py-1 text-xs font-medium transition-colors',
                chartPeriod === p
                  ? 'bg-background text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              )}
            >
              {p === 'month' ? 'Month' : p === '6m' ? '6 Months' : '1 Year'}
            </button>
          ))}
        </div>

        {chartPeriod === 'month' && (
          <MonthCharts transactions={transactions} pieData={pieData} totals={totals} />
        )}

        {(chartPeriod === '6m' || chartPeriod === '1y') && (
          rangeLoading
            ? <div className="flex items-center justify-center h-48"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
            : <RangeCharts data={rangeData} />
        )}
      </div>
    </div>
  )
}

// ─── Month charts ────────────────────────────────────────────────────────────

interface PieEntry { name: string; value: number }

function MonthCharts({ transactions, pieData, totals }: {
  transactions: Transaction[]
  pieData: PieEntry[]
  totals: { income: number; expenses: number; balance: number }
}) {
  const barData = [
    { name: 'Income', value: Math.abs(totals.income) },
    { name: 'Expenses', value: Math.abs(totals.expenses) },
  ]

  if (transactions.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No data for this month.</p>
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <ChartCard title="Expenses by Category">
        {pieData.length === 0
          ? <p className="text-sm text-muted-foreground text-center py-8">No expenses this month.</p>
          : (
            <ResponsiveContainer width="100%" height={240}>
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${((percent ?? 0) * 100).toFixed(0)}%`} labelLine={false}>
                  {pieData.map(entry => (
                    <Cell key={entry.name} fill={CATEGORY_COLORS[entry.name] ?? '#9ca3af'} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => formatBRL(Number(v))} />
              </PieChart>
            </ResponsiveContainer>
          )}
      </ChartCard>

      <ChartCard title="Income vs Expenses">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={barData} barSize={48}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={v => formatBRL(v)} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
            <Tooltip formatter={(v) => formatBRL(Number(v))} />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {barData.map(entry => (
                <Cell key={entry.name} fill={entry.name === 'Income' ? INCOME_COLOR : EXPENSE_COLOR} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>
    </div>
  )
}

// ─── Range charts (6M / 1Y) ──────────────────────────────────────────────────

function RangeCharts({ data }: { data: MonthData[] }) {
  if (data.length === 0) {
    return <p className="text-sm text-muted-foreground text-center py-8">No data available.</p>
  }

  // All categories that appear across the range
  const allCategories = Array.from(
    new Set(data.flatMap(d => Object.keys(d.byCategory)))
  )

  // Stacked bar data: each month has a key per category
  const stackedData = data.map(d => ({
    label: d.label,
    ...Object.fromEntries(allCategories.map(c => [c, d.byCategory[c] ?? 0])),
  }))

  return (
    <div className="flex flex-col gap-6">
      {/* Income vs Expenses per month */}
      <ChartCard title="Income vs Expenses">
        <ResponsiveContainer width="100%" height={240}>
          <BarChart data={data} barCategoryGap="30%" barGap={4}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={v => formatBRL(v)} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
            <Tooltip formatter={(v) => formatBRL(Number(v))} />
            <Legend />
            <Bar dataKey="income" name="Income" fill={INCOME_COLOR} radius={[3, 3, 0, 0]} />
            <Bar dataKey="expenses" name="Expenses" fill={EXPENSE_COLOR} radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Balance trend */}
      <ChartCard title="Balance Trend">
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
            <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
            <YAxis tickFormatter={v => formatBRL(v)} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
            <Tooltip formatter={(v) => formatBRL(Number(v))} />
            <Line type="monotone" dataKey="balance" name="Balance" stroke={BALANCE_COLOR} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* Expenses by category (stacked bars) */}
      {allCategories.length > 0 && (
        <ChartCard title="Expenses by Category">
          <ResponsiveContainer width="100%" height={240}>
            <BarChart data={stackedData} barCategoryGap="30%">
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
              <XAxis dataKey="label" tick={{ fontSize: 11 }} axisLine={false} tickLine={false} />
              <YAxis tickFormatter={v => formatBRL(v)} tick={{ fontSize: 11 }} axisLine={false} tickLine={false} width={80} />
              <Tooltip formatter={(v) => formatBRL(Number(v))} />
              <Legend />
              {allCategories.map(cat => (
                <Bar key={cat} dataKey={cat} stackId="a" fill={CATEGORY_COLORS[cat] ?? '#9ca3af'} radius={allCategories[allCategories.length - 1] === cat ? [3, 3, 0, 0] : [0, 0, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>
      )}
    </div>
  )
}

// ─── Shared primitives ────────────────────────────────────────────────────────

function TotalCard({ label, value, color }: { label: string; value: number; color: 'green' | 'red' }) {
  return (
    <div className="rounded-lg border bg-card px-4 py-3 space-y-1">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className={cn(
        'text-lg font-bold tabular-nums',
        color === 'green' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
      )}>
        {formatBRL(value)}
      </p>
    </div>
  )
}

function ChartCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{title}</p>
      {children}
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

function TypePill({ type }: { type: TransactionType }) {
  return (
    <span className={cn(
      'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium',
      type === 'income'
        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
        : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
    )}>
      {type === 'income' ? 'Income' : 'Expense'}
    </span>
  )
}

export const financeMeta = {
  id: 'finance' as const,
  label: 'Finance',
  description: 'Track income and expenses',
  icon: DollarSign,
  badge: <Badge variant="outline">New</Badge>,
}
