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
    top_evidence: ['Alias match in OCCRP Aleph database', 'UAE company registration 2025-11'],
  },
]

const RISK_COLORS = {
  critical: '#f87171',
  high: '#fbbf24',
  medium: '#60a5fa',
  low: '#34d399',
}

export default function AlertHistory() {
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

      <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
        {MOCK_ALERTS.map((alert) => (
          <div key={alert.alert_id} className="glass-card animate-slide-up" style={{ padding: '1.5rem' }}>
            <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '0.75rem' }}>
              <div>
                <span className={`badge badge-${alert.risk_level}`} style={{ marginRight: '0.75rem' }}>
                  {alert.risk_level}
                </span>
                <span style={{ fontWeight: 700, fontSize: '1rem' }}>{alert.entity_name}</span>
              </div>
              <span style={{ fontSize: '0.75rem', color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>
                {new Date(alert.timestamp).toLocaleString()}
              </span>
            </div>

            <div style={{ fontSize: '0.9rem', color: '#94a3b8', marginBottom: '0.75rem' }}>
              {alert.match_event}
            </div>

            <div style={{ display: 'flex', gap: '1rem', fontSize: '0.8rem', color: '#475569' }}>
              <span>Confidence: <strong style={{ color: RISK_COLORS[alert.risk_level] }}>{(alert.confidence * 100).toFixed(0)}%</strong></span>
              <span>Jurisdiction: <strong style={{ color: '#94a3b8' }}>{alert.jurisdiction}</strong></span>
              <span>Type: <strong style={{ color: '#94a3b8' }}>{alert.alert_type}</strong></span>
            </div>

            {alert.top_evidence.length > 0 && (
              <div style={{ marginTop: '0.75rem', paddingTop: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: '0.72rem', color: '#475569', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '0.4rem' }}>
                  Evidence
                </div>
                {alert.top_evidence.map((e, i) => (
                  <div key={i} style={{ fontSize: '0.82rem', color: '#64748b', paddingLeft: '0.75rem', borderLeft: '2px solid rgba(59,130,246,0.3)', marginBottom: '0.25rem' }}>
                    {e}
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
