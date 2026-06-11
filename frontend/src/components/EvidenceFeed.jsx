import { Activity, Clock } from 'lucide-react'

export default function EvidenceFeed({ report }) {
  const allEvidence = [
    ...(report?.ghost_tracker?.evidence   || []),
    ...(report?.money_trail?.evidence     || []),
    ...(report?.ownership_unwind?.evidence || []),
    ...(report?.dark_signal?.evidence     || []),
    ...(report?.resurface_watch?.evidence || []),
  ].sort((a, b) => b.confidence - a.confidence)

  if (allEvidence.length === 0) return null

  return (
    <div className="card" style={{ padding: '1.25rem' }}>
      <div className="section-label" style={{ marginBottom: '1.25rem', display: 'flex', alignItems: 'center', gap: 6 }}>
        <Activity size={14} /> Full Evidence Feed ({allEvidence.length} items)
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))', gap: '0.85rem' }}>
        {allEvidence.map((ev, i) => (
          <div key={i} style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border)',
            borderRadius: 'var(--radius-sm)', padding: '12px 14px',
            display: 'flex', flexDirection: 'column', gap: 8
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <span className="source-badge" style={{ background: 'var(--bg-hover)', color: 'var(--text-secondary)' }}>
                {ev.source}
              </span>
              <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 600 }}>
                {(ev.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)', lineHeight: 1.5 }}>
              {ev.detail}
            </div>
            {ev.url && (
              <a href={ev.url} target="_blank" rel="noreferrer" style={{ fontSize: '0.75rem', fontWeight: 500, marginTop: 'auto' }}>
                View source
              </a>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
