import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export function ModulePage({
  title,
  description,
  icon: Icon,
  children,
  fullHeight,
}: {
  title: string
  description: string
  icon: LucideIcon
  children: ReactNode
  /** Module owns its own internal scroll/height (e.g. a chat two-pane layout). */
  fullHeight?: boolean
}) {
  return (
    <div
      className={cn(
        'mx-auto flex w-full max-w-6xl flex-col px-6 py-8 md:px-10',
        fullHeight && 'h-full',
      )}
    >
      <div className="mb-6 flex shrink-0 items-center gap-2.5">
        <Icon className="h-5 w-5 text-muted-foreground" />
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      <div className={cn(fullHeight && 'min-h-0 flex-1')}>{children}</div>
    </div>
  )
}
