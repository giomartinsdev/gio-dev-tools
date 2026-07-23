import { useCallback, useEffect, useRef, useState } from 'react'
import { MessageSquare, RefreshCw, Send } from 'lucide-react'
import { Skeleton } from 'boneyard-js/react'
import { cn } from '@/lib/utils'

const GW = import.meta.env.VITE_GATEWAY_URL

interface Chat {
  remote_jid: string
  contact_name: string | null
  total_messages: number
  last_message_at: string
  last_message_text: string | null
}

interface Message {
  id: number
  event: string
  remote_jid: string | null
  from_me: boolean | null
  payload: Record<string, unknown>
  received_at: string
}

type MsgData = Record<string, unknown>

function extractText(msg: Message): string {
  const data = (msg.payload?.data ?? {}) as MsgData
  const message = (data?.message ?? {}) as MsgData
  return (
    (message?.conversation as string) ||
    ((message?.extendedTextMessage as MsgData)?.text as string) ||
    '[media]'
  )
}

function displayName(chat: Chat): string {
  return chat.contact_name || chat.remote_jid.split('@')[0]
}

function fmtTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

function fmtDate(iso: string): string {
  const d = new Date(iso)
  return d.toDateString() === new Date().toDateString()
    ? fmtTime(iso)
    : d.toLocaleDateString([], { day: '2-digit', month: '2-digit' })
}

export function WhatsappModule() {
  const [chats, setChats] = useState<Chat[]>([])
  const [selectedJid, setSelectedJid] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [text, setText] = useState('')
  const [sending, setSending] = useState(false)
  const [loadingChats, setLoadingChats] = useState(true)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  const loadChats = useCallback(async () => {
    setLoadingChats(true)
    try {
      const r = await fetch(`${GW}/whatsapp/chats`)
      if (r.ok) setChats(await r.json())
    } finally {
      setLoadingChats(false)
    }
  }, [])

  const loadMessages = useCallback(async (jid: string) => {
    const r = await fetch(`${GW}/whatsapp/messages/${encodeURIComponent(jid)}`)
    if (r.ok) setMessages(await r.json())
  }, [])

  useEffect(() => { loadChats() }, [loadChats])

  useEffect(() => {
    if (!selectedJid) return
    setMessages([])
    loadMessages(selectedJid)
  }, [selectedJid, loadMessages])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // SSE for real-time updates
  useEffect(() => {
    const es = new EventSource(`${GW}/whatsapp/events`)
    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data as string) as Record<string, unknown>
        const event = (msg.event as string) || ''
        if (!['messages.upsert', 'send.message'].includes(event)) return

        const data = (msg.data ?? {}) as MsgData
        const key = (data.key ?? {}) as MsgData
        const jid = key.remoteJid as string | null

        loadChats()
        if (jid && jid === selectedJid) {
          loadMessages(jid)
        }
      } catch { /* ignore malformed */ }
    }
    return () => es.close()
  }, [selectedJid, loadChats, loadMessages])

  async function send() {
    if (!text.trim() || !selectedJid || sending) return
    setSending(true)
    const number = selectedJid.split('@')[0]
    try {
      await fetch(`${GW}/whatsapp/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ number, text: text.trim() }),
      })
      setText('')
      inputRef.current?.focus()
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const selectedChat = chats.find(c => c.remote_jid === selectedJid)

  return (
    <div className="flex h-full rounded-[14px] border shadow-[var(--shadow-card)] overflow-hidden">
      {/* Chat list */}
      <aside className="w-72 shrink-0 border-r flex flex-col bg-sidebar">
        <div className="flex items-center justify-between px-4 py-3 border-b">
          <span className="font-medium text-sm text-sidebar-foreground">Conversas</span>
          <button
            onClick={loadChats}
            className="text-muted-foreground hover:text-foreground transition-colors"
            title="Atualizar"
          >
            <RefreshCw className={cn('h-3.5 w-3.5', loadingChats && 'animate-spin')} />
          </button>
        </div>

        <Skeleton
          name="whatsapp-chats"
          loading={loadingChats}
          className="flex-1 overflow-y-auto"
          fixture={
            <div>
              {['Fulano', 'Ciclana', 'Suporte'].map(name => (
                <div key={name} className="flex flex-col gap-0.5 px-4 py-3 border-b text-left">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium">{name}</span>
                    <span className="text-[10px] text-muted-foreground shrink-0">12:00</span>
                  </div>
                  <span className="text-xs text-muted-foreground truncate">Última mensagem de exemplo</span>
                </div>
              ))}
            </div>
          }
        >
          <div className="flex-1 overflow-y-auto">
            {chats.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground py-8">
                <MessageSquare className="h-8 w-8 opacity-20" />
                <p className="text-sm">Sem conversas</p>
              </div>
            ) : (
              chats.map(chat => (
                <button
                  key={chat.remote_jid}
                  onClick={() => setSelectedJid(chat.remote_jid)}
                  className={cn(
                    'w-full flex flex-col gap-0.5 px-4 py-3 border-b text-left transition-colors',
                    selectedJid === chat.remote_jid
                      ? 'bg-sidebar-accent'
                      : 'hover:bg-sidebar-accent/50'
                  )}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-medium truncate text-sidebar-foreground">
                      {displayName(chat)}
                    </span>
                    <span className="text-[10px] text-muted-foreground shrink-0">
                      {fmtDate(chat.last_message_at)}
                    </span>
                  </div>
                  {chat.last_message_text && (
                    <span className="text-xs text-muted-foreground truncate">
                      {chat.last_message_text}
                    </span>
                  )}
                </button>
              ))
            )}
          </div>
        </Skeleton>
      </aside>

      {/* Message area */}
      <div className="flex flex-1 flex-col overflow-hidden bg-background">
        {!selectedJid ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 text-muted-foreground">
            <MessageSquare className="h-10 w-10 opacity-20" />
            <p className="text-sm">Selecione uma conversa</p>
          </div>
        ) : (
          <>
            {/* Chat header */}
            <div className="flex items-center gap-3 border-b px-4 py-3 shrink-0">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary shrink-0">
                {(selectedChat ? displayName(selectedChat) : '?')[0].toUpperCase()}
              </div>
              <div className="min-w-0">
                <p className="text-sm font-medium truncate">
                  {selectedChat ? displayName(selectedChat) : selectedJid}
                </p>
                <p className="text-xs text-muted-foreground truncate">{selectedJid}</p>
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1.5">
              {messages.map((msg) => {
                const isMe = msg.from_me === true
                const txt = extractText(msg)
                return (
                  <div key={msg.id} className={cn('flex', isMe ? 'justify-end' : 'justify-start')}>
                    <div className={cn(
                      'max-w-[72%] rounded-2xl px-3.5 py-2 text-sm shadow-sm',
                      isMe
                        ? 'bg-primary text-primary-foreground rounded-br-sm'
                        : 'bg-muted rounded-bl-sm'
                    )}>
                      <p className="break-words whitespace-pre-wrap">{txt}</p>
                      <p className={cn(
                        'mt-0.5 text-right text-[10px] leading-none',
                        isMe ? 'text-primary-foreground/60' : 'text-muted-foreground'
                      )}>
                        {fmtTime(msg.received_at)}
                      </p>
                    </div>
                  </div>
                )
              })}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="border-t px-3 py-3 shrink-0">
              <div className="flex items-end gap-2">
                <textarea
                  ref={inputRef}
                  rows={1}
                  className="flex-1 resize-none rounded-xl border bg-muted/30 px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring placeholder:text-muted-foreground max-h-32"
                  placeholder="Digite uma mensagem… (Enter para enviar)"
                  value={text}
                  onChange={e => setText(e.target.value)}
                  onKeyDown={handleKeyDown}
                />
                <button
                  onClick={send}
                  disabled={!text.trim() || sending}
                  className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40 transition-colors"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

export const whatsappMeta = {
  id: 'whatsapp' as const,
  label: 'WhatsApp',
  description: 'Conversas e mensagens do WhatsApp',
  icon: MessageSquare,
}
