import { NavLink } from 'react-router-dom'
import { Moon, Sun, Zap } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/hooks/useTheme'
import { overviewNav, appsNav } from '@/nav'
import { LivePulse } from './LivePulse'

export function Sidebar() {
  const { theme, toggle } = useTheme()

  return (
    <aside className="flex w-64 shrink-0 flex-col border-r bg-sidebar px-3 py-5">
      <div className="flex items-center gap-2.5 px-2 pb-6">
        <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-primary">
          <Zap className="h-4 w-4 text-primary-foreground" />
        </div>
        <div>
          <div className="text-sm font-semibold leading-tight text-sidebar-foreground">gio dev tools</div>
          <div className="text-[11px] leading-tight text-muted-foreground">hub</div>
        </div>
      </div>

      <NavSection title="Overview" items={overviewNav} />
      <NavSection title="Apps" items={appsNav} />

      <div className="mt-auto flex items-center gap-2.5 border-t pt-4 pl-2">
        <div className="h-7 w-7 shrink-0 rounded-full bg-gradient-to-br from-primary to-sidebar-accent-foreground" />
        <div>
          <div className="text-[12.5px] font-semibold leading-tight">Gio</div>
          <div className="text-[10.5px] leading-tight text-muted-foreground">5 apps ativos</div>
        </div>
        <button
          onClick={toggle}
          aria-label="Alternar tema"
          className="ml-auto flex h-7 w-7 items-center justify-center rounded-full border bg-muted text-muted-foreground hover:text-foreground"
        >
          {theme === 'dark' ? <Moon className="h-3.5 w-3.5" /> : <Sun className="h-3.5 w-3.5" />}
        </button>
      </div>
    </aside>
  )
}

function NavSection({ title, items }: { title: string; items: typeof overviewNav }) {
  return (
    <div className="mb-1">
      <p className="mb-1 mt-3 px-2.5 text-[10.5px] font-semibold uppercase tracking-wider text-muted-foreground">
        {title}
      </p>
      <nav className="flex flex-col gap-0.5">
        {items.map(item => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.path === '/'}
            className={({ isActive }) =>
              cn(
                'flex items-center gap-2.5 rounded-md px-2.5 py-[7px] text-[13.5px] font-medium transition-colors',
                isActive
                  ? 'bg-sidebar-accent text-sidebar-accent-foreground'
                  : 'text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground'
              )
            }
          >
            <item.icon className="h-4 w-4 shrink-0 opacity-90" />
            <span className="flex-1 text-left">{item.label}</span>
            {item.live && <LivePulse className="h-3.5 w-3.5 shrink-0" />}
          </NavLink>
        ))}
      </nav>
    </div>
  )
}
