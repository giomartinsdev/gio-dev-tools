import { Outlet } from 'react-router-dom'
import { Sidebar } from '@/components/Sidebar'

export default function App() {
  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <div className="flex-1 overflow-y-auto">
        <Outlet />
      </div>
    </div>
  )
}
