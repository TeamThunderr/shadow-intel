import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Home from './pages/Home'
import Investigation from './pages/Investigation'
import Watchlist from './pages/Watchlist'
import AlertHistory from './pages/AlertHistory'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 2, refetchOnWindowFocus: false },
  },
})

function NavBar() {
  return (
    <nav style={{
      display: 'flex',
      alignItems: 'center',
      gap: '2rem',
      padding: '0 2rem',
      height: '60px',
      borderBottom: '1px solid rgba(255,255,255,0.07)',
      background: 'rgba(8,12,20,0.95)',
      backdropFilter: 'blur(12px)',
      position: 'sticky',
      top: 0,
      zIndex: 100,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginRight: '1rem' }}>
        <div style={{
          width: 32, height: 32, borderRadius: 8,
          background: 'linear-gradient(135deg, #3b82f6, #6366f1)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 16, fontWeight: 700,
        }}>S</div>
        <span style={{ fontWeight: 700, fontSize: '1.05rem', letterSpacing: '-0.02em', color: '#e2e8f0' }}>
          Shadow Intel
        </span>
      </div>
      {[
        { to: '/', label: 'Investigate' },
        { to: '/watchlist', label: 'Watchlist' },
        { to: '/alerts', label: 'Alert History' },
      ].map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          end={to === '/'}
          style={({ isActive }) => ({
            fontSize: '0.875rem',
            fontWeight: 500,
            color: isActive ? '#60a5fa' : '#94a3b8',
            textDecoration: 'none',
            transition: 'color 0.2s',
            paddingBottom: '2px',
            borderBottom: isActive ? '2px solid #3b82f6' : '2px solid transparent',
          })}
        >
          {label}
        </NavLink>
      ))}
      <div style={{ marginLeft: 'auto', fontSize: '0.75rem', color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>
        Agents League 2026
      </div>
    </nav>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <NavBar />
        <main style={{ minHeight: 'calc(100vh - 60px)' }}>
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/investigate/:entityId" element={<Investigation />} />
            <Route path="/watchlist" element={<Watchlist />} />
            <Route path="/alerts" element={<AlertHistory />} />
          </Routes>
        </main>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
