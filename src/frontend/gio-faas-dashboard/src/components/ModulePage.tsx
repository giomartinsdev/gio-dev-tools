import type { ReactNode } from 'react'
import type { LucideIcon } from 'lucide-react'

export function ModulePage({
  title,
  description,
  icon: Icon,
  children,
}: {
  title: string
  description: string
  icon: LucideIcon
  children: ReactNode
}) {
  return (
    <div className="mx-auto w-full max-w-6xl px-6 py-8 md:px-10">
      <div className="mb-6 flex items-center gap-2.5">
        <Icon className="h-5 w-5 text-muted-foreground" />
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
      {children}
    </div>
  )
}
