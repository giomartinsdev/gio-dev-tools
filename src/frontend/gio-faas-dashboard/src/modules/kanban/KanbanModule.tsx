import { useCallback, useEffect, useRef, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { LayoutGrid, Plus, Trash2, ChevronLeft, ChevronRight, X, Eye, Edit3 } from 'lucide-react'
import { cn } from '@/lib/utils'

const GW = import.meta.env.VITE_GATEWAY_URL

type CardStatus = 'backlog' | 'todo' | 'in_progress' | 'done'

interface Board {
  id: string
  name: string
  created_at: string | null
}

interface Card {
  id: string
  board_id: string
  title: string
  content: string
  status: CardStatus
  position: number
}

const COLUMNS: { id: CardStatus; label: string }[] = [
  { id: 'backlog', label: 'Backlog' },
  { id: 'todo', label: 'To Do' },
  { id: 'in_progress', label: 'In Progress' },
  { id: 'done', label: 'Done' },
]

const COLUMN_INDEX = Object.fromEntries(COLUMNS.map((c, i) => [c.id, i])) as Record<CardStatus, number>

async function apiFetch(path: string, opts?: RequestInit) {
  const res = await fetch(`${GW}/fn/kanban${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'unknown error' }))
    throw new Error(err.error ?? 'request failed')
  }
  return res.json()
}

export function KanbanModule() {
  const [boards, setBoards] = useState<Board[]>([])
  const [activeBoardId, setActiveBoardId] = useState<string | null>(null)
  const [cards, setCards] = useState<Card[]>([])
  const [openCard, setOpenCard] = useState<Card | null>(null)
  const [newBoardName, setNewBoardName] = useState('')
  const [addingCard, setAddingCard] = useState<CardStatus | null>(null)
  const [newCardTitle, setNewCardTitle] = useState('')
  const [loading, setLoading] = useState(true)

  // Drag state
  const draggingCard = useRef<Card | null>(null)
  const [draggingCardId, setDraggingCardId] = useState<string | null>(null)
  const [dragOverColumn, setDragOverColumn] = useState<CardStatus | null>(null)

  const fetchBoards = useCallback(async () => {
    const data = await apiFetch('')
    setBoards(data)
    if (data.length > 0 && !activeBoardId) {
      setActiveBoardId(data[0].id)
    }
  }, [activeBoardId])

  const fetchCards = useCallback(async (boardId: string) => {
    const data = await apiFetch(`?board_id=${boardId}`)
    setCards(data)
  }, [])

  useEffect(() => {
    setLoading(true)
    fetchBoards().finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (activeBoardId) fetchCards(activeBoardId)
  }, [activeBoardId, fetchCards])

  async function createBoard() {
    if (!newBoardName.trim()) return
    const board = await apiFetch('', {
      method: 'POST',
      body: JSON.stringify({ resource: 'board', name: newBoardName }),
    })
    setBoards(prev => [...prev, board])
    setActiveBoardId(board.id)
    setNewBoardName('')
  }

  async function deleteBoard() {
    if (!activeBoardId) return
    if (!confirm('Delete this board and all its cards?')) return
    await apiFetch('', {
      method: 'DELETE',
      body: JSON.stringify({ resource: 'board', id: activeBoardId }),
    })
    const remaining = boards.filter(b => b.id !== activeBoardId)
    setBoards(remaining)
    setActiveBoardId(remaining[0]?.id ?? null)
    setCards([])
  }

  async function createCard(status: CardStatus) {
    if (!newCardTitle.trim() || !activeBoardId) return
    const card = await apiFetch('', {
      method: 'POST',
      body: JSON.stringify({ resource: 'card', board_id: activeBoardId, title: newCardTitle, status }),
    })
    setCards(prev => [...prev, card])
    setNewCardTitle('')
    setAddingCard(null)
  }

  async function moveCardToStatus(card: Card, newStatus: CardStatus) {
    if (card.status === newStatus) return
    // Optimistic update
    setCards(prev => prev.map(c => c.id === card.id ? { ...c, status: newStatus } : c))
    if (openCard?.id === card.id) setOpenCard(prev => prev ? { ...prev, status: newStatus } : null)
    try {
      const updated = await apiFetch('', {
        method: 'PATCH',
        body: JSON.stringify({ id: card.id, title: card.title, content: card.content, status: newStatus, board_id: card.board_id }),
      })
      setCards(prev => prev.map(c => c.id === card.id ? updated : c))
      if (openCard?.id === card.id) setOpenCard(updated)
    } catch {
      // Revert on failure
      setCards(prev => prev.map(c => c.id === card.id ? card : c))
      if (openCard?.id === card.id) setOpenCard(card)
    }
  }

  async function moveCard(card: Card, direction: -1 | 1) {
    const newIndex = COLUMN_INDEX[card.status] + direction
    if (newIndex < 0 || newIndex >= COLUMNS.length) return
    await moveCardToStatus(card, COLUMNS[newIndex].id)
  }

  async function saveCard(card: Card) {
    const updated = await apiFetch('', {
      method: 'PATCH',
      body: JSON.stringify({ id: card.id, title: card.title, content: card.content, status: card.status, board_id: card.board_id }),
    })
    setCards(prev => prev.map(c => c.id === card.id ? updated : c))
    setOpenCard(null)
  }

  async function deleteCard(cardId: string) {
    await apiFetch('', {
      method: 'DELETE',
      body: JSON.stringify({ resource: 'card', id: cardId }),
    })
    setCards(prev => prev.filter(c => c.id !== cardId))
    setOpenCard(null)
  }

  // Drag handlers
  function handleDragStart(card: Card) {
    draggingCard.current = card
    setDraggingCardId(card.id)
  }

  function handleDragEnd() {
    draggingCard.current = null
    setDraggingCardId(null)
    setDragOverColumn(null)
  }

  function handleColumnDragOver(e: React.DragEvent, status: CardStatus) {
    e.preventDefault()
    e.dataTransfer.dropEffect = 'move'
    setDragOverColumn(status)
  }

  async function handleColumnDrop(e: React.DragEvent, targetStatus: CardStatus) {
    e.preventDefault()
    const card = draggingCard.current
    draggingCard.current = null
    setDraggingCardId(null)
    setDragOverColumn(null)
    if (card) await moveCardToStatus(card, targetStatus)
  }

  if (loading) {
    return <div className="flex h-full items-center justify-center text-muted-foreground text-sm">Loading…</div>
  }

  return (
    <div className="flex h-full flex-col gap-4">
      {/* Board toolbar */}
      <div className="flex flex-wrap items-center gap-2">
        <select
          value={activeBoardId ?? ''}
          onChange={e => setActiveBoardId(e.target.value)}
          className="h-9 rounded-md border bg-background px-3 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
        >
          {boards.length === 0 && <option value="">No boards</option>}
          {boards.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
        </select>

        <div className="flex items-center gap-1 rounded-md border bg-background px-2">
          <input
            className="h-9 w-40 bg-transparent text-sm focus:outline-none placeholder:text-muted-foreground"
            placeholder="New board name…"
            value={newBoardName}
            onChange={e => setNewBoardName(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && createBoard()}
          />
          <button
            onClick={createBoard}
            disabled={!newBoardName.trim()}
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:text-foreground disabled:opacity-30"
          >
            <Plus className="h-4 w-4" />
          </button>
        </div>

        {activeBoardId && (
          <button
            onClick={deleteBoard}
            className="flex h-9 items-center gap-1.5 rounded-md border px-3 text-sm text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete board
          </button>
        )}
      </div>

      {/* Kanban columns */}
      {activeBoardId ? (
        <div
          className="flex flex-1 gap-3 overflow-x-auto pb-2"
          onDragLeave={e => {
            // Only clear when leaving the entire board area, not between children
            if (!e.currentTarget.contains(e.relatedTarget as Node)) {
              setDragOverColumn(null)
            }
          }}
        >
          {COLUMNS.map(col => {
            const colCards = cards.filter(c => c.status === col.id)
            const isDropTarget = dragOverColumn === col.id && draggingCard.current?.status !== col.id
            return (
              <div
                key={col.id}
                onDragOver={e => handleColumnDragOver(e, col.id)}
                onDrop={e => handleColumnDrop(e, col.id)}
                className={cn(
                  'flex w-64 shrink-0 flex-col rounded-lg border transition-colors',
                  isDropTarget
                    ? 'border-primary bg-primary/5 shadow-[0_0_0_2px] shadow-primary/30'
                    : 'border-border bg-muted/30'
                )}
              >
                {/* Column header */}
                <div className="flex items-center justify-between px-3 py-2.5">
                  <span className="text-xs font-semibold uppercase tracking-wide text-muted-foreground">{col.label}</span>
                  <span className="flex h-5 min-w-5 items-center justify-center rounded-full bg-muted px-1.5 text-xs font-medium text-muted-foreground">
                    {colCards.length}
                  </span>
                </div>

                {/* Cards */}
                <div className="flex flex-1 flex-col gap-2 overflow-y-auto px-2 pb-2">
                  {colCards.map(card => (
                    <KanbanCard
                      key={card.id}
                      card={card}
                      isDragging={draggingCardId === card.id}
                      onOpen={() => setOpenCard(card)}
                      onMoveLeft={() => moveCard(card, -1)}
                      onMoveRight={() => moveCard(card, 1)}
                      onDragStart={() => handleDragStart(card)}
                      onDragEnd={handleDragEnd}
                      isFirst={COLUMN_INDEX[card.status] === 0}
                      isLast={COLUMN_INDEX[card.status] === COLUMNS.length - 1}
                    />
                  ))}

                  {/* Drop hint when column is empty and is a valid drop target */}
                  {isDropTarget && colCards.length === 0 && (
                    <div className="flex h-16 items-center justify-center rounded-md border-2 border-dashed border-primary/40 text-xs text-primary/60">
                      Drop here
                    </div>
                  )}

                  {/* Inline add */}
                  {addingCard === col.id ? (
                    <div className="rounded-md border bg-background p-2 shadow-sm">
                      <input
                        autoFocus
                        className="w-full text-sm focus:outline-none"
                        placeholder="Card title…"
                        value={newCardTitle}
                        onChange={e => setNewCardTitle(e.target.value)}
                        onKeyDown={e => {
                          if (e.key === 'Enter') createCard(col.id)
                          if (e.key === 'Escape') { setAddingCard(null); setNewCardTitle('') }
                        }}
                      />
                      <div className="mt-2 flex gap-1">
                        <button
                          onClick={() => createCard(col.id)}
                          className="rounded bg-primary px-2 py-1 text-xs text-primary-foreground"
                        >
                          Add
                        </button>
                        <button
                          onClick={() => { setAddingCard(null); setNewCardTitle('') }}
                          className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => { setAddingCard(col.id); setNewCardTitle('') }}
                      className="flex items-center gap-1 rounded-md px-2 py-1.5 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      <Plus className="h-3.5 w-3.5" />
                      Add card
                    </button>
                  )}
                </div>
              </div>
            )
          })}
        </div>
      ) : (
        <div className="flex flex-1 flex-col items-center justify-center gap-2 text-center text-muted-foreground">
          <LayoutGrid className="h-10 w-10 opacity-30" />
          <p className="text-sm">Create a board to get started</p>
        </div>
      )}

      {/* Card modal */}
      {openCard && (
        <CardModal
          card={openCard}
          boards={boards}
          onClose={() => setOpenCard(null)}
          onSave={saveCard}
          onDelete={deleteCard}
          onMoveLeft={() => moveCard(openCard, -1)}
          onMoveRight={() => moveCard(openCard, 1)}
        />
      )}
    </div>
  )
}

function KanbanCard({
  card,
  isDragging,
  onOpen,
  onMoveLeft,
  onMoveRight,
  onDragStart,
  onDragEnd,
  isFirst,
  isLast,
}: {
  card: Card
  isDragging: boolean
  onOpen: () => void
  onMoveLeft: () => void
  onMoveRight: () => void
  onDragStart: () => void
  onDragEnd: () => void
  isFirst: boolean
  isLast: boolean
}) {
  return (
    <div
      draggable
      onDragStart={onDragStart}
      onDragEnd={onDragEnd}
      className={cn(
        'group relative rounded-md border bg-background p-3 shadow-sm hover:shadow-md transition-all cursor-grab active:cursor-grabbing select-none',
        isDragging && 'opacity-40 scale-95 rotate-1'
      )}
    >
      <div onClick={onOpen} className="pr-12 cursor-pointer">
        <p className="text-sm font-medium leading-snug">{card.title}</p>
        {card.content && (
          <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">{card.content.replace(/[#*`_[\]]/g, '')}</p>
        )}
      </div>
      <div className="absolute right-2 top-2 flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity">
        {!isFirst && (
          <button
            onClick={e => { e.stopPropagation(); onMoveLeft() }}
            className="flex h-5 w-5 items-center justify-center rounded hover:bg-muted"
          >
            <ChevronLeft className="h-3 w-3" />
          </button>
        )}
        {!isLast && (
          <button
            onClick={e => { e.stopPropagation(); onMoveRight() }}
            className="flex h-5 w-5 items-center justify-center rounded hover:bg-muted"
          >
            <ChevronRight className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  )
}

function CardModal({
  card: initialCard,
  boards,
  onClose,
  onSave,
  onDelete,
  onMoveLeft,
  onMoveRight,
}: {
  card: Card
  boards: Board[]
  onClose: () => void
  onSave: (card: Card) => void
  onDelete: (id: string) => void
  onMoveLeft: () => void
  onMoveRight: () => void
}) {
  const [draft, setDraft] = useState<Card>(initialCard)
  const [tab, setTab] = useState<'write' | 'preview'>('write')
  const [saving, setSaving] = useState(false)
  const overlayRef = useRef<HTMLDivElement>(null)

  const colIndex = COLUMN_INDEX[draft.status]

  async function handleSave() {
    setSaving(true)
    try {
      await onSave(draft)
    } finally {
      setSaving(false)
    }
  }

  function handleMoveLeft() {
    const newStatus = COLUMNS[colIndex - 1].id
    setDraft(d => ({ ...d, status: newStatus }))
    onMoveLeft()
  }

  function handleMoveRight() {
    const newStatus = COLUMNS[colIndex + 1].id
    setDraft(d => ({ ...d, status: newStatus }))
    onMoveRight()
  }

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      onClick={e => { if (e.target === overlayRef.current) onClose() }}
    >
      <div className="flex h-[80vh] w-full max-w-3xl flex-col rounded-xl border bg-background shadow-2xl">
        {/* Modal header */}
        <div className="flex items-start gap-3 border-b px-5 py-4">
          <input
            className="flex-1 text-base font-semibold focus:outline-none bg-transparent"
            value={draft.title}
            onChange={e => setDraft(d => ({ ...d, title: e.target.value }))}
            placeholder="Card title"
          />
          <button onClick={onClose} className="mt-0.5 rounded hover:bg-muted p-1">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Metadata row */}
        <div className="flex flex-wrap items-center gap-3 border-b px-5 py-2.5 text-sm">
          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Status</span>
            <select
              value={draft.status}
              onChange={e => setDraft(d => ({ ...d, status: e.target.value as CardStatus }))}
              className="rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {COLUMNS.map(c => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </div>

          <div className="flex items-center gap-1.5">
            <span className="text-muted-foreground">Board</span>
            <select
              value={draft.board_id}
              onChange={e => setDraft(d => ({ ...d, board_id: e.target.value }))}
              className="rounded border bg-background px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {boards.map(b => <option key={b.id} value={b.id}>{b.name}</option>)}
            </select>
          </div>

          <div className="ml-auto flex items-center gap-1">
            <button
              onClick={handleMoveLeft}
              disabled={colIndex === 0}
              className="flex h-7 items-center gap-1 rounded border px-2 text-xs hover:bg-muted disabled:opacity-30"
            >
              <ChevronLeft className="h-3 w-3" />
              {colIndex > 0 ? COLUMNS[colIndex - 1].label : ''}
            </button>
            <button
              onClick={handleMoveRight}
              disabled={colIndex === COLUMNS.length - 1}
              className="flex h-7 items-center gap-1 rounded border px-2 text-xs hover:bg-muted disabled:opacity-30"
            >
              {colIndex < COLUMNS.length - 1 ? COLUMNS[colIndex + 1].label : ''}
              <ChevronRight className="h-3 w-3" />
            </button>
          </div>
        </div>

        {/* Tab bar */}
        <div className="flex gap-1 border-b px-5 pt-2">
          <TabBtn active={tab === 'write'} onClick={() => setTab('write')} icon={<Edit3 className="h-3.5 w-3.5" />} label="Write" />
          <TabBtn active={tab === 'preview'} onClick={() => setTab('preview')} icon={<Eye className="h-3.5 w-3.5" />} label="Preview" />
        </div>

        {/* Editor / Preview */}
        <div className="flex-1 overflow-auto px-5 py-4">
          {tab === 'write' ? (
            <textarea
              className="h-full w-full resize-none bg-transparent font-mono text-sm focus:outline-none placeholder:text-muted-foreground"
              placeholder="Write your card content in Markdown…"
              value={draft.content}
              onChange={e => setDraft(d => ({ ...d, content: e.target.value }))}
            />
          ) : (
            <div className="prose prose-sm dark:prose-invert max-w-none">
              {draft.content ? (
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{draft.content}</ReactMarkdown>
              ) : (
                <p className="text-muted-foreground italic">Nothing to preview.</p>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between border-t px-5 py-3">
          <button
            onClick={() => { if (confirm('Delete this card?')) onDelete(draft.id) }}
            className="flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm text-destructive hover:bg-destructive/10"
          >
            <Trash2 className="h-3.5 w-3.5" />
            Delete
          </button>
          <div className="flex gap-2">
            <button onClick={onClose} className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted">
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !draft.title.trim()}
              className="rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
            >
              {saving ? 'Saving…' : 'Save'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function TabBtn({ active, onClick, icon, label }: { active: boolean; onClick: () => void; icon: React.ReactNode; label: string }) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-1.5 rounded-t px-3 py-1.5 text-xs font-medium border-b-2 -mb-px transition-colors',
        active
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground'
      )}
    >
      {icon}
      {label}
    </button>
  )
}

export const kanbanMeta = {
  id: 'kanban',
  label: 'Kanban',
  description: 'Manage tasks across boards and columns',
  icon: LayoutGrid,
}
