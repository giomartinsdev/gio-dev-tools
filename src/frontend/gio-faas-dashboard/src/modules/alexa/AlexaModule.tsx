import { useEffect, useRef, useState } from 'react'
import { Mic, Send, AlertCircle, ExternalLink, CheckCircle2, ClipboardPaste } from 'lucide-react'
import { cn } from '@/lib/utils'

const GW = import.meta.env.VITE_GATEWAY_URL

interface Device { name: string; type: string; serial: string }
interface CommandEntry {
  id: string; text: string; device: string
  timestamp: Date; status: 'pending' | 'sent' | 'error'; error?: string
}

export function AlexaModule() {
  const [authenticated, setAuthenticated] = useState<boolean | null>(null)
  const [startUrl, setStartUrl] = useState<string | null>(null)
  const [waitingAuth, setWaitingAuth] = useState(false)
  const [pasteUrl, setPasteUrl] = useState('')
  const [pasteError, setPasteError] = useState<string | null>(null)
  const [pasteLoading, setPasteLoading] = useState(false)

  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState('')
  const [devicesError, setDevicesError] = useState<string | null>(null)
  const [history, setHistory] = useState<CommandEntry[]>([])
  const [inputText, setInputText] = useState('')
  const [lastSent, setLastSent] = useState<string | null>(null)
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const pasteRef = useRef<HTMLInputElement>(null)

  async function fetchStatus() {
    try {
      const r = await fetch(`${GW}/alexa/auth/status`)
      const data = await r.json()
      setAuthenticated(data.authenticated)
      setStartUrl(data.start_url ?? null)
      return data.authenticated as boolean
    } catch {
      setAuthenticated(false)
      return false
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
      setDevicesError(e instanceof Error ? e.message : 'failed')
    }
  }

  function openLogin() {
    if (!startUrl) return
    window.open(startUrl, '_blank', 'noopener,noreferrer,width=600,height=700')
    setWaitingAuth(true)
    setTimeout(() => pasteRef.current?.focus(), 800)
  }

  async function handlePasteFocus() {
    try {
      const text = await navigator.clipboard.readText()
      if (text.includes('openid.oa2.authorization_code') || text.includes('maplanding')) {
        setPasteUrl(text)
      }
    } catch {
      // clipboard permission denied — user types manually
    }
  }

  async function submitUrl(url: string) {
    const trimmed = url.trim()
    if (!trimmed) return
    setPasteLoading(true)
    setPasteError(null)
    try {
      const r = await fetch(`${GW}/alexa/auth/finalize`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmed }),
      })
      if (r.ok) {
        await fetchStatus()
        await loadDevices()
        setWaitingAuth(false)
      } else {
        const err = await r.json().catch(() => ({ detail: 'error' }))
        setPasteError(err.detail ?? 'Authentication failed')
      }
    } catch (e: unknown) {
      setPasteError(e instanceof Error ? e.message : 'network error')
    } finally {
      setPasteLoading(false)
    }
  }

  function handlePasteChange(e: React.ChangeEvent<HTMLInputElement>) {
    const val = e.target.value
    setPasteUrl(val)
    // auto-submit when a valid maplanding URL is pasted
    if (val.includes('openid.oa2.authorization_code') || (val.includes('maplanding') && val.includes('code='))) {
      submitUrl(val)
    }
  }

  useEffect(() => {
    fetchStatus().then(ok => { if (ok) loadDevices() })
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

  useEffect(() => {
    if (!lastSent) return
    const t = setTimeout(() => setLastSent(null), 3000)
    return () => clearTimeout(t)
  }, [lastSent])

  async function sendCommand() {
    const text = inputText.trim()
    if (!text || sending) return

    const entry: CommandEntry = {
      id: crypto.randomUUID(), text, device: selectedDevice,
      timestamp: new Date(), status: 'pending',
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
      if (res.ok) {
        setHistory(prev => prev.map(e => e.id === entry.id ? { ...e, status: 'sent' } : e))
        setLastSent(text)
      } else {
        const err = await res.json().catch(() => ({ detail: 'error' }))
        setHistory(prev => prev.map(e => e.id === entry.id
          ? { ...e, status: 'error', error: err.detail ?? 'error' } : e))
      }
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : 'network error'
      setHistory(prev => prev.map(e => e.id === entry.id ? { ...e, status: 'error', error: msg } : e))
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendCommand() }
  }

  if (authenticated === null) {
    return <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Connecting…</div>
  }

  if (!authenticated) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-6 px-4 max-w-sm mx-auto">
        <div className="flex flex-col items-center gap-2 text-center">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <Mic className="h-6 w-6 text-primary" />
          </div>
          <h2 className="text-base font-semibold">Connect Amazon Account</h2>
          {!waitingAuth && (
            <p className="text-sm text-muted-foreground">
              Click the button to open Amazon login.
            </p>
          )}
        </div>

        {!waitingAuth ? (
          <button
            onClick={openLogin}
            disabled={!startUrl}
            className="flex items-center gap-2 rounded-md bg-primary px-6 py-2.5 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
          >
            <ExternalLink className="h-4 w-4" />
            Login with Amazon
          </button>
        ) : (
          <div className="flex w-full flex-col gap-3">
            <p className="text-sm text-muted-foreground text-center">
              After logging in, Amazon shows an error page — that's expected.<br />
              <strong>Copy the URL</strong> from the address bar and paste it below.
            </p>

            <div className="flex gap-2">
              <input
                ref={pasteRef}
                type="text"
                value={pasteUrl}
                onChange={handlePasteChange}
                onFocus={handlePasteFocus}
                placeholder="Paste the amazon.com/ap/maplanding?… URL"
                className="flex-1 h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground"
              />
              <button
                onClick={() => submitUrl(pasteUrl)}
                disabled={!pasteUrl.trim() || pasteLoading}
                className="flex items-center gap-1.5 rounded-md bg-primary px-3 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
              >
                <ClipboardPaste className="h-4 w-4" />
                {pasteLoading ? '…' : 'OK'}
              </button>
            </div>

            {pasteError && (
              <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-xs text-destructive">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" />{pasteError}
              </div>
            )}

            <button
              onClick={openLogin}
              className="text-xs text-muted-foreground underline underline-offset-2 hover:text-foreground"
            >
              Re-open Amazon login
            </button>
          </div>
        )}
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
            <option key={d.serial} value={d.name}>{d.name} ({d.type})</option>
          ))}
        </select>
      </div>

      {devicesError && (
        <div className="flex items-center gap-2 rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <AlertCircle className="h-4 w-4 shrink-0" />{devicesError}
        </div>
      )}

      {lastSent && (
        <div className="flex items-center gap-2 rounded-md border border-green-500/30 bg-green-500/10 px-3 py-2 text-sm text-green-700 dark:text-green-400">
          <CheckCircle2 className="h-4 w-4 shrink-0" />
          <span>Command sent: <span className="font-medium">"{lastSent}"</span></span>
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
                  <div className={cn(
                    'max-w-[75%] rounded-xl px-4 py-2.5 text-sm shadow-sm',
                    entry.status === 'error'
                      ? 'bg-destructive/10 text-destructive border border-destructive/30'
                      : entry.status === 'pending'
                      ? 'bg-primary/60 text-primary-foreground'
                      : 'bg-primary text-primary-foreground'
                  )}>
                    {entry.text}
                    {entry.error && <p className="mt-1 text-xs opacity-80">{entry.error}</p>}
                  </div>
                  <div className="flex items-center gap-2 px-1">
                    <span className="text-xs text-muted-foreground">{entry.device}</span>
                    <span className={cn(
                      'rounded-full px-1.5 py-0.5 text-xs font-medium',
                      entry.status === 'error' ? 'bg-destructive/10 text-destructive'
                        : entry.status === 'pending' ? 'bg-muted text-muted-foreground'
                        : 'bg-green-500/10 text-green-600 dark:text-green-400'
                    )}>
                      {entry.status === 'error' ? 'error' : entry.status === 'pending' ? 'sending…' : 'sent ✓'}
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
