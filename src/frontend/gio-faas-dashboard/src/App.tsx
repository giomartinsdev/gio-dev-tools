import { useState } from 'react'
import { Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { WhatsappModule, whatsappMeta } from '@/modules/whatsapp/WhatsappModule'
import { FinanceModule, financeMeta } from '@/modules/finance/FinanceModule'
import { PortfolioModule, portfolioMeta } from '@/modules/portfolio/PortfolioModule'
import { KanbanModule, kanbanMeta } from '@/modules/kanban/KanbanModule'
import { ObsidianModule, obsidianMeta } from '@/modules/obsidian/ObsidianModule'

const modules = [whatsappMeta, financeMeta, portfolioMeta, kanbanMeta, obsidianMeta]

type ModuleId = (typeof modules)[number]['id']

export default function App() {
  const [activeId, setActiveId] = useState<ModuleId>('whatsapp')

  const active = modules.find(m => m.id === activeId)!

  return (
    <div className="flex h-screen bg-background">
      <aside className="flex w-64 shrink-0 flex-col border-r bg-sidebar">
        <div className="flex h-14 items-center gap-2.5 border-b px-4">
          <div className="flex h-7 w-7 items-center justify-center rounded-md bg-primary">
            <Zap className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-sidebar-foreground">Gio Dev Tools</span>
        </div>

        <nav className="flex-1 overflow-y-auto px-2 py-3">
          <p className="mb-1 px-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
            Modules
          </p>
          <ul className="space-y-0.5">
            {modules.map(mod => {
              const Icon = mod.icon
              const isActive = mod.id === activeId
              return (
                <li key={mod.id}>
                  <button
                    onClick={() => setActiveId(mod.id)}
                    className={cn(
                      'flex w-full items-center gap-2.5 rounded-md px-2 py-2 text-sm transition-colors',
                      isActive
                        ? 'bg-sidebar-accent text-sidebar-accent-foreground font-medium'
                        : 'text-muted-foreground hover:bg-sidebar-accent hover:text-sidebar-accent-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="flex-1 text-left">{mod.label}</span>
                    {'badge' in mod && (mod as { badge: React.ReactNode }).badge}
                  </button>
                </li>
              )
            })}
          </ul>
        </nav>
      </aside>

      <div className="flex flex-1 flex-col overflow-hidden">
        <header className="flex h-14 items-center border-b px-6">
          <div>
            <h1 className="text-base font-semibold">{active.label}</h1>
            <p className="text-xs text-muted-foreground">{active.description}</p>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">
          {activeId === 'whatsapp' && <WhatsappModule />}
          {activeId === 'finance' && <FinanceModule />}
          {activeId === 'portfolio' && <PortfolioModule />}
          {activeId === 'kanban' && <KanbanModule />}
          {activeId === 'obsidian' && <ObsidianModule />}
        </main>
      </div>
    </div>
  )
}
