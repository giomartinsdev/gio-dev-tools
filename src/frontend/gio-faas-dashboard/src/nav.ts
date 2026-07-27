import { LayoutGrid, DollarSign, Landmark, MessageSquare, Trophy, Settings, Bus } from 'lucide-react'

export type NavItem = {
  path: string
  label: string
  description: string
  icon: typeof LayoutGrid
  live: boolean
}

export const overviewNav: NavItem[] = [
  { path: '/', label: 'Home', description: 'Visão geral de tudo', icon: LayoutGrid, live: false },
]

export const appsNav: NavItem[] = [
  { path: '/finance', label: 'Finance', description: 'Track income and expenses', icon: DollarSign, live: true },
  { path: '/portfolio', label: 'Portfolio', description: 'Track your investments and assets', icon: Landmark, live: true },
  { path: '/whatsapp', label: 'WhatsApp', description: 'Conversas e mensagens do WhatsApp', icon: MessageSquare, live: true },
  { path: '/sports-data', label: 'Sports Data', description: 'bzzoiro pipeline — matches, value bets and ML insights', icon: Trophy, live: true },
  { path: '/bus-tracker', label: 'Ônibus (Rio)', description: 'Rastreamento de linhas de ônibus em tempo real', icon: Bus, live: true },
  { path: '/settings', label: 'Configuração', description: 'Números, periodicidade e envio dos relatórios e serviços', icon: Settings, live: false },
]

export const allNav: NavItem[] = [...overviewNav, ...appsNav]
