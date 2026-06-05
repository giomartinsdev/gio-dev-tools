import { useState } from 'react'
import { MessageCircle, Send, CheckCircle, XCircle, Loader2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'

type Status = 'idle' | 'loading' | 'success' | 'error'

interface Result {
  status: Status
  message: string
}

export function WpMessageModule() {
  const [number, setNumber] = useState('')
  const [message, setMessage] = useState('')
  const [result, setResult] = useState<Result | null>(null)

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setResult({ status: 'loading', message: '' })

    try {
      const res = await fetch(`${import.meta.env.VITE_GATEWAY_URL}/fn/wp-message`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ number, message }),
      })

      const data = await res.json()

      if (res.ok) {
        setResult({ status: 'success', message: 'Message sent successfully!' })
        setNumber('')
        setMessage('')
      } else {
        setResult({ status: 'error', message: data.error ?? 'Failed to send message.' })
      }
    } catch {
      setResult({ status: 'error', message: 'Failed to connect to the gateway.' })
    }
  }

  return (
    <div className="max-w-lg w-full mx-auto">
      <Card>
        <CardHeader>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-green-100 dark:bg-green-900">
              <MessageCircle className="h-5 w-5 text-green-700 dark:text-green-300" />
            </div>
            <div>
              <CardTitle>WhatsApp Message</CardTitle>
              <CardDescription>Send a WhatsApp message</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-5">
            <div className="space-y-2">
              <Label htmlFor="number">Phone number</Label>
              <Input
                id="number"
                type="tel"
                placeholder="5511999999999"
                value={number}
                onChange={e => setNumber(e.target.value)}
                required
              />
              <p className="text-xs text-muted-foreground">
                Format: country code + area code + number (no + or spaces)
              </p>
            </div>

            <div className="space-y-2">
              <Label htmlFor="message">Message</Label>
              <Textarea
                id="message"
                placeholder="Type your message..."
                value={message}
                onChange={e => setMessage(e.target.value)}
                rows={4}
                required
              />
            </div>

            {result && result.status !== 'loading' && (
              <div
                className={cn(
                  'flex items-center gap-2 rounded-md border px-3 py-2 text-sm',
                  result.status === 'success'
                    ? 'border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200'
                    : 'border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200'
                )}
              >
                {result.status === 'success' ? (
                  <CheckCircle className="h-4 w-4 shrink-0" />
                ) : (
                  <XCircle className="h-4 w-4 shrink-0" />
                )}
                {result.message}
              </div>
            )}

            <Button
              type="submit"
              className="w-full"
              disabled={result?.status === 'loading'}
            >
              {result?.status === 'loading' ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Sending...
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  Send message
                </>
              )}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  )
}

export const wpMessageMeta = {
  id: 'wp-message',
  label: 'WP Message',
  description: 'Send WhatsApp messages',
  icon: MessageCircle,
  badge: <Badge variant="success">Active</Badge>,
}
