const AGENT_META = {
  ghost_tracker: { label: 'Ghost Tracker', icon: '👻', color: '#3b82f6' },
  money_trail: { label: 'Money Trail', icon: '💸', color: '#8b5cf6' },
  ownership_unwind: { label: 'Ownership Unwind', icon: '🕸️', color: '#6366f1' },
  dark_signal: { label: 'Dark Signal', icon: '📡', color: '#ec4899' },
  resurface_engine: { label: 'Resurface Engine', icon: '🔔', color: '#f59e0b' },
  orchestrator: { label: 'Orchestrator', icon: '🧠', color: '#10b981' },
}

const STATUS_LABELS = {
  pending: 'Pending',
  running: 'Running',
  complete: 'Done',
  failed: 'Failed',
}

export default function AgentStatusPanel({ agents }) {
  if (!agents) return null

  return (
    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
      {Object.entries(agents).map(([key, status]) => {
        const meta = AGENT_META[key] || { label: key, icon: '🤖', color: '#64748b' }
        return (
          <div
            key={key}
            className="glass-card"
            style={{
              padding: '0.75rem 1rem',
              display: 'flex',
              alignItems: 'center',
              gap: '0.6rem',
              minWidth: 160,
              borderColor: status === 'running' ? `${meta.color}40` : undefined,
              boxShadow: status === 'running' ? `0 0 12px ${meta.color}20` : undefined,
              transition: 'all 0.3s',
            }}
          >
            <span style={{ fontSize: '1.1rem' }}>{meta.icon}</span>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: status === 'complete' ? meta.color : '#64748b', letterSpacing: '0.02em' }}>
                {meta.label}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 2 }}>
                <span className={`status-dot ${status}`} />
                <span style={{ fontSize: '0.72rem', color: '#475569' }}>{STATUS_LABELS[status]}</span>
              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
