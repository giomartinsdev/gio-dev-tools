import { useState, useCallback, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  BookOpen,
  ChevronRight,
  Edit3,
  Eye,
  File,
  FileText,
  Folder,
  FolderOpen,
  FolderPlus,
  Loader2,
  Pencil,
  Plus,
  RefreshCw,
  Save,
  Trash2,
  X,
} from 'lucide-react'
import { cn } from '@/lib/utils'

const GW = import.meta.env.VITE_GATEWAY_URL
const ROOT_PATH = 'gio'

interface FileEntry {
  name: string
  path: string
  is_dir: boolean
  size: number
  modified: string | null
}

type Modal =
  | { type: 'new-file' | 'new-folder'; parentPath: string }
  | { type: 'rename'; path: string; isDir: boolean; currentName: string }
  | null

async function apiFetch(path: string, opts?: RequestInit) {
  const res = await fetch(`${GW}/obsidian${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ error: 'unknown error' }))
    throw new Error(err.error ?? 'request failed')
  }
  return res.json()
}

export function ObsidianModule() {
  const [dirCache, setDirCache] = useState<Record<string, FileEntry[]>>({})
  const [openDirs, setOpenDirs] = useState<Set<string>>(new Set([ROOT_PATH]))
  const [loadingDirs, setLoadingDirs] = useState<Set<string>>(new Set())
  const [activeDir, setActiveDir] = useState<string>(ROOT_PATH)

  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [draftContent, setDraftContent] = useState('')
  const [savedContent, setSavedContent] = useState('')
  const [editorTab, setEditorTab] = useState<'write' | 'preview'>('write')
  const [saving, setSaving] = useState(false)
  const [loadingFile, setLoadingFile] = useState(false)

  const [modal, setModal] = useState<Modal>(null)
  const [modalInput, setModalInput] = useState('')
  const [modalLoading, setModalLoading] = useState(false)

  const isDirty = draftContent !== savedContent

  const loadDir = useCallback(async (path: string) => {
    setLoadingDirs(prev => new Set([...prev, path]))
    try {
      const entries: FileEntry[] = await apiFetch(`/files?path=${encodeURIComponent(path)}&type=dir`)
      setDirCache(prev => ({ ...prev, [path]: entries }))
    } catch (e) {
      console.error('loadDir error', e)
    } finally {
      setLoadingDirs(prev => {
        const s = new Set(prev)
        s.delete(path)
        return s
      })
    }
  }, [])

  useEffect(() => {
    loadDir(ROOT_PATH)
  }, [loadDir])

  const refreshDir = useCallback(
    (path: string) => {
      loadDir(path)
    },
    [loadDir],
  )

  const toggleDir = useCallback(
    async (path: string) => {
      setActiveDir(path)
      const willOpen = !openDirs.has(path)
      setOpenDirs(prev => {
        const next = new Set(prev)
        if (next.has(path)) next.delete(path)
        else next.add(path)
        return next
      })
      if (willOpen && !dirCache[path]) {
        await loadDir(path)
      }
    },
    [openDirs, dirCache, loadDir],
  )

  const openFile = useCallback(
    async (path: string, parentDir: string) => {
      if (isDirty && selectedPath) {
        if (!confirm('Unsaved changes will be lost. Continue?')) return
      }
      setSelectedPath(path)
      setActiveDir(parentDir)
      setEditorTab('write')
      setLoadingFile(true)
      try {
        const data = await apiFetch(`/files?path=${encodeURIComponent(path)}&type=file`)
        setDraftContent(data.content)
        setSavedContent(data.content)
      } catch (e) {
        console.error('openFile error', e)
      } finally {
        setLoadingFile(false)
      }
    },
    [isDirty, selectedPath],
  )

  const saveFile = useCallback(async () => {
    if (!selectedPath || !isDirty) return
    setSaving(true)
    try {
      await apiFetch('/files', {
        method: 'PUT',
        body: JSON.stringify({ path: selectedPath, content: draftContent }),
      })
      setSavedContent(draftContent)
    } catch {
      alert('Failed to save file')
    } finally {
      setSaving(false)
    }
  }, [selectedPath, draftContent, isDirty])

  const deleteResource = useCallback(
    async (path: string, isDir: boolean) => {
      const name = path.split('/').pop()
      if (!confirm(`Delete "${name}"${isDir ? ' and all its contents' : ''}?`)) return
      const parentPath = path.split('/').slice(0, -1).join('/') || ROOT_PATH
      try {
        await apiFetch('/files', {
          method: 'DELETE',
          body: JSON.stringify({ path }),
        })
        refreshDir(parentPath)
        if (selectedPath === path || selectedPath?.startsWith(path + '/')) {
          setSelectedPath(null)
          setDraftContent('')
          setSavedContent('')
        }
      } catch {
        alert('Failed to delete')
      }
    },
    [refreshDir, selectedPath],
  )

  const openModal = useCallback((m: NonNullable<Modal>) => {
    setModal(m)
    setModalInput(m.type === 'rename' ? m.currentName : '')
  }, [])

  const handleModalConfirm = useCallback(async () => {
    if (!modal || !modalInput.trim()) return
    setModalLoading(true)
    try {
      if (modal.type === 'new-file') {
        const name = modalInput.trim().endsWith('.md') ? modalInput.trim() : `${modalInput.trim()}.md`
        const path = `${modal.parentPath}/${name}`
        await apiFetch('/files', {
          method: 'POST',
          body: JSON.stringify({ action: 'create', path, content: '' }),
        })
        refreshDir(modal.parentPath)
        setModal(null)
        setModalInput('')
        await openFile(path, modal.parentPath)
      } else if (modal.type === 'new-folder') {
        const path = `${modal.parentPath}/${modalInput.trim()}`
        await apiFetch('/files', {
          method: 'POST',
          body: JSON.stringify({ action: 'mkdir', path }),
        })
        refreshDir(modal.parentPath)
        setOpenDirs(prev => new Set([...prev, modal.parentPath]))
        setModal(null)
        setModalInput('')
        await loadDir(path)
        setOpenDirs(prev => new Set([...prev, path]))
      } else if (modal.type === 'rename') {
        const parentPath = modal.path.split('/').slice(0, -1).join('/') || ROOT_PATH
        const newPath = `${parentPath}/${modalInput.trim()}`
        await apiFetch('/files', {
          method: 'PATCH',
          body: JSON.stringify({ from: modal.path, to: newPath }),
        })
        refreshDir(parentPath)
        if (selectedPath === modal.path) {
          setSelectedPath(newPath)
        }
        setModal(null)
        setModalInput('')
      }
    } catch {
      alert('Operation failed')
    } finally {
      setModalLoading(false)
    }
  }, [modal, modalInput, refreshDir, openFile, loadDir, selectedPath])

  return (
    <div className="flex h-full overflow-hidden -m-6">
      {/* Left: file tree */}
      <div className="flex w-72 shrink-0 flex-col border-r bg-muted/20">
        <div className="flex items-center gap-1 border-b px-3 py-2">
          <span className="flex-1 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
            Vault
          </span>
          <button
            onClick={() => openModal({ type: 'new-file', parentPath: activeDir })}
            title={`New file in ${activeDir}`}
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Plus className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => openModal({ type: 'new-folder', parentPath: activeDir })}
            title={`New folder in ${activeDir}`}
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <FolderPlus className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => refreshDir(ROOT_PATH)}
            title="Refresh"
            className="flex h-6 w-6 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <RefreshCw className="h-3.5 w-3.5" />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto py-1">
          {loadingDirs.has(ROOT_PATH) && !dirCache[ROOT_PATH] ? (
            <div className="flex items-center gap-2 px-4 py-2 text-xs text-muted-foreground">
              <Loader2 className="h-3 w-3 animate-spin" />
              Loading…
            </div>
          ) : dirCache[ROOT_PATH] ? (
            <TreeContents
              parentPath={ROOT_PATH}
              entries={dirCache[ROOT_PATH]}
              depth={0}
              dirCache={dirCache}
              openDirs={openDirs}
              loadingDirs={loadingDirs}
              selectedPath={selectedPath}
              activeDir={activeDir}
              onToggleDir={toggleDir}
              onOpenFile={openFile}
              onOpenModal={openModal}
              onDelete={deleteResource}
            />
          ) : (
            <div className="px-4 py-2 text-xs text-muted-foreground">No files found</div>
          )}
        </div>
      </div>

      {/* Right: editor */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {selectedPath ? (
          <>
            <div className="flex items-center gap-2 border-b px-4 py-2.5">
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{selectedPath.split('/').pop()}</p>
                <p className="truncate text-xs text-muted-foreground">{selectedPath}</p>
              </div>
              {isDirty && (
                <span className="h-2 w-2 shrink-0 rounded-full bg-amber-500" title="Unsaved changes" />
              )}
              <button
                onClick={saveFile}
                disabled={saving || !isDirty}
                className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs hover:bg-muted disabled:opacity-40"
              >
                {saving ? (
                  <Loader2 className="h-3 w-3 animate-spin" />
                ) : (
                  <Save className="h-3 w-3" />
                )}
                {saving ? 'Saving…' : 'Save'}
              </button>
              <button
                onClick={() => deleteResource(selectedPath, false)}
                className="flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-xs text-destructive hover:bg-destructive/10"
              >
                <Trash2 className="h-3 w-3" />
                Delete
              </button>
            </div>

            <div className="flex gap-1 border-b px-4 pt-2">
              <TabBtn
                active={editorTab === 'write'}
                onClick={() => setEditorTab('write')}
                icon={<Edit3 className="h-3.5 w-3.5" />}
                label="Write"
              />
              <TabBtn
                active={editorTab === 'preview'}
                onClick={() => setEditorTab('preview')}
                icon={<Eye className="h-3.5 w-3.5" />}
                label="Preview"
              />
            </div>

            <div className="flex-1 overflow-auto p-4">
              {loadingFile ? (
                <div className="flex h-full items-center justify-center">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : editorTab === 'write' ? (
                <textarea
                  className="h-full w-full resize-none bg-transparent font-mono text-sm focus:outline-none placeholder:text-muted-foreground"
                  value={draftContent}
                  onChange={e => setDraftContent(e.target.value)}
                  placeholder="Start writing…"
                  onKeyDown={e => {
                    if ((e.metaKey || e.ctrlKey) && e.key === 's') {
                      e.preventDefault()
                      saveFile()
                    }
                  }}
                />
              ) : (
                <div className="prose prose-sm dark:prose-invert max-w-none">
                  {draftContent ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{draftContent}</ReactMarkdown>
                  ) : (
                    <p className="italic text-muted-foreground">Nothing to preview.</p>
                  )}
                </div>
              )}
            </div>
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-3 text-muted-foreground">
            <BookOpen className="h-12 w-12 opacity-20" />
            <p className="text-sm">Select a file to view or edit</p>
            <p className="text-xs opacity-60">New files go to: {activeDir}</p>
          </div>
        )}
      </div>

      {modal && (
        <OperationModal
          modal={modal}
          value={modalInput}
          onChange={setModalInput}
          onConfirm={handleModalConfirm}
          onClose={() => {
            setModal(null)
            setModalInput('')
          }}
          loading={modalLoading}
        />
      )}
    </div>
  )
}

function TreeContents({
  parentPath,
  entries,
  depth,
  dirCache,
  openDirs,
  loadingDirs,
  selectedPath,
  activeDir,
  onToggleDir,
  onOpenFile,
  onOpenModal,
  onDelete,
}: {
  parentPath: string
  entries: FileEntry[]
  depth: number
  dirCache: Record<string, FileEntry[]>
  openDirs: Set<string>
  loadingDirs: Set<string>
  selectedPath: string | null
  activeDir: string
  onToggleDir: (path: string) => void
  onOpenFile: (path: string, parentDir: string) => void
  onOpenModal: (m: NonNullable<Modal>) => void
  onDelete: (path: string, isDir: boolean) => void
}) {
  return (
    <>
      {entries.map(entry =>
        entry.is_dir ? (
          <TreeDirNode
            key={entry.path}
            entry={entry}
            depth={depth}
            dirCache={dirCache}
            openDirs={openDirs}
            loadingDirs={loadingDirs}
            selectedPath={selectedPath}
            activeDir={activeDir}
            onToggleDir={onToggleDir}
            onOpenFile={onOpenFile}
            onOpenModal={onOpenModal}
            onDelete={onDelete}
          />
        ) : (
          <TreeFileNode
            key={entry.path}
            entry={entry}
            depth={depth}
            parentPath={parentPath}
            selectedPath={selectedPath}
            onOpenFile={onOpenFile}
            onOpenModal={onOpenModal}
            onDelete={onDelete}
          />
        ),
      )}
    </>
  )
}

function TreeDirNode({
  entry,
  depth,
  dirCache,
  openDirs,
  loadingDirs,
  selectedPath,
  activeDir,
  onToggleDir,
  onOpenFile,
  onOpenModal,
  onDelete,
}: {
  entry: FileEntry
  depth: number
  dirCache: Record<string, FileEntry[]>
  openDirs: Set<string>
  loadingDirs: Set<string>
  selectedPath: string | null
  activeDir: string
  onToggleDir: (path: string) => void
  onOpenFile: (path: string, parentDir: string) => void
  onOpenModal: (m: NonNullable<Modal>) => void
  onDelete: (path: string, isDir: boolean) => void
}) {
  const isOpen = openDirs.has(entry.path)
  const isLoading = loadingDirs.has(entry.path)
  const isActive = activeDir === entry.path
  const children = dirCache[entry.path]

  return (
    <div>
      <div
        className={cn(
          'group flex cursor-pointer select-none items-center gap-1 py-1 pr-2 text-sm hover:bg-muted/60',
          isActive && 'bg-muted/40',
        )}
        style={{ paddingLeft: `${8 + depth * 16}px` }}
        onClick={() => onToggleDir(entry.path)}
      >
        <ChevronRight
          className={cn(
            'h-3 w-3 shrink-0 text-muted-foreground transition-transform',
            isOpen && 'rotate-90',
          )}
        />
        {isOpen ? (
          <FolderOpen className="h-3.5 w-3.5 shrink-0 text-amber-500" />
        ) : (
          <Folder className="h-3.5 w-3.5 shrink-0 text-amber-500" />
        )}
        <span className="flex-1 truncate text-xs">{entry.name}</span>
        {isLoading && <Loader2 className="h-3 w-3 shrink-0 animate-spin text-muted-foreground" />}
        <div className="hidden shrink-0 items-center gap-0.5 group-hover:flex">
          <button
            onClick={e => {
              e.stopPropagation()
              onOpenModal({ type: 'new-file', parentPath: entry.path })
            }}
            title="New file here"
            className="flex h-4 w-4 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Plus className="h-3 w-3" />
          </button>
          <button
            onClick={e => {
              e.stopPropagation()
              onOpenModal({ type: 'rename', path: entry.path, isDir: true, currentName: entry.name })
            }}
            title="Rename"
            className="flex h-4 w-4 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
          >
            <Pencil className="h-3 w-3" />
          </button>
          <button
            onClick={e => {
              e.stopPropagation()
              onDelete(entry.path, true)
            }}
            title="Delete folder"
            className="flex h-4 w-4 items-center justify-center rounded text-destructive/70 hover:bg-muted hover:text-destructive"
          >
            <Trash2 className="h-3 w-3" />
          </button>
        </div>
      </div>

      {isOpen && children && (
        <>
          {children.length === 0 ? (
            <p
              className="py-0.5 text-xs italic text-muted-foreground/60"
              style={{ paddingLeft: `${8 + (depth + 1) * 16 + 16}px` }}
            >
              Empty
            </p>
          ) : (
            <TreeContents
              parentPath={entry.path}
              entries={children}
              depth={depth + 1}
              dirCache={dirCache}
              openDirs={openDirs}
              loadingDirs={loadingDirs}
              selectedPath={selectedPath}
              activeDir={activeDir}
              onToggleDir={onToggleDir}
              onOpenFile={onOpenFile}
              onOpenModal={onOpenModal}
              onDelete={onDelete}
            />
          )}
        </>
      )}
    </div>
  )
}

function TreeFileNode({
  entry,
  depth,
  parentPath,
  selectedPath,
  onOpenFile,
  onOpenModal,
  onDelete,
}: {
  entry: FileEntry
  depth: number
  parentPath: string
  selectedPath: string | null
  onOpenFile: (path: string, parentDir: string) => void
  onOpenModal: (m: NonNullable<Modal>) => void
  onDelete: (path: string, isDir: boolean) => void
}) {
  const isSelected = selectedPath === entry.path
  const isMd = entry.name.endsWith('.md')

  return (
    <div
      className={cn(
        'group flex cursor-pointer select-none items-center gap-1 py-1 pr-2',
        isSelected
          ? 'bg-primary/10 text-primary'
          : 'text-muted-foreground hover:bg-muted/60 hover:text-foreground',
      )}
      style={{ paddingLeft: `${8 + depth * 16 + 16}px` }}
      onClick={() => onOpenFile(entry.path, parentPath)}
    >
      {isMd ? (
        <FileText className="h-3.5 w-3.5 shrink-0" />
      ) : (
        <File className="h-3.5 w-3.5 shrink-0" />
      )}
      <span className="flex-1 truncate text-xs">{entry.name}</span>
      <div className="hidden shrink-0 items-center gap-0.5 group-hover:flex">
        <button
          onClick={e => {
            e.stopPropagation()
            onOpenModal({ type: 'rename', path: entry.path, isDir: false, currentName: entry.name })
          }}
          title="Rename"
          className="flex h-4 w-4 items-center justify-center rounded text-muted-foreground hover:bg-muted hover:text-foreground"
        >
          <Pencil className="h-3 w-3" />
        </button>
        <button
          onClick={e => {
            e.stopPropagation()
            onDelete(entry.path, false)
          }}
          title="Delete"
          className="flex h-4 w-4 items-center justify-center rounded text-destructive/70 hover:bg-muted hover:text-destructive"
        >
          <Trash2 className="h-3 w-3" />
        </button>
      </div>
    </div>
  )
}

function OperationModal({
  modal,
  value,
  onChange,
  onConfirm,
  onClose,
  loading,
}: {
  modal: NonNullable<Modal>
  value: string
  onChange: (v: string) => void
  onConfirm: () => void
  onClose: () => void
  loading: boolean
}) {
  const inputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    inputRef.current?.focus()
    inputRef.current?.select()
  }, [])

  const title =
    modal.type === 'new-file'
      ? 'New File'
      : modal.type === 'new-folder'
        ? 'New Folder'
        : 'Rename'

  const placeholder =
    modal.type === 'new-file'
      ? 'filename.md'
      : modal.type === 'new-folder'
        ? 'folder-name'
        : modal.type === 'rename'
          ? modal.currentName
          : ''

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="w-80 rounded-xl border bg-background p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold">{title}</h3>
          <button onClick={onClose} className="rounded p-1 hover:bg-muted">
            <X className="h-4 w-4" />
          </button>
        </div>
        {modal.type !== 'rename' && (
          <p className="mb-3 text-xs text-muted-foreground">
            In: <span className="font-mono">{modal.parentPath}</span>
          </p>
        )}
        <input
          ref={inputRef}
          className="w-full rounded-md border bg-background px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring"
          value={value}
          onChange={e => onChange(e.target.value)}
          placeholder={placeholder}
          onKeyDown={e => {
            if (e.key === 'Enter') onConfirm()
            if (e.key === 'Escape') onClose()
          }}
        />
        <div className="mt-4 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border px-3 py-1.5 text-sm hover:bg-muted">
            Cancel
          </button>
          <button
            onClick={onConfirm}
            disabled={loading || !value.trim()}
            className="flex items-center gap-1.5 rounded-md bg-primary px-4 py-1.5 text-sm text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
            Confirm
          </button>
        </div>
      </div>
    </div>
  )
}

function TabBtn({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean
  onClick: () => void
  icon: React.ReactNode
  label: string
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        '-mb-px flex items-center gap-1.5 rounded-t border-b-2 px-3 py-1.5 text-xs font-medium transition-colors',
        active
          ? 'border-primary text-primary'
          : 'border-transparent text-muted-foreground hover:text-foreground',
      )}
    >
      {icon}
      {label}
    </button>
  )
}

export const obsidianMeta = {
  id: 'obsidian' as const,
  label: 'Obsidian',
  description: 'Browse and edit your Obsidian vault',
  icon: BookOpen,
}
