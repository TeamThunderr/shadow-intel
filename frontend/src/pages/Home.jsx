import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { startInvestigation } from '../api/client'
import { Search, ArrowRight, Clock, Building2, User, HelpCircle, Activity } from 'lucide-react'

const PLACEHOLDERS = [
  'Search entity name…',
  "Try 'Rosneft'",
  "Try 'Gazprom'",
  "Try 'Wirecard'",
  "Try 'Glencore'",
  "Try 'Viktor Bout'",
]

const DEMO_ENTITIES = [
  { name: 'Rosneft',     type: 'company', hint: 'RU', icon: Building2 },
  { name: 'Gazprom',     type: 'company', hint: 'RU', icon: Building2 },
  { name: 'Wirecard AG', type: 'company', hint: 'DE', icon: Building2 },
  { name: 'Glencore',    type: 'company', hint: 'CH', icon: Building2 },
  { name: 'Viktor Bout', type: 'person',  hint: 'RU', icon: User },
]

const AGENTS = [
  { icon: Search,   name: 'Ghost Tracker',    desc: 'Sanctions matching across OFAC, UN, OpenSanctions.',  color: 'var(--accent-blue)' },
  { icon: Activity, name: 'Money Trail',      desc: 'Blockchain tracing, FATF jurisdiction scoring.',        color: 'var(--accent-purple)' },
  { icon: Building2,name: 'Ownership Unwind', desc: 'Recursive UBO graph, shell company detection.',         color: 'var(--accent-teal)' },
  { icon: Activity, name: 'Dark Signal',      desc: 'ICIJ leaks, OCCRP Aleph, GDELT news monitoring.',      color: 'var(--risk-high)' },
  { icon: Clock,    name: 'Resurface Engine', desc: 'Watchlist polling, new registration alerts.',           color: 'var(--accent-amber)' },
]

const ENTITY_TYPES = [
  { value: 'company', label: 'Company', icon: Building2 },
  { value: 'person',  label: 'Person',  icon: User },
  { value: 'unknown', label: 'Unknown', icon: HelpCircle },
]

const LS_KEY = 'si_recent_investigations'

function getRecent() {
  try {
    return JSON.parse(localStorage.getItem(LS_KEY) || '[]')
  } catch {
    return []
  }
}

function saveRecent(entry) {
  const prev = getRecent().filter(r => r.entityId !== entry.entityId)
  const next  = [entry, ...prev].slice(0, 5)
  localStorage.setItem(LS_KEY, JSON.stringify(next))
}

export default function Home() {
  const navigate = useNavigate()
  const inputRef  = useRef(null)

  const [name,       setName]       = useState('')
  const [entityType, setEntityType] = useState('unknown')
  const [countryHint, setCountryHint] = useState('')
  const [loading,    setLoading]    = useState(false)
  const [error,      setError]      = useState(null)
  const [recent,     setRecent]     = useState(getRecent)
  const [phIdx,      setPhIdx]      = useState(0)

  // Rotate placeholder
  useEffect(() => {
    const id = setInterval(() => setPhIdx(i => (i + 1) % PLACEHOLDERS.length), 3000)
    return () => clearInterval(id)
  }, [])

  const handleInvestigate = async (payload = null) => {
    const investigateName = payload?.name || name.trim()
    const investigateType = payload?.type || entityType
    const investigateHint = payload?.hint || countryHint.trim().toUpperCase() || null

    if (!investigateName) {
      setError('Please enter an entity name.')
      inputRef.current?.focus()
      return
    }

    setLoading(true)
    setError(null)

    try {
      const res = await startInvestigation({
        name:                 investigateName,
        entity_type:          investigateType,
        country_hint:         investigateHint || null,
        confidence_threshold: 0.80,
      })
      const entityId = res.data.entity_id

      // Save to recent
      const entry = { entityId, name: investigateName, type: investigateType, ts: Date.now() }
      saveRecent(entry)
      setRecent(getRecent())

      navigate(`/investigate/${entityId}`)
    } catch (err) {
      setError(err.message || 'Failed to start investigation. Is the backend running?')
      setLoading(false)
    }
  }

  const onKeyDown = (e) => {
    if (e.key === 'Enter') handleInvestigate()
  }

  return (
    <div style={{ maxWidth: 860, margin: '0 auto', padding: '4rem 2rem', animation: 'fadeIn 0.35s ease' }}>

      {/* ── Hero ──────────────────────────────────────────────────────────── */}
      <div style={{ textAlign: 'center', marginBottom: '3.5rem' }}>
        {/* Tag line */}
        <div style={{
          display: 'inline-flex', alignItems: 'center', gap: 8,
          background: 'var(--accent-blue-light)', border: '1px solid var(--accent-blue-mid)',
          borderRadius: 999, padding: '4px 14px',
          fontSize: '0.72rem', color: 'var(--accent-blue)',
          fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase',
          marginBottom: '1.5rem',
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%',
            background: 'var(--accent-blue)', display: 'inline-block',
            animation: 'pulse-ring 1.4s infinite',
          }} />
          5-Agent Intelligence Platform
        </div>

        <h1 style={{
          fontSize: 'clamp(2rem, 5vw, 3rem)',
          fontWeight: 800,
          letterSpacing: '-0.04em',
          lineHeight: 1.1,
          color: 'var(--text-primary)',
          marginBottom: '1rem',
        }}>
          Follow the money.<br />Expose the shadow.
        </h1>

        <p style={{
          color: 'var(--text-muted)', fontSize: '1rem',
          maxWidth: 520, margin: '0 auto 2.5rem', lineHeight: 1.65,
        }}>
          Shadow Intel deploys five specialised AI agents simultaneously — detecting sanctions,
          tracing blockchain flows, unwinding corporate shells, and monitoring for resurface events.
        </p>

        {/* ── Search box ──────────────────────────────────────────────────── */}
        <div className="card" style={{
          padding: '20px 20px 16px', textAlign: 'left',
          boxShadow: 'var(--shadow-lg)',
        }}>
          {/* Name input row */}
          <div style={{ position: 'relative', marginBottom: 12 }}>
            <Search
              size={16}
              style={{
                position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)',
                color: 'var(--text-placeholder)', pointerEvents: 'none',
              }}
            />
            <input
              ref={inputRef}
              className="input-field"
              value={name}
              onChange={e => setName(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder={PLACEHOLDERS[phIdx]}
              style={{
                paddingLeft: 42, fontSize: '1rem', height: 48,
                transition: 'placeholder 0.3s',
              }}
              disabled={loading}
              autoFocus
            />
          </div>

          {/* Entity type + country hint row */}
          <div style={{ display: 'flex', gap: 10, marginBottom: 14, flexWrap: 'wrap' }}>
            {/* Entity type */}
            <div style={{ display: 'flex', gap: 6 }}>
              {ENTITY_TYPES.map(({ value, label, icon: Icon }) => (
                <button
                  key={value}
                  onClick={() => setEntityType(value)}
                  disabled={loading}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 5,
                    padding: '6px 12px', borderRadius: 7, border: '1px solid',
                    borderColor: entityType === value ? 'var(--accent-blue)' : 'var(--border)',
                    background:  entityType === value ? 'var(--accent-blue-light)' : 'transparent',
                    color:       entityType === value ? 'var(--accent-blue)' : 'var(--text-muted)',
                    fontSize: '0.78rem', fontWeight: 600, cursor: 'pointer',
                    transition: 'all 0.15s',
                  }}
                >
                  <Icon size={12} />
                  {label}
                </button>
              ))}
            </div>

            {/* Country hint */}
            <input
              className="input-field"
              value={countryHint}
              onChange={e => setCountryHint(e.target.value.slice(0, 2))}
              placeholder="Country (e.g. RU)"
              maxLength={2}
              disabled={loading}
              style={{ width: 130, height: 34, padding: '6px 12px', fontSize: '0.82rem', textTransform: 'uppercase' }}
            />
          </div>

          {/* Submit button */}
          <button
            className="btn-primary"
            onClick={() => handleInvestigate()}
            disabled={loading || !name.trim()}
            style={{ width: '100%', justifyContent: 'center', height: 46, fontSize: '0.95rem' }}
          >
            {loading ? (
              <><div className="spinner" /> Starting investigation…</>
            ) : (
              <><Search size={15} /> Investigate<ArrowRight size={15} /></>
            )}
          </button>

          {/* Error */}
          {error && (
            <div style={{
              marginTop: 10, padding: '8px 12px', borderRadius: 7,
              background: 'var(--risk-critical-bg)', border: '1px solid rgba(220,38,38,0.2)',
              color: 'var(--risk-critical)', fontSize: '0.8rem',
            }}>
              {error}
            </div>
          )}
        </div>

        {/* ── Demo tiles ──────────────────────────────────────────────────── */}
        <div style={{ marginTop: '1.5rem' }}>
          <p style={{
            fontSize: '0.72rem', color: 'var(--text-muted)',
            textTransform: 'uppercase', letterSpacing: '0.08em',
            marginBottom: '0.75rem', fontWeight: 600,
          }}>Try a demo investigation</p>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
            {DEMO_ENTITIES.map(e => {
              const Icon = e.icon;
              return (
                <button
                  key={e.name}
                  className="btn-ghost"
                  disabled={loading}
                  onClick={() => handleInvestigate(e)}
                  style={{ fontSize: '0.8rem', padding: '6px 14px', background: 'var(--bg-card)' }}
                >
                  <Icon size={14} style={{ color: 'var(--text-muted)' }} />
                  {e.name}
                </button>
              )
            })}
          </div>
        </div>
      </div>

      {/* ── Recent investigations ─────────────────────────────────────────── */}
      {recent.length > 0 && (
        <div style={{ marginBottom: '3rem' }}>
          <div className="section-label" style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: '0.75rem' }}>
            <Clock size={12} />
            Recent investigations
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {recent.map(r => (
              <button
                key={r.entityId}
                onClick={() => navigate(`/investigate/${r.entityId}`)}
                className="card"
                style={{
                  display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                  padding: '10px 14px', cursor: 'pointer', textAlign: 'left',
                  transition: 'all 0.15s', color: 'var(--text-primary)',
                  boxShadow: 'none',
                }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--border-focus)'; e.currentTarget.style.background = 'var(--bg-hover)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--bg-card)' }}
              >
                <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>{r.name}</span>
                <span style={{
                  fontSize: '0.7rem', color: 'var(--text-muted)',
                  fontFamily: 'var(--font-mono)',
                }}>
                  {new Date(r.ts).toLocaleDateString()} &rsaquo;
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Agent grid ───────────────────────────────────────────────────── */}
      <div>
        <p className="section-label" style={{ marginBottom: '0.75rem' }}>Intelligence agents</p>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '0.75rem',
        }}>
          {AGENTS.map(a => {
            const Icon = a.icon;
            return (
              <div
                key={a.name}
                className="card"
                style={{ padding: '1rem 1.25rem', boxShadow: 'none' }}
              >
                <div style={{ marginBottom: 8, color: a.color }}><Icon size={20} /></div>
                <div style={{ fontWeight: 700, fontSize: '0.82rem', color: 'var(--text-primary)', marginBottom: 4 }}>
                  {a.name}
                </div>
                <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  {a.desc}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
