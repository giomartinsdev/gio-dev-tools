import { useState, useEffect, useRef, useCallback } from 'react'
import { MessageCircle, Send, Check, CheckCheck } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

const API = `${import.meta.env.VITE_GATEWAY_URL}/fn/whatsapp`

interface Chat {
  jid: string
  name: string | null
  last_message_at: string | null
  last_message_text: string | null
  unread_count: number
}

interface Message {
  id: string
  chat_jid: string
  from_me: boolean
  text: string
  timestamp: string
  status: 'pending' | 'sent' | 'delivered' | 'read' | 'error'
}

function StatusTick({ status }: { status: Message['status'] }) {
  if (status === 'pending') return <Check className="h-3 w-3 text-green-200" />
  if (status === 'sent') return <Check className="h-3 w-3 text-green-200" />
  if (status === 'delivered') return <CheckCheck className="h-3 w-3 text-green-200" />
  if (status === 'read') return <CheckCheck className="h-3 w-3 text-blue-300" />
  return null
}

function formatTime(iso: string) {
  return new Date(iso).toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
}

function displayName(chat: Chat) {
  return chat.name ?? chat.jid.replace('@s.whatsapp.net', '')
}

export function WhatsappModule() {
  const [chats, setChats] = useState<Chat[]>([])
  const [selectedJid, setSelectedJid] = useState<string | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const selectedJidRef = useRef<string | null>(null)
  selectedJidRef.current = selectedJid

  const fetchChats = useCallback(async () => {
    try {
      const res = await fetch(`${API}?action=chats`)
      if (res.ok) setChats(await res.json())
    } catch {}
  }, [])

  const fetchMessages = useCallback(async (jid: string) => {
    try {
      const res = await fetch(`${API}?action=messages&jid=${encodeURIComponent(jid)}`)
      if (res.ok) setMessages(await res.json())
    } catch {}
  }, [])

  // Poll chats every 3s
  useEffect(() => {
    fetchChats()
    const t = setInterval(fetchChats, 3000)
    return () => clearInterval(t)
  }, [fetchChats])

  // Poll messages every 2s when a chat is open
  useEffect(() => {
    if (!selectedJid) return
    fetchMessages(selectedJid)
    const t = setInterval(() => {
      if (selectedJidRef.current) fetchMessages(selectedJidRef.current)
    }, 2000)
    return () => clearInterval(t)
  }, [selectedJid, fetchMessages])

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function openChat(jid: string) {
    if (jid === selectedJid) return
    setSelectedJid(jid)
    setMessages([])
    try {
      await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'read', jid }),
      })
      setChats(prev => prev.map(c => c.jid === jid ? { ...c, unread_count: 0 } : c))
    } catch {}
  }

  async function send() {
    if (!selectedJid || !input.trim() || sending) return
    const number = selectedJid.replace('@s.whatsapp.net', '')
    const text = input.trim()
    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
    setSending(true)
    try {
      await fetch(API, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ number, message: text }),
      })
      await fetchMessages(selectedJid)
    } catch {}
    setSending(false)
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  function handleInput(e: React.ChangeEvent<HTMLTextAreaElement>) {
    setInput(e.target.value)
    const ta = e.target
    ta.style.height = 'auto'
    ta.style.height = `${Math.min(ta.scrollHeight, 128)}px`
  }

  const selectedChat = chats.find(c => c.jid === selectedJid)

  return (
    <div className="flex h-full overflow-hidden -m-6">
      {/* Chat list */}
      <div className="w-72 shrink-0 border-r border-border flex flex-col bg-muted/20">
        <div className="px-4 py-3 border-b border-border">
          <p className="text-sm font-semibold">Conversas</p>
        </div>
        <div className="flex-1 overflow-y-auto">
          {chats.length === 0 ? (
            <div className="flex h-full items-center justify-center text-xs text-muted-foreground">
              Sem conversas
            </div>
          ) : (
            chats.map(chat => (
              <button
                key={chat.jid}
                onClick={() => openChat(chat.jid)}
                className={cn(
                  'w-full text-left px-4 py-3 border-b border-border/40 hover:bg-muted/40 transition-colors',
                  selectedJid === chat.jid && 'bg-muted'
                )}
              >
                <div className="flex items-center justify-between gap-2">
                  <span className="text-sm font-medium truncate">{displayName(chat)}</span>
                  {chat.unread_count > 0 && (
                    <span className="shrink-0 flex h-5 min-w-5 px-1 items-center justify-center rounded-full bg-green-500 text-white text-[10px] font-bold">
                      {chat.unread_count > 99 ? '99+' : chat.unread_count}
                    </span>
                  )}
                </div>
                {chat.last_message_text && (
                  <p className="text-xs text-muted-foreground truncate mt-0.5">
                    {chat.last_message_text}
                  </p>
                )}
              </button>
            ))
          )}
        </div>
      </div>

      {/* Message pane */}
      <div className="flex-1 flex flex-col min-w-0 bg-[url('data:image/svg+xml,%3Csvg%20xmlns%3D%22http%3A//www.w3.org/2000/svg%22/%3E')]">
        {selectedJid ? (
          <>
            <div className="px-4 py-3 border-b border-border bg-muted/20 shrink-0">
              <p className="text-sm font-semibold">{selectedChat ? displayName(selectedChat) : ''}</p>
              <p className="text-xs text-muted-foreground">
                {selectedJid.replace('@s.whatsapp.net', '')}
              </p>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-4 space-y-1.5">
              {messages.map(msg => (
                <div
                  key={msg.id}
                  className={cn('flex', msg.from_me ? 'justify-end' : 'justify-start')}
                >
                  <div
                    className={cn(
                      'max-w-xs lg:max-w-md xl:max-w-lg rounded-2xl px-3 py-2 text-sm shadow-sm',
                      msg.from_me
                        ? 'bg-green-500 text-white rounded-br-sm'
                        : 'bg-card border border-border/50 rounded-bl-sm'
                    )}
                  >
                    <p className="whitespace-pre-wrap break-words leading-relaxed">{msg.text}</p>
                    <div className={cn(
                      'flex items-center justify-end gap-1 mt-0.5',
                      msg.from_me ? 'text-green-100' : 'text-muted-foreground'
                    )}>
                      <span className="text-[10px]">{formatTime(msg.timestamp)}</span>
                      {msg.from_me && <StatusTick status={msg.status} />}
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            <div className="px-4 py-3 border-t border-border bg-muted/20 shrink-0">
              <div className="flex items-end gap-2">
                <textarea
                  ref={textareaRef}
                  value={input}
                  onChange={handleInput}
                  onKeyDown={handleKeyDown}
                  placeholder="Mensagem..."
                  rows={1}
                  className="flex-1 resize-none rounded-2xl border border-input bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring overflow-y-auto"
                  style={{ minHeight: '36px', maxHeight: '128px' }}
                />
                <button
                  onClick={send}
                  disabled={!input.trim() || sending}
                  className="shrink-0 h-9 w-9 flex items-center justify-center rounded-full bg-green-500 text-white hover:bg-green-600 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
                >
                  <Send className="h-4 w-4" />
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-3 text-muted-foreground">
            <MessageCircle className="h-12 w-12 opacity-20" />
            <p className="text-sm">Selecione uma conversa para começar</p>
          </div>
        )}
      </div>
    </div>
  )
}

export const whatsappMeta = {
  id: 'whatsapp',
  label: 'WhatsApp',
  description: 'Chat de WhatsApp',
  icon: MessageCircle,
  badge: <Badge variant="success">Active</Badge>,
}
