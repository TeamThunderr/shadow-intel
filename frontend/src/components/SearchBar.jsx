import { useState } from 'react'

const ENTITY_TYPES = [
  { value: 'unknown', label: 'Auto-detect' },
  { value: 'company', label: 'Company' },
  { value: 'person', label: 'Person' },
]

export default function SearchBar({ onInvestigate, loading = false }) {
  const [name, setName] = useState('')
  const [entityType, setEntityType] = useState('unknown')
  const [countryHint, setCountryHint] = useState('')

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!name.trim() || loading) return
    onInvestigate({ name: name.trim(), entityType, countryHint: countryHint.trim().toUpperCase().slice(0, 2) || null })
  }

  return (
    <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', alignItems: 'center' }}>
      <div style={{ display: 'flex', gap: '0.75rem', width: '100%', maxWidth: 680 }}>
        <input
          id="search-entity-name"
          className="input-field"
          placeholder="Enter entity name, company, or individual…"
          value={name}
          onChange={(e) => setName(e.target.value)}
          style={{ flex: 1, fontSize: '1rem' }}
          autoFocus
          required
          minLength={2}
        />
        <button
          id="start-investigation-btn"
          type="submit"
          className="btn-primary"
          disabled={!name.trim() || loading}
          style={{ whiteSpace: 'nowrap', padding: '12px 28px', fontSize: '1rem' }}
        >
          {loading ? (
            <>
              <span style={{ display: 'inline-block', width: 14, height: 14, border: '2px solid rgba(255,255,255,0.3)', borderTopColor: '#fff', borderRadius: '50%', animation: 'spin 0.8s linear infinite' }} />
              Launching…
            </>
          ) : (
            '🔍 Investigate'
          )}
        </button>
      </div>

      {/* Advanced options */}
      <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
        <select
          id="entity-type-select"
          value={entityType}
          onChange={(e) => setEntityType(e.target.value)}
          style={{
            background: 'rgba(17,28,48,0.9)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            color: '#94a3b8',
            padding: '6px 12px',
            fontSize: '0.82rem',
            cursor: 'pointer',
            outline: 'none',
          }}
        >
          {ENTITY_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>

        <input
          id="country-hint-input"
          value={countryHint}
          onChange={(e) => setCountryHint(e.target.value)}
          placeholder="Country (e.g. GB)"
          maxLength={2}
          style={{
            background: 'rgba(17,28,48,0.9)',
            border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: 8,
            color: '#94a3b8',
            padding: '6px 12px',
            fontSize: '0.82rem',
            outline: 'none',
            width: 110,
          }}
        />

        <span style={{ fontSize: '0.75rem', color: '#475569' }}>
          ISO 2-letter country code (optional)
        </span>
      </div>

      <style>{`
        @keyframes spin { to { transform: rotate(360deg); } }
      `}</style>
    </form>
  )
}
