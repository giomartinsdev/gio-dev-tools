import { useState, useCallback, useMemo, useRef, useEffect } from 'react'
import { DollarSign, Trash2, Loader2, Plus } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

type TransactionType = 'income' | 'expense'

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

const CATEGORIES: Record<TransactionType, string[]> = {
  income: ['Salary', 'Freelance', 'Investment', 'Gift', 'Other'],
  expense: ['Food', 'Transport', 'Housing', 'Health', 'Entertainment', 'Education', 'Shopping', 'Other'],
}

function today() {
  return new Date().toISOString().split('T')[0]
}

function emptyDraft(): Draft {
  return { date: today(), description: '', category: 'Food', type: 'expense', amount: '' }
}

function formatBRL(value: number) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value)
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

const cellInput = 'w-full rounded border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground'

export function FinanceModule() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [loading, setLoading] = useState(true)
  const [draft, setDraft] = useState<Draft>(emptyDraft)
  const [submitting, setSubmitting] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const dateRef = useRef<HTMLInputElement>(null)

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

  const fetchTransactions = useCallback(async () => {
    const res = await fetch(`${GATEWAY}/fn/finance`)
    if (res.ok) setTransactions(await res.json())
    setLoading(false)
  }, [])

  useEffect(() => { fetchTransactions() }, [fetchTransactions])

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
      const res = await fetch(`${GATEWAY}/fn/finance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })
      if (res.ok) {
        await fetchTransactions()
        setDraft(emptyDraft())
        setTimeout(() => dateRef.current?.focus(), 0)
      }
    } finally {
      setSubmitting(false)
    }
  }

  async function remove(id: string) {
    setDeletingId(id)
    try {
      const res = await fetch(`${GATEWAY}/fn/finance`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      })
      if (res.ok) await fetchTransactions()
    } finally {
      setDeletingId(null)
    }
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); submit() }
  }

  return (
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
            <tr>
              <td colSpan={6} className="py-16 text-center">
                <Loader2 className="h-5 w-5 animate-spin mx-auto text-muted-foreground" />
              </td>
            </tr>
          ) : (
            transactions.map(tx => (
              <tr key={tx.id} className="border-b group hover:bg-muted/30 transition-colors">
                <Td className="tabular-nums text-muted-foreground">{formatDate(tx.date)}</Td>
                <Td className="font-medium">{tx.description}</Td>
                <Td className="text-muted-foreground">{tx.category}</Td>
                <Td>
                  <TypePill type={tx.type} />
                </Td>
                <Td className={cn(
                  'text-right font-semibold tabular-nums',
                  tx.type === 'income' ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
                )}>
                  {tx.type === 'income' ? '+' : '−'}{formatBRL(parseFloat(tx.amount.amount))}
                </Td>
                <td className="px-1.5">
                  <button
                    onClick={() => remove(tx.id)}
                    disabled={deletingId === tx.id}
                    className="opacity-0 group-hover:opacity-100 rounded p-1 text-muted-foreground hover:text-destructive transition-opacity disabled:opacity-30"
                  >
                    {deletingId === tx.id
                      ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                      : <Trash2 className="h-3.5 w-3.5" />}
                  </button>
                </td>
              </tr>
            ))
          )}

          {/* Input row */}
          <tr className="border-b bg-blue-50/30 dark:bg-blue-950/20">
            <td className="px-1.5 py-1.5">
              <input
                ref={dateRef}
                type="date"
                value={draft.date}
                onChange={e => set('date', e.target.value)}
                onKeyDown={onKeyDown}
                className={cellInput}
              />
            </td>
            <td className="px-1.5 py-1.5">
              <input
                type="text"
                value={draft.description}
                onChange={e => set('description', e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="Description..."
                className={cellInput}
              />
            </td>
            <td className="px-1.5 py-1.5">
              <select
                value={draft.category}
                onChange={e => set('category', e.target.value)}
                onKeyDown={onKeyDown}
                className={cellInput}
              >
                {CATEGORIES[draft.type].map(c => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </td>
            <td className="px-1.5 py-1.5">
              <button
                type="button"
                onClick={toggleType}
                className={cn(
                  'w-full rounded px-2 py-1 text-xs font-medium border transition-colors',
                  draft.type === 'income'
                    ? 'border-green-500 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300'
                    : 'border-red-500 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300'
                )}
              >
                {draft.type === 'income' ? 'Income' : 'Expense'}
              </button>
            </td>
            <td className="px-1.5 py-1.5">
              <input
                type="number"
                min="0.01"
                step="0.01"
                value={draft.amount}
                onChange={e => set('amount', e.target.value)}
                onKeyDown={onKeyDown}
                placeholder="0.00"
                className={cn(cellInput, 'text-right')}
              />
            </td>
            <td className="px-1.5 py-1.5">
              <button
                onClick={submit}
                disabled={submitting || !draft.amount || !draft.description}
                className="rounded p-1 text-muted-foreground hover:text-primary transition-colors disabled:opacity-30"
              >
                {submitting
                  ? <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  : <Plus className="h-3.5 w-3.5" />}
              </button>
            </td>
          </tr>
        </tbody>

        {/* Totals footer */}
        <tfoot className="border-t-2">
          <tr className="bg-muted/20">
            <td className="px-3 py-2" />
            <td className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Income</td>
            <td colSpan={2} />
            <td className="px-3 py-2 text-right font-semibold tabular-nums text-green-600 dark:text-green-400">
              {formatBRL(totals.income)}
            </td>
            <td />
          </tr>
          <tr className="bg-muted/20">
            <td className="px-3 py-2" />
            <td className="px-3 py-2 text-xs font-semibold uppercase tracking-wide text-muted-foreground">Expenses</td>
            <td colSpan={2} />
            <td className="px-3 py-2 text-right font-semibold tabular-nums text-red-600 dark:text-red-400">
              {formatBRL(totals.expenses)}
            </td>
            <td />
          </tr>
          <tr className="bg-muted/20 border-t">
            <td className="px-3 py-2.5" />
            <td className="px-3 py-2.5 text-xs font-bold uppercase tracking-wide text-foreground">Balance</td>
            <td colSpan={2} />
            <td className={cn(
              'px-3 py-2.5 text-right font-bold tabular-nums text-base',
              totals.balance >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            )}>
              {formatBRL(totals.balance)}
            </td>
            <td />
          </tr>
        </tfoot>
      </table>
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
