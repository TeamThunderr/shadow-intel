import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { startInvestigation } from '../api/client'
import SearchBar from '../components/SearchBar'

const DEMO_ENTITIES = [
  { name: 'Mossack Fonseca', type: 'company', hint: 'PA' },
  { name: 'Viktor Bout', type: 'person', hint: 'RU' },
  { name: 'Wirecard AG', type: 'company', hint: 'DE' },
]

export default function Home() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleInvestigate = async ({ name, entityType, countryHint }) => {
    setLoading(true)
    setError(null)
    try {
      const res = await startInvestigation({
        name,
        entity_type: entityType,
        country_hint: countryHint || null,
      })
      navigate(`/investigate/${res.data.entity_id}`)
    } catch (err) {
      setError('Failed to start investigation. Is the backend running?')
      setLoading(false)
    }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '4rem 2rem' }}>
      {/* Hero */}
      <div style={{ textAlign: 'center', marginBottom: '3rem' }} className="animate-fade-in">
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'rgba(59,130,246,0.1)', border: '1px solid rgba(59,130,246,0.25)',
          borderRadius: 999, padding: '4px 14px', fontSize: '0.78rem',
          color: '#60a5fa', fontWeight: 600, letterSpacing: '0.06em',
          textTransform: 'uppercase', marginBottom: '1.5rem',
        }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#3b82f6', display: 'inline-block' }} />
          Multi-Agent Intelligence Platform
        </div>

        <h1 style={{
          fontSize: 'clamp(2rem, 5vw, 3.2rem)',
          fontWeight: 800,
          letterSpacing: '-0.04em',
          lineHeight: 1.1,
          background: 'linear-gradient(135deg, #e2e8f0 0%, #94a3b8 100%)',
          WebkitBackgroundClip: 'text',
          WebkitTextFillColor: 'transparent',
          marginBottom: '1rem',
        }}>
          Follow the money.<br />Expose the shadow.
        </h1>

        <p style={{ color: '#64748b', fontSize: '1.05rem', maxWidth: 560, margin: '0 auto 2.5rem' }}>
          Shadow Intel deploys five specialised AI agents simultaneously — detecting sanctions,
          tracing financial flows, unwinding corporate shells, and monitoring for resurface events.
        </p>

        <SearchBar onInvestigate={handleInvestigate} loading={loading} />

        {error && (
          <p style={{ marginTop: '1rem', color: '#f87171', fontSize: '0.875rem' }}>{error}</p>
        )}
      </div>

      {/* Demo tiles */}
      <div style={{ marginTop: '3.5rem' }}>
        <p style={{ fontSize: '0.8rem', color: '#475569', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem', fontWeight: 600 }}>
          Try a demo investigation
        </p>
        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
          {DEMO_ENTITIES.map((e) => (
            <button
              key={e.name}
              className="btn-ghost"
              disabled={loading}
              onClick={() => handleInvestigate({ name: e.name, entityType: e.type, countryHint: e.hint })}
            >
              <span style={{ fontSize: '0.75rem', opacity: 0.6 }}>{e.type === 'company' ? '🏢' : '👤'}</span>
              {e.name}
            </button>
          ))}
        </div>
      </div>

      {/* Agent grid */}
      <div style={{ marginTop: '4rem', display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '1rem' }}>
        {[
          { name: 'Ghost Tracker', icon: '👻', desc: 'Sanctions matching, entity fingerprinting across OFAC, OpenSanctions, UN lists.', color: '#3b82f6' },
          { name: 'Money Trail', icon: '💸', desc: 'Blockchain tracing, FinCEN cross-reference, FATF jurisdiction scoring.', color: '#8b5cf6' },
          { name: 'Ownership Unwind', icon: '🕸️', desc: 'Recursive UBO graph via OpenOwnership, Companies House, SEC EDGAR.', color: '#6366f1' },
          { name: 'Dark Signal', icon: '📡', desc: 'ICIJ leaks, OCCRP Aleph database, GDELT news signal monitoring.', color: '#ec4899' },
          { name: 'Resurface Engine', icon: '🔔', desc: 'Watchlist polling, new registration detection, Teams + Outlook alerts.', color: '#f59e0b' },
        ].map((agent) => (
          <div key={agent.name} className="glass-card" style={{ padding: '1.25rem 1.5rem' }}>
            <div style={{ fontSize: '1.5rem', marginBottom: '0.5rem' }}>{agent.icon}</div>
            <div style={{ fontWeight: 700, fontSize: '0.9rem', color: agent.color, marginBottom: '0.4rem' }}>{agent.name}</div>
            <div style={{ fontSize: '0.82rem', color: '#64748b', lineHeight: 1.5 }}>{agent.desc}</div>
          </div>
        ))}
      </div>
    </div>
  )
}
