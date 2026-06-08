import { useState, useMemo } from 'react'
import { Search, Filter, Calendar, ChevronLeft, ChevronRight } from 'lucide-react'

// Alert history is currently read from in-memory store.
// P4: Connect to Fabric for persistent alert log.

const MOCK_ALERTS = [
  {
    alert_id: 'a1',
    entity_name: 'Mossack Fonseca',
    alert_type: 'resurface',
    risk_level: 'critical',
    confidence: 0.94,
    match_event: 'New company registration with identical director overlap in BVI',
    jurisdiction: 'VG',
    timestamp: new Date(Date.now() - 3600000).toISOString(),
    status: 'delivered',
    top_evidence: ['Director "John Doe" matches 3 known shell entities', 'Address reuse: 22 Harbour Rd, Road Town'],
  },
  {
    alert_id: 'a2',
    entity_name: 'Viktor Bout',
    alert_type: 'resurface',
    risk_level: 'high',
    confidence: 0.81,
    match_event: 'OCCRP article mentions alias "Viktor Anatoliyevich"',
    jurisdiction: 'AE',
    timestamp: new Date(Date.now() - 86400000).toISOString(),
    status: 'delivered',
    top_evidence: ['Alias match in OCCRP Aleph database', 'UAE company registration 2025-11'],
  },
  {
    alert_id: 'a3',
    entity_name: 'Wirecard AG',
    alert_type: 'resurface',
    risk_level: 'medium',
    confidence: 0.65,
    match_event: 'New domain registration matches pattern',
    jurisdiction: 'DE',
    timestamp: new Date(Date.now() - 86400000 * 2).toISOString(),
    status: 'failed',
    top_evidence: ['Domain wirecard-consulting.de registered yesterday'],
  },
]

const RISK_COLORS = {
  critical: '#f87171',
  high: '#fbbf24',
  medium: '#60a5fa',
  low: '#34d399',
}

export default function AlertHistory() {
  const [searchQuery, setSearchQuery] = useState('')
  const [minConfidence, setMinConfidence] = useState(0)
  const [daysFilter, setDaysFilter] = useState('all')
  const [page, setPage] = useState(1)
  const ITEMS_PER_PAGE = 5

  const filteredAlerts = useMemo(() => {
    let result = [...MOCK_ALERTS]
    
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(a => 
        a.entity_name.toLowerCase().includes(q) || 
        a.match_event.toLowerCase().includes(q)
      )
    }

    if (minConfidence > 0) {
      result = result.filter(a => a.confidence >= minConfidence / 100)
    }

    if (daysFilter !== 'all') {
      const ms = parseInt(daysFilter, 10) * 86400000
      const cutoff = Date.now() - ms
      result = result.filter(a => new Date(a.timestamp).getTime() >= cutoff)
    }

    // Default sort by newest
    result.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    return result
  }, [searchQuery, minConfidence, daysFilter])

  const totalPages = Math.ceil(filteredAlerts.length / ITEMS_PER_PAGE) || 1
  const paginatedAlerts = filteredAlerts.slice((page - 1) * ITEMS_PER_PAGE, page * ITEMS_PER_PAGE)
  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.5rem' }}>
          Alert History
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.9rem' }}>
          Resurface events fired by the Resurface Engine. Delivered via Microsoft Teams and Outlook.
        </p>
      </div>

      {/* Filters */}
      <div className="glass-card" style={{ padding: '1.25rem', marginBottom: '1.5rem', display: 'flex', gap: '1.5rem', flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1, minWidth: 240, borderRight: '1px solid rgba(255,255,255,0.1)', paddingRight: '1.5rem' }}>
          <Search size={18} color="#64748b" />
          <input
            placeholder="Search entity or event…"
            value={searchQuery}
            onChange={e => { setSearchQuery(e.target.value); setPage(1) }}
            style={{ background: 'transparent', border: 'none', color: '#e2e8f0', outline: 'none', width: '100%' }}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Filter size={16} color="#64748b" />
          <select 
            className="input-field" 
            style={{ padding: '6px 10px', width: 140 }}
            value={minConfidence}
            onChange={e => { setMinConfidence(Number(e.target.value)); setPage(1) }}
          >
            <option value={0}>All Confidences</option>
            <option value={70}>&gt; 70% Confidence</option>
            <option value={85}>&gt; 85% Confidence</option>
          </select>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <Calendar size={16} color="#64748b" />
          <select 
            className="input-field" 
            style={{ padding: '6px 10px', width: 120 }}
            value={daysFilter}
            onChange={e => { setDaysFilter(e.target.value); setPage(1) }}
          >
            <option value="all">Any time</option>
            <option value="1">Last 24 hours</option>
            <option value="7">Last 7 days</option>
            <option value="30">Last 30 days</option>
          </select>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {paginatedAlerts.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: '#64748b' }}>No alerts match your filters.</div>
        ) : (
          paginatedAlerts.map((alert) => (
            <div key={alert.alert_id} className="glass-card animate-slide-up" style={{ padding: '0' }}>
              {/* Header row acting as columns */}
              <div style={{ display: 'grid', gridTemplateColumns: '2fr 1.5fr 1fr 1fr 1fr', gap: '1rem', padding: '1rem 1.5rem', alignItems: 'center', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
                <div>
                  <span className={`badge badge-${alert.risk_level}`} style={{ marginRight: '0.75rem' }}>
                    {alert.risk_level}
                  </span>
                  <span style={{ fontWeight: 700, fontSize: '1rem' }}>{alert.entity_name}</span>
                </div>
                <div style={{ fontSize: '0.85rem', color: '#94a3b8', textTransform: 'capitalize' }}>
                  {alert.alert_type}
                </div>
                <div style={{ fontSize: '0.85rem', color: RISK_COLORS[alert.risk_level] || '#e2e8f0', fontWeight: 600 }}>
                  {(alert.confidence * 100).toFixed(0)}%
                </div>
                <div style={{ fontSize: '0.75rem', color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>
                  {new Date(alert.timestamp).toLocaleString()}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.85rem', color: alert.status === 'delivered' ? '#10b981' : '#ef4444' }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: alert.status === 'delivered' ? '#10b981' : '#ef4444' }} />
                  <span style={{ textTransform: 'capitalize' }}>{alert.status || 'unknown'}</span>
                </div>
              </div>

              {/* Event details row */}
              <div style={{ padding: '1rem 1.5rem', background: 'rgba(0,0,0,0.1)' }}>
                <div style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: 6 }}>
                  <strong style={{ color: '#cbd5e1' }}>Trigger Event:</strong> {alert.match_event} 
                  <span style={{ fontSize: '0.7rem', background: 'rgba(255,255,255,0.1)', padding: '2px 6px', borderRadius: 4 }}>{alert.jurisdiction}</span>
                </div>

                {alert.top_evidence.length > 0 && (
                  <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ fontSize: '0.72rem', color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.4rem' }}>
                      Key Evidence
                    </div>
                    {alert.top_evidence.map((e, i) => (
                      <div key={i} style={{ fontSize: '0.82rem', color: '#64748b', paddingLeft: '0.75rem', borderLeft: '2px solid rgba(59,130,246,0.3)', marginBottom: '0.25rem' }}>
                        {e}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '1rem', marginTop: '2rem' }}>
          <button 
            className="btn-ghost" 
            style={{ padding: '6px' }}
            disabled={page === 1}
            onClick={() => setPage(p => Math.max(1, p - 1))}
          >
            <ChevronLeft size={18} />
          </button>
          <span style={{ fontSize: '0.85rem', color: '#94a3b8' }}>
            Page {page} of {totalPages}
          </span>
          <button 
            className="btn-ghost" 
            style={{ padding: '6px' }}
            disabled={page === totalPages}
            onClick={() => setPage(p => Math.min(totalPages, p + 1))}
          >
            <ChevronRight size={18} />
          </button>
        </div>
      )}
    </div>
  )
}
