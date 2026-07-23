import { useState, useEffect, useCallback } from 'react'
import { Send, Loader2, Trash2, CalendarClock, Zap } from 'lucide-react'
import { Skeleton } from 'boneyard-js/react'
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'

const GATEWAY = import.meta.env.VITE_GATEWAY_URL

interface Config {
  send_time: string
  reference_day_offset: number
  enabled: boolean
  realtime_alerts_enabled: boolean
  realtime_edge_threshold: number
}

interface Recipient {
  id: number
  phone_number: string
  name: string | null
  active: boolean
  realtime_alerts: boolean
}

function referenceDayLabel(offset: number) {
  if (offset === 0) return 'hoje'
  if (offset === 1) return 'amanhã'
  return `em ${offset} dias`
}

export function ValueBetsReportModule() {
  const [config, setConfig] = useState<Config | null>(null)
  const [loadingConfig, setLoadingConfig] = useState(true)
  const [savingConfig, setSavingConfig] = useState(false)

  const [recipients, setRecipients] = useState<Recipient[]>([])
  const [loadingRecipients, setLoadingRecipients] = useState(true)
  const [newPhone, setNewPhone] = useState('')
  const [newName, setNewName] = useState('')
  const [newRealtimeAlerts, setNewRealtimeAlerts] = useState(false)
  const [addingRecipient, setAddingRecipient] = useState(false)
  const [togglingId, setTogglingId] = useState<number | null>(null)
  const [deletingId, setDeletingId] = useState<number | null>(null)

  const [sending, setSending] = useState(false)
  const [sentAt, setSentAt] = useState<Date | null>(null)

  const fetchConfig = useCallback(async () => {
    setLoadingConfig(true)
    const res = await fetch(`${GATEWAY}/value-bets-report/config`)
    if (res.ok) setConfig(await res.json())
    setLoadingConfig(false)
  }, [])

  const fetchRecipients = useCallback(async () => {
    setLoadingRecipients(true)
    const res = await fetch(`${GATEWAY}/value-bets-report/recipients`)
    if (res.ok) setRecipients(await res.json())
    setLoadingRecipients(false)
  }, [])

  useEffect(() => { fetchConfig() }, [fetchConfig])
  useEffect(() => { fetchRecipients() }, [fetchRecipients])

  async function saveConfig() {
    if (!config) return
    setSavingConfig(true)
    try {
      const res = await fetch(`${GATEWAY}/value-bets-report/config`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(config),
      })
      if (res.ok) setConfig(await res.json())
    } finally {
      setSavingConfig(false)
    }
  }

  async function addRecipient() {
    if (!newPhone) return
    setAddingRecipient(true)
    try {
      const res = await fetch(`${GATEWAY}/value-bets-report/recipients`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone_number: newPhone, name: newName || null, realtime_alerts: newRealtimeAlerts }),
      })
      if (res.ok) {
        await fetchRecipients()
        setNewPhone('')
        setNewName('')
        setNewRealtimeAlerts(false)
      }
    } finally {
      setAddingRecipient(false)
    }
  }

  async function toggleRecipient(recipient: Recipient) {
    setTogglingId(recipient.id)
    try {
      const res = await fetch(`${GATEWAY}/value-bets-report/recipients/${recipient.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ active: !recipient.active }),
      })
      if (res.ok) await fetchRecipients()
    } finally {
      setTogglingId(null)
    }
  }

  async function toggleRealtimeAlerts(recipient: Recipient) {
    setTogglingId(recipient.id)
    try {
      const res = await fetch(`${GATEWAY}/value-bets-report/recipients/${recipient.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ realtime_alerts: !recipient.realtime_alerts }),
      })
      if (res.ok) await fetchRecipients()
    } finally {
      setTogglingId(null)
    }
  }

  async function removeRecipient(id: number) {
    setDeletingId(id)
    try {
      const res = await fetch(`${GATEWAY}/value-bets-report/recipients/${id}`, { method: 'DELETE' })
      if (res.ok) await fetchRecipients()
    } finally {
      setDeletingId(null)
    }
  }

  async function sendNow() {
    setSending(true)
    try {
      const res = await fetch(`${GATEWAY}/value-bets-report/trigger`, { method: 'POST' })
      if (res.ok) setSentAt(new Date())
    } finally {
      setSending(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 max-w-2xl">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-xs text-muted-foreground">
            {config ? `Envio diário às ${config.send_time} com as value bets de ${referenceDayLabel(config.reference_day_offset)}` : ''}
          </p>
          {sentAt && (
            <p className="text-xs text-success mt-0.5">
              Enviado às {sentAt.toLocaleTimeString('pt-BR')}
            </p>
          )}
        </div>
        <Button onClick={sendNow} disabled={sending} size="sm">
          {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
          {sending ? 'Enviando...' : 'Enviar agora'}
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <CalendarClock className="h-4 w-4" />
            Agendamento
          </CardTitle>
          <CardDescription>Horário e dia de referência do relatório automático</CardDescription>
        </CardHeader>
        <CardContent>
          {loadingConfig || !config ? (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          ) : (
            <div className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <Label htmlFor="vbr-enabled">Ativo</Label>
                <Switch
                  id="vbr-enabled"
                  checked={config.enabled}
                  onCheckedChange={checked => setConfig(c => c && { ...c, enabled: checked })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="vbr-time">Horário de envio</Label>
                <Input
                  id="vbr-time"
                  type="time"
                  value={config.send_time}
                  onChange={e => setConfig(c => c && { ...c, send_time: e.target.value })}
                  className="w-32"
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="vbr-offset">Dia de referência</Label>
                <Input
                  id="vbr-offset"
                  type="number"
                  min={0}
                  value={config.reference_day_offset}
                  onChange={e => setConfig(c => c && { ...c, reference_day_offset: parseInt(e.target.value, 10) || 0 })}
                  className="w-32"
                />
                <p className="text-xs text-muted-foreground">0 = hoje, 1 = amanhã</p>
              </div>
              <div className="flex items-center justify-between pt-2 border-t">
                <Label htmlFor="vbr-realtime-enabled">Alertas em tempo real</Label>
                <Switch
                  id="vbr-realtime-enabled"
                  checked={config.realtime_alerts_enabled}
                  onCheckedChange={checked => setConfig(c => c && { ...c, realtime_alerts_enabled: checked })}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <Label htmlFor="vbr-realtime-threshold">Edge mínimo para alerta instantâneo (%)</Label>
                <Input
                  id="vbr-realtime-threshold"
                  type="number"
                  min={0}
                  max={100}
                  step={0.1}
                  value={(config.realtime_edge_threshold * 100).toFixed(1)}
                  onChange={e => setConfig(c => c && { ...c, realtime_edge_threshold: (parseFloat(e.target.value) || 0) / 100 })}
                  className="w-32"
                />
              </div>
              <Button onClick={saveConfig} disabled={savingConfig} size="sm" className="w-fit">
                {savingConfig ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                Salvar
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Destinatários</CardTitle>
          <CardDescription>Números de WhatsApp que recebem o relatório</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col gap-2">
            <Skeleton
              name="vbr-recipients"
              loading={loadingRecipients}
              fixture={
                <div className="flex flex-col gap-2">
                  {['Gio', '5511999999999'].map(name => (
                    <div key={name} className="flex items-center justify-between rounded-md border px-3 py-2">
                      <p className="text-sm font-medium">{name}</p>
                      <div className="flex items-center gap-3">
                        <div className="h-5 w-9 rounded-full bg-muted" />
                        <div className="h-5 w-9 rounded-full bg-muted" />
                      </div>
                    </div>
                  ))}
                </div>
              }
            >
              {recipients.length === 0 ? (
                <p className="text-sm text-muted-foreground">Nenhum destinatário cadastrado.</p>
              ) : (
                <div className="flex flex-col gap-2">
                  {recipients.map(r => (
                    <div key={r.id} className="flex items-center justify-between rounded-md border px-3 py-2">
                      <div>
                        <p className="text-sm font-medium">{r.name || r.phone_number}</p>
                        {r.name && <p className="text-xs text-muted-foreground">{r.phone_number}</p>}
                      </div>
                      <div className="flex items-center gap-3">
                        <div className="flex items-center gap-1.5" title="Alertas em tempo real">
                          <Zap className={r.realtime_alerts ? 'h-3.5 w-3.5 text-warning' : 'h-3.5 w-3.5 text-muted-foreground/40'} />
                          <Switch
                            checked={r.realtime_alerts}
                            disabled={togglingId === r.id}
                            onCheckedChange={() => toggleRealtimeAlerts(r)}
                          />
                        </div>
                        <Switch
                          checked={r.active}
                          disabled={togglingId === r.id}
                          onCheckedChange={() => toggleRecipient(r)}
                        />
                        <button
                          onClick={() => removeRecipient(r.id)}
                          disabled={deletingId === r.id}
                          className="rounded p-1 text-muted-foreground hover:text-destructive transition-colors disabled:opacity-30"
                        >
                          {deletingId === r.id ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Trash2 className="h-3.5 w-3.5" />}
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Skeleton>

            <div className="flex items-end gap-2 mt-2">
              <div className="flex flex-col gap-1.5 flex-1">
                <Label htmlFor="vbr-new-phone">Telefone</Label>
                <Input
                  id="vbr-new-phone"
                  placeholder="5511999999999"
                  value={newPhone}
                  onChange={e => setNewPhone(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5 flex-1">
                <Label htmlFor="vbr-new-name">Nome (opcional)</Label>
                <Input
                  id="vbr-new-name"
                  placeholder="Gio"
                  value={newName}
                  onChange={e => setNewName(e.target.value)}
                />
              </div>
              <div className="flex items-center gap-1.5 pb-2" title="Alertas em tempo real">
                <Zap className={newRealtimeAlerts ? 'h-3.5 w-3.5 text-warning' : 'h-3.5 w-3.5 text-muted-foreground/40'} />
                <Switch checked={newRealtimeAlerts} onCheckedChange={setNewRealtimeAlerts} />
              </div>
              <Button onClick={addRecipient} disabled={addingRecipient || !newPhone} size="sm">
                {addingRecipient ? <Loader2 className="h-4 w-4 animate-spin" /> : 'Adicionar'}
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export const valueBetsReportMeta = {
  id: 'value-bets-report' as const,
  label: 'Value Bets Report',
  description: 'Relatório diário de value bets no WhatsApp',
  icon: CalendarClock,
}
