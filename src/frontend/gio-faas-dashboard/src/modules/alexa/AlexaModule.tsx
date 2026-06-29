import { useEffect, useRef, useState } from 'react'
import { Mic, Send, AlertCircle, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'

const GW = import.meta.env.VITE_GATEWAY_URL

interface Device {
  name: string
  type: string
  serial: string
}

interface CommandEntry {
  id: string
  text: string
  device: string
  timestamp: Date
  status: 'sent' | 'error'
  error?: string
}

export function AlexaModule() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [startUrl, setStartUrl] = useState<string | null>(null)
  const [callbackUrl, setCallbackUrl] = useState('')
  const [finalizing, setFinalizing] = useState(false)
  const [finalizeError, setFinalizeError] = useState<string | null>(null)

  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string>('')
  const [devicesError, setDevicesError] = useState<string | null>(null)
  const [history, setHistory] = useState<CommandEntry[]>([])
  const [inputText, setInputText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  async function checkAuth() {
    try {
      const r = await fetch(`${GW}/alexa/auth/status`)
      const data = await r.json()
      setAuthenticated(data.authenticated)
      setStartUrl(data.start_url ?? null)
      if (data.authenticated) loadDevices()
    } catch {
      setAuthenticated(false)
    }
  }

  async function loadDevices() {
    try {
      const r = await fetch(`${GW}/alexa/devices`)
      if (!r.ok) throw new Error(`${r.status}`)
      const data: Device[] = await r.json()
      setDevices(data)
      if (data.length > 0) setSelectedDevice(data[0].name)
    } catch (e: unknown) {
      setDevicesError(e instanceof Error ? e.message : 'failed to load devices')
    }
  }

  useEffect(() => { checkAuth() }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  async function finalize() {
    if (!callbackUrl.trim() || finalizing) return
    setFinalizing(true)
    setFinalizeError(null)
    try {
      const r = await fetch(`${GW}/alexa/auth/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: callbackUrl.trim() }),
      })
      const data = await r.json()
      if (!r.ok) {
        setFinalizeError(data.detail ?? 'failed')
        return
      }
      setCallbackUrl('')
      checkAuth()
    } catch {
      setFinalizeError('network error')
    } finally {
      setFinalizing(false)
    }
  }

  async function sendCommand() {
    const text = inputText.trim()
    if (!text || sending) return

    const entry: CommandEntry = {
      id: crypto.randomUUID(),
      text,
      device: selectedDevice,
      timestamp: new Date(),
      status: 'sent',
    }

    setHistory(prev => [...prev, entry])
    setInputText('')
    setSending(true)

    try {
      const res = await fetch(`${GW}/alexa/command`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, device_name: selectedDevice }),
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'request failed' }))
        setHistory(prev =>
          prev.map(e => e.id === entry.id ? { ...e, status: 'error', error: err.detail ?? 'request failed' } : e)
        )
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'network error'
      setHistory(prev =>
        prev.map(e => e.id === entry.id ? { ...e, status: 'error', error: msg } : e)
      )
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendCommand()
    }
  }

  if (authenticated === null) {
    return <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Connecting…</div>
  }

  if (!authenticated) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 px-4">
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Mic className="h-6 w-6 text-primary" />
          </div>
          <h2 className="text-base font-semibold">Connect Amazon Account</h2>
          <p className="text-sm text-muted-foreground max-w-sm">
            Log in with your Amazon account, then paste the redirect URL to complete setup.
          </p>
        </div>

        <div className="flex w-full max-w-md flex-col gap-4">
          <div className="rounded-lg border bg-muted/30 p-4 flex flex-col gap-3">
            <p className="text-sm font-medium">Step 1 — Open Amazon login</p>
            <a
              href={startUrl ?? '#'}
              target="_blank"
              rel="noopener noreferrer"
              className={cn(
                'flex items-center justify-center gap-2 rounded-md py-2 text-sm font-medium transition-colors',
                startUrl
                  ? 'bg-primary text-primary-foreground hover:bg-primary/90'
                  : 'bg-muted text-muted-foreground cursor-not-allowed pointer-events-none'
              )}
            >
              <ExternalLink className="h-4 w-4" />
              Login with Amazon
            </a>
          </div>

          <div className="rounded-lg border bg-muted/30 p-4 flex flex-col gap-3">
            <p className="text-sm font-medium">Step 2 — Paste the redirect URL</p>
            <p className="text-xs text-muted-foreground">
              After logging in, the browser will redirect to a page at <code className="bg-muted px-1 rounded">amazon.com/ap/maplanding</code>.
              Copy the full URL from the address bar and paste it below.
            </p>
            <textarea
              rows={3}
              className="w-full resize-none rounded-md border bg-background px-3 py-2 text-xs font-mono focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground"
              placeholder="https://www.amazon.com/ap/maplanding?openid.oa2.authorization_code=..."
              value={callbackUrl}
              onChange={e => setCallbackUrl(e.target.value)}
            />
            {finalizeError && (
              <div className="flex items-center gap-2 text-sm text-destructive">
                <AlertCircle className="h-4 w-4 shrink-0" />
                {finalizeError}
              </div>
            )}
            <button
              onClick={finalize}
              disabled={!callbackUrl.trim() || finalizing}
              className="rounded-md bg-primary py-2 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors"
            >
              {finalizing ? 'Connecting…' : 'Complete Setup'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col gap-4">
      <div className="flex items-center gap-3">
        <select
          value={selectedDevice}
          onChange={e => setSelectedDevice(e.target.value)}
          disabled={devices.length === 0}
          className="h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring disabled:opacity-50"
        >
          {devices.length === 0 && <option value="">No devices</option>}
          {devices.map(d => (
            <option key={d.serial} value={d.name}>
              {d.name} ({d.type})
            </option>
          ))}
        </select>
      </div>

      {devicesError && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />
          <span>Could not load devices: {devicesError}</span>
        </div>
      )}

      <div className="flex flex-1 flex-col overflow-hidden rounded-lg border bg-muted/20">
        <div className="flex-1 overflow-y-auto px-4 py-4">
          {history.length === 0 ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
              <Mic className="h-10 w-10 opacity-20" />
              <p className="text-sm">Send a command to your Echo device</p>
            </div>
          ) : (
            <div className="flex flex-col gap-3">
              {history.map(entry => (
                <div key={entry.id} className="flex flex-col items-end gap-1">
                  <div
                    className={cn(
                      'max-w-[75%] rounded-xl px-4 py-2.5 text-sm shadow-sm',
                      entry.status === 'error'
                        ? 'bg-destructive/10 text-destructive border border-destructive/30'
                        : 'bg-primary text-primary-foreground'
                    )}
                  >
                    {entry.text}
                    {entry.status === 'error' && entry.error && (
                      <p className="mt-1 text-xs opacity-80">{entry.error}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-2 px-1">
                    <span className="text-xs text-muted-foreground">{entry.device}</span>
                    <span
                      className={cn(
                        'rounded-full px-1.5 py-0.5 text-xs font-medium',
                        entry.status === 'error'
                          ? 'bg-destructive/10 text-destructive'
                          : 'bg-green-500/10 text-green-600 dark:text-green-400'
                      )}
                    >
                      {entry.status === 'error' ? 'error' : 'sent'}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {entry.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>
              ))}
              <div ref={bottomRef} />
            </div>
          )}
        </div>

        <div className="border-t bg-background px-3 py-3">
          <div className="flex items-end gap-2">
            <textarea
              rows={2}
              className="flex-1 resize-none rounded-md border bg-muted/30 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground"
              placeholder="Type a command… (Enter to send, Shift+Enter for new line)"
              value={inputText}
              onChange={e => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
            />
            <button
              onClick={sendCommand}
              disabled={!inputText.trim() || sending}
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

export const alexaMeta = {
  id: 'alexa',
  label: 'Alexa',
  description: 'Send voice commands to your Echo device',
  icon: Mic,
}
