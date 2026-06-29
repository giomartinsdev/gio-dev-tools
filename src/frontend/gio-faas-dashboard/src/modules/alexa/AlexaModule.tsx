import { useEffect, useRef, useState } from 'react'
import { Mic, Send, AlertCircle } from 'lucide-react'
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
  const [devices, setDevices] = useState<Device[]>([])
  const [selectedDevice, setSelectedDevice] = useState<string>('')
  const [devicesError, setDevicesError] = useState<string | null>(null)
  const [history, setHistory] = useState<CommandEntry[]>([])
  const [inputText, setInputText] = useState('')
  const [sending, setSending] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    fetch(`${GW}/alexa/devices`)
      .then(r => {
        if (!r.ok) throw new Error(`${r.status} ${r.statusText}`)
        return r.json()
      })
      .then((data: Device[]) => {
        setDevices(data)
        if (data.length > 0) setSelectedDevice(data[0].name)
      })
      .catch(e => setDevicesError(e.message ?? 'Failed to load devices'))
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [history])

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
        const err = await res.json().catch(() => ({ error: 'request failed' }))
        setHistory(prev =>
          prev.map(e => e.id === entry.id ? { ...e, status: 'error', error: err.error ?? 'request failed' } : e)
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
          <span>Could not load devices: {devicesError}. You can still send commands manually.</span>
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
              disabled={!inputText.trim() || sending || (!selectedDevice && !devicesError)}
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
