import { useState, useEffect, useCallback } from 'react'
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  Plus,
  Trash2,
  Loader2,
  CheckCircle,
  XCircle,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/lib/utils'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

type TransactionType = 'income' | 'expense'

interface Money {
  amount: string
  currency: string
}

interface Transaction {
  id: string
  amount: Money
  type: TransactionType
  category: string
  description: string
  date: string
}

interface Summary {
  total_income: string
  total_expenses: string
  balance: string
  transaction_count: number
}

const CATEGORIES: Record<TransactionType, string[]> = {
  income: ['Salary', 'Freelance', 'Investment', 'Gift', 'Other'],
  expense: ['Food', 'Transport', 'Housing', 'Health', 'Entertainment', 'Education', 'Shopping', 'Other'],
}

type Status = 'idle' | 'loading' | 'success' | 'error'

function formatBRL(value: string): string {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value))
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
}

function today(): string {
  return new Date().toISOString().split('T')[0]
}

export function FinanceModule() {
  const [transactions, setTransactions] = useState<Transaction[]>([])
  const [summary, setSummary] = useState<Summary | null>(null)
  const [loadingData, setLoadingData] = useState(true)

  const [amount, setAmount] = useState('')
  const [type, setType] = useState<TransactionType>('expense')
  const [category, setCategory] = useState('')
  const [description, setDescription] = useState('')
  const [date, setDate] = useState(today)
  const [submitStatus, setSubmitStatus] = useState<Status>('idle')
  const [submitMsg, setSubmitMsg] = useState('')
  const [deletingId, setDeletingId] = useState<string | null>(null)

  const fetchAll = useCallback(async () => {
    try {
      const [txRes, sumRes] = await Promise.all([
        fetch(`${GATEWAY}/fn/finance`),
        fetch(`${GATEWAY}/fn/finance?summary=true`),
      ])
      if (txRes.ok) setTransactions(await txRes.json())
      if (sumRes.ok) setSummary(await sumRes.json())
    } finally {
      setLoadingData(false)
    }
  }, [])

  useEffect(() => { fetchAll() }, [fetchAll])

  useEffect(() => { setCategory('') }, [type])

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitStatus('loading')
    try {
      const res = await fetch(`${GATEWAY}/fn/finance`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount, type, category, description, date }),
      })
      const data = await res.json()
      if (res.ok) {
        setSubmitStatus('success')
        setSubmitMsg('Transaction recorded.')
        setAmount('')
        setDescription('')
        setDate(today())
        await fetchAll()
      } else {
        setSubmitStatus('error')
        setSubmitMsg(data.error ?? 'Failed to record transaction.')
      }
    } catch {
      setSubmitStatus('error')
      setSubmitMsg('Failed to connect to the gateway.')
    }
  }

  async function handleDelete(id: string) {
    setDeletingId(id)
    try {
      const res = await fetch(`${GATEWAY}/fn/finance`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ id }),
      })
      if (res.ok) await fetchAll()
    } finally {
      setDeletingId(null)
    }
  }

  const balancePositive = summary ? Number(summary.balance) >= 0 : true

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      {/* Summary */}
      <div className="grid grid-cols-3 gap-4">
        <SummaryCard
          label="Balance"
          value={summary ? formatBRL(summary.balance) : '—'}
          icon={DollarSign}
          positive={balancePositive}
          loading={loadingData}
        />
        <SummaryCard
          label="Income"
          value={summary ? formatBRL(summary.total_income) : '—'}
          icon={TrendingUp}
          positive
          loading={loadingData}
        />
        <SummaryCard
          label="Expenses"
          value={summary ? formatBRL(summary.total_expenses) : '—'}
          icon={TrendingDown}
          positive={false}
          loading={loadingData}
        />
      </div>

      {/* Form */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">New Transaction</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="flex gap-2">
              {(['income', 'expense'] as const).map(t => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setType(t)}
                  className={cn(
                    'flex-1 rounded-md border py-2 text-sm font-medium transition-colors',
                    type === t
                      ? t === 'income'
                        ? 'border-green-500 bg-green-50 text-green-700 dark:border-green-700 dark:bg-green-950 dark:text-green-300'
                        : 'border-red-500 bg-red-50 text-red-700 dark:border-red-700 dark:bg-red-950 dark:text-red-300'
                      : 'border-input bg-transparent text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                  )}
                >
                  {t === 'income' ? 'Income' : 'Expense'}
                </button>
              ))}
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="amount">Amount (R$)</Label>
                <Input
                  id="amount"
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="0.00"
                  value={amount}
                  onChange={e => setAmount(e.target.value)}
                  required
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="date">Date</Label>
                <Input
                  id="date"
                  type="date"
                  value={date}
                  onChange={e => setDate(e.target.value)}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label>Category</Label>
                <Select value={category} onValueChange={setCategory} required>
                  <SelectTrigger>
                    <SelectValue placeholder="Select category" />
                  </SelectTrigger>
                  <SelectContent>
                    {CATEGORIES[type].map(c => (
                      <SelectItem key={c} value={c}>{c}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  placeholder="e.g. Supermarket"
                  value={description}
                  onChange={e => setDescription(e.target.value)}
                  required
                />
              </div>
            </div>

            {submitStatus !== 'idle' && submitStatus !== 'loading' && (
              <div
                className={cn(
                  'flex items-center gap-2 rounded-md border px-3 py-2 text-sm',
                  submitStatus === 'success'
                    ? 'border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200'
                    : 'border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200'
                )}
              >
                {submitStatus === 'success' ? (
                  <CheckCircle className="h-4 w-4 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 shrink-0" />
                )}
                {submitMsg}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={submitStatus === 'loading' || !category}
            >
              {submitStatus === 'loading' ? (
                <><Loader2 className="h-4 w-4 animate-spin" /> Saving...</>
              ) : (
                <><Plus className="h-4 w-4" /> Record transaction</>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* List */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">
            Transactions
            {summary && (
              <span className="ml-2 text-sm font-normal text-muted-foreground">
                {summary.transaction_count} total
              </span>
            )}
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loadingData ? (
            <div className="flex justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : transactions.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No transactions yet.
            </p>
          ) : (
            <ul className="divide-y">
              {transactions.map(tx => (
                <li key={tx.id} className="flex items-center gap-3 py-3">
                  <div
                    className={cn(
                      'flex h-8 w-8 shrink-0 items-center justify-center rounded-full text-xs font-semibold',
                      tx.type === 'income'
                        ? 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300'
                        : 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300'
                    )}
                  >
                    {tx.category.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{tx.description}</p>
                    <p className="text-xs text-muted-foreground">
                      {tx.category} · {formatDate(tx.date)}
                    </p>
                  </div>
                  <span
                    className={cn(
                      'text-sm font-semibold tabular-nums',
                      tx.type === 'income'
                        ? 'text-green-600 dark:text-green-400'
                        : 'text-red-600 dark:text-red-400'
                    )}
                  >
                    {tx.type === 'income' ? '+' : '−'}{formatBRL(tx.amount.amount)}
                  </span>
                  <button
                    onClick={() => handleDelete(tx.id)}
                    disabled={deletingId === tx.id}
                    className="ml-1 rounded p-1 text-muted-foreground opacity-40 transition-opacity hover:opacity-100 hover:text-destructive disabled:opacity-20"
                  >
                    {deletingId === tx.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Trash2 className="h-4 w-4" />
                    )}
                  </button>
                </li>
              ))}
            </ul>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function SummaryCard({
  label,
  value,
  icon: Icon,
  positive,
  loading,
}: {
  label: string
  value: string
  icon: React.ElementType
  positive: boolean
  loading: boolean
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="mb-2 flex items-center justify-between">
          <p className="text-sm text-muted-foreground">{label}</p>
          <Icon className={cn('h-4 w-4', positive ? 'text-green-500' : 'text-red-500')} />
        </div>
        {loading ? (
          <div className="h-7 w-24 animate-pulse rounded bg-muted" />
        ) : (
          <p
            className={cn(
              'text-xl font-bold',
              positive ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400'
            )}
          >
            {value}
          </p>
        )}
      </CardContent>
    </Card>
  )
}

export const financeMeta = {
  id: 'finance' as const,
  label: 'Finance',
  description: 'Track income and expenses',
  icon: DollarSign,
  badge: <Badge variant="outline">New</Badge>,
}
