import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Search, Eye, Bell, Zap } from 'lucide-react'
import Home from './pages/Home'
import Investigation from './pages/Investigation'
import Watchlist from './pages/Watchlist'
import AlertHistory from './pages/AlertHistory'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000, refetchOnWindowFocus: false },
  },
})

const NAV = [
  { to: '/', icon: Search, label: 'Investigate', exact: true },
  { to: '/watchlist', icon: Eye,  label: 'Watchlist' },
  { to: '/alerts',   icon: Bell, label: 'Alerts' },
]

const sidebarStyle = {
  width: 56,
  background: 'var(--bg-secondary)',
  borderRight: '1px solid var(--border)',
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  padding: '16px 0',
  gap: 4,
  position: 'fixed',
  left: 0, top: 0, bottom: 0,
  zIndex: 50,
}

const logoStyle = {
  width: 32, height: 32,
  borderRadius: 8,
  background: 'var(--accent-blue)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  fontWeight: 800,
  fontSize: 12,
  color: '#fff',
  marginBottom: 16,
  letterSpacing: '-0.5px',
  fontFamily: 'var(--font-mono)',
  flexShrink: 0,
  userSelect: 'none',
}

function Sidebar() {
  return (
    <nav style={sidebarStyle}>
      {/* Logo */}
      <div style={logoStyle}>SI</div>

      {/* Nav links */}
      {NAV.map(({ to, icon: Icon, label, exact }) => (
        <NavLink
          key={to}
          to={to}
          end={exact}
          title={label}
          style={({ isActive }) => ({
            width: 40, height: 40,
            borderRadius: 8,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: isActive ? 'var(--accent-blue)' : 'var(--text-muted)',
            background: isActive ? 'rgba(77,127,255,0.12)' : 'transparent',
            textDecoration: 'none',
            transition: 'all 0.15s',
          })}
        >
          <Icon size={17} />
        </NavLink>
      ))}

      {/* Foundry IQ badge at bottom */}
      <div style={{ marginTop: 'auto', marginBottom: 4 }}>
        <div
          title="Powered by Azure AI Foundry"
          style={{
            width: 32, height: 32,
            borderRadius: 8,
            border: '1px solid var(--border-bright)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <Zap size={13} color="var(--accent-purple)" />
        </div>
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
          <Sidebar />
          <main style={{ marginLeft: 56, flex: 1, minHeight: '100vh', overflow: 'hidden' }}>
            <Routes>
              <Route path="/"                        element={<Home />} />
              <Route path="/investigate/:entityId"   element={<Investigation />} />
              <Route path="/watchlist"               element={<Watchlist />} />
              <Route path="/alerts"                  element={<AlertHistory />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
