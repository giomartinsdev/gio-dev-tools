import { useCallback, useEffect, useState } from 'react'
import { Settings as SettingsIcon, Plus, Pencil, Trash2, Check, X, Loader2 } from 'lucide-react'
import { Skeleton } from 'boneyard-js/react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { cn } from '@/lib/utils'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

const CATEGORIES = ['API', 'Worker', 'Integration', 'Storage', 'Other'] as const
type Category = typeof CATEGORIES[number]

const STATUSES = ['connected', 'disconnected', 'error'] as const
type Status = typeof STATUSES[number]

interface Service {
  id: string
  name: string
  category: Category
  status: Status
  secret_ref: string | null
  notes: string | null
  created_at: string | null
  updated_at: string | null
}

interface Draft {
  name: string
  category: Category
  status: Status
  secret_ref: string
  notes: string
}

function emptyDraft(): Draft {
  return { name: '', category: 'API', status: 'disconnected', secret_ref: '', notes: '' }
}

const STATUS_STYLE: Record<Status, string> = {
  connected: 'bg-success/15 text-success',
  disconnected: 'bg-muted text-muted-foreground',
  error: 'bg-destructive/15 text-destructive',
}

const STATUS_LABEL: Record<Status, string> = {
  connected: 'Conectado',
  disconnected: 'Desconectado',
  error: 'Erro',
}

export default function SettingsModule() {
  const [services, setServices] = useState<Service[]>([])
  const [loading, setLoading] = useState(true)
  const [creating, setCreating] = useState(false)
  const [draft, setDraft] = useState<Draft>(emptyDraft())
  const [submitting, setSubmitting] = useState(false)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editDraft, setEditDraft] = useState<Draft | null>(null)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch(`${GATEWAY}/settings/services`)
      if (res.ok) setServices(await res.json())
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  async function submitCreate() {
    if (!draft.name.trim()) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${GATEWAY}/settings/services`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(draft),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || 'Falha ao criar serviço')
      }
      setDraft(emptyDraft())
      setCreating(false)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao criar serviço')
    } finally {
      setSubmitting(false)
    }
  }

  function startEdit(s: Service) {
    setEditingId(s.id)
    setEditDraft({
      name: s.name,
      category: s.category,
      status: s.status,
      secret_ref: s.secret_ref ?? '',
      notes: s.notes ?? '',
    })
  }

  async function submitEdit() {
    if (!editingId || !editDraft) return
    setSubmitting(true)
    setError(null)
    try {
      const res = await fetch(`${GATEWAY}/settings/services/${editingId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(editDraft),
      })
      if (!res.ok) {
        const body = await res.json().catch(() => null)
        throw new Error(body?.detail || 'Falha ao atualizar serviço')
      }
      setEditingId(null)
      setEditDraft(null)
      await load()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Falha ao atualizar serviço')
    } finally {
      setSubmitting(false)
    }
  }

  async function remove(id: string) {
    setDeletingId(id)
    try {
      await fetch(`${GATEWAY}/settings/services/${id}`, { method: 'DELETE' })
      await load()
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-6 py-8">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="flex items-center gap-2 text-xl font-semibold tracking-tight">
            <SettingsIcon className="h-5 w-5 text-muted-foreground" />
            Configuração
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Cadastro de credenciais e integrações por serviço. As credenciais em si ficam no Infisical —
            aqui você registra só a referência.
          </p>
        </div>
        {!creating && (
          <Button size="sm" onClick={() => setCreating(true)}>
            <Plus className="h-4 w-4" />
            Novo serviço
          </Button>
        )}
      </div>

      {error && (
        <div className="mb-4 rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      {creating && (
        <div className="mb-5 rounded-[14px] border bg-card p-4 shadow-[var(--shadow-card)]">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Nome">
              <Input value={draft.name} onChange={e => setDraft(d => ({ ...d, name: e.target.value }))} placeholder="ex: bzzoiro" autoFocus />
            </Field>
            <Field label="Categoria">
              <Select value={draft.category} onValueChange={v => setDraft(d => ({ ...d, category: v as Category }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Status">
              <Select value={draft.status} onValueChange={v => setDraft(d => ({ ...d, status: v as Status }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {STATUSES.map(s => <SelectItem key={s} value={s}>{STATUS_LABEL[s]}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>
            <Field label="Referência do secret (Infisical)">
              <Input value={draft.secret_ref} onChange={e => setDraft(d => ({ ...d, secret_ref: e.target.value }))} placeholder="ex: BZZOIRO_API_KEY" />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Notas">
                <Input value={draft.notes} onChange={e => setDraft(d => ({ ...d, notes: e.target.value }))} placeholder="opcional" />
              </Field>
            </div>
          </div>
          <div className="mt-3 flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={() => { setCreating(false); setDraft(emptyDraft()); setError(null) }}>
              Cancelar
            </Button>
            <Button size="sm" onClick={submitCreate} disabled={submitting || !draft.name.trim()}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
              Salvar
            </Button>
          </div>
        </div>
      )}

      <Skeleton name="settings-list" loading={loading}>
        <div className="flex flex-col gap-2.5">
          {services.length === 0 && (
            <div className="rounded-[14px] border border-dashed p-8 text-center text-sm text-muted-foreground">
              Nenhum serviço cadastrado ainda.
            </div>
          )}
          {services.map(s => (
            <div key={s.id} className="rounded-[14px] border bg-card p-4 shadow-[var(--shadow-card)]">
              {editingId === s.id && editDraft ? (
                <div>
                  <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                    <Field label="Nome">
                      <Input value={editDraft.name} onChange={e => setEditDraft(d => d && { ...d, name: e.target.value })} />
                    </Field>
                    <Field label="Categoria">
                      <Select value={editDraft.category} onValueChange={v => setEditDraft(d => d && { ...d, category: v as Category })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {CATEGORIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="Status">
                      <Select value={editDraft.status} onValueChange={v => setEditDraft(d => d && { ...d, status: v as Status })}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {STATUSES.map(st => <SelectItem key={st} value={st}>{STATUS_LABEL[st]}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </Field>
                    <Field label="Referência do secret">
                      <Input value={editDraft.secret_ref} onChange={e => setEditDraft(d => d && { ...d, secret_ref: e.target.value })} />
                    </Field>
                  </div>
                  <div className="mt-3 flex justify-end gap-2">
                    <Button variant="outline" size="sm" onClick={() => { setEditingId(null); setEditDraft(null) }}>
                      <X className="h-4 w-4" />
                    </Button>
                    <Button size="sm" onClick={submitEdit} disabled={submitting}>
                      {submitting ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}
                    </Button>
                  </div>
                </div>
              ) : (
                <div className="flex items-center justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="truncate font-medium">{s.name}</span>
                      <span className={cn('rounded-full px-2 py-0.5 text-[11px] font-semibold', STATUS_STYLE[s.status])}>
                        {STATUS_LABEL[s.status]}
                      </span>
                      <span className="rounded-md border px-1.5 py-0.5 text-[10.5px] text-muted-foreground">{s.category}</span>
                    </div>
                    {s.secret_ref && (
                      <div className="mt-0.5 truncate font-mono text-xs text-muted-foreground">{s.secret_ref}</div>
                    )}
                  </div>
                  <div className="flex shrink-0 items-center gap-1">
                    <Button variant="ghost" size="icon" onClick={() => startEdit(s)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button variant="ghost" size="icon" onClick={() => remove(s.id)} disabled={deletingId === s.id}>
                      {deletingId === s.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                    </Button>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      </Skeleton>
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label>{label}</Label>
      {children}
    </div>
  )
}

export const settingsMeta = {
  id: 'settings' as const,
  label: 'Configuração',
  description: 'Cadastro de credenciais e integrações por serviço',
  icon: SettingsIcon,
}
