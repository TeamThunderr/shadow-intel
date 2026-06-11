import { CheckCircle2, Circle, Search, Activity, Building2, Clock, AlertTriangle } from 'lucide-react'

const AGENT_ICONS = {
  ghost_tracker:    Search,
  money_trail:      Activity,
  ownership_unwind: Building2,
  dark_signal:      Activity,
  resurface_watch:  Clock,
}

const AGENT_LABELS = {
  ghost_tracker:    'Ghost Tracker',
  money_trail:      'Money Trail',
  ownership_unwind: 'Ownership Unwind',
  dark_signal:      'Dark Signal',
  resurface_watch:  'Resurface Engine',
}

const RISK_COLORS = {
  critical: 'var(--risk-critical)',
  high:     'var(--risk-high)',
  medium:   'var(--risk-medium)',
  low:      'var(--risk-low)',
}

export default function AgentStatusPanel({ agents, report }) {
  const agentList = [
    'ghost_tracker',
    'money_trail',
    'ownership_unwind',
    'dark_signal',
    'resurface_watch'
  ]

  return (
    <div className="card" style={{ padding: '1.25rem', height: '100%' }}>
      <div className="section-label" style={{ marginBottom: '1.25rem' }}>Agent Pipeline</div>
      
      <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
        {agentList.map((agentKey, i) => {
          const statusObj = agents?.[agentKey] || { status: 'pending' }
          const reportObj = report?.[agentKey]
          const isComplete = statusObj.status === 'complete' || reportObj
          const isRunning = statusObj.status === 'running'
          const isFailed = statusObj.status === 'failed'

          const Icon = AGENT_ICONS[agentKey] || Circle
          const riskLevel = reportObj?.risk_level || 'low'
          const riskColor = RISK_COLORS[riskLevel]

          return (
            <div key={agentKey} style={{ display: 'flex', gap: 12, position: 'relative' }}>
              {/* Timeline connecting line */}
              {i < agentList.length - 1 && (
                <div style={{
                  position: 'absolute', left: 11, top: 24, bottom: -20,
                  width: 2, background: isComplete ? 'var(--accent-blue-light)' : 'var(--border)',
                  zIndex: 0
                }} />
              )}

              {/* Status Icon */}
              <div style={{ position: 'relative', zIndex: 1, marginTop: 2 }}>
                {isComplete ? (
                  <CheckCircle2 size={24} color="var(--accent-blue)" fill="var(--bg-card)" />
                ) : isRunning ? (
                  <div style={{
                    width: 24, height: 24, borderRadius: '50%',
                    border: '2px solid var(--accent-blue-light)',
                    borderTopColor: 'var(--accent-blue)',
                    animation: 'spin 1s linear infinite',
                    background: 'var(--bg-card)'
                  }} />
                ) : isFailed ? (
                  <AlertTriangle size={24} color="var(--risk-critical)" fill="var(--bg-card)" />
                ) : (
                  <Circle size={24} color="var(--border-bright)" fill="var(--bg-card)" />
                )}
              </div>

              {/* Agent Details */}
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div style={{
                    fontWeight: 700, fontSize: '0.85rem',
                    color: isComplete || isRunning ? 'var(--text-primary)' : 'var(--text-muted)',
                    display: 'flex', alignItems: 'center', gap: 6
                  }}>
                    <Icon size={14} style={{ color: isComplete || isRunning ? 'var(--accent-blue)' : 'var(--text-muted)' }} />
                    {AGENT_LABELS[agentKey]}
                  </div>
                  {isComplete && reportObj && (
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase',
                      padding: '2px 6px', borderRadius: 4,
                      background: `var(--risk-${riskLevel}-bg)`, color: riskColor,
                      border: `1px solid ${riskColor}40`
                    }}>
                      {riskLevel}
                    </span>
                  )}
                </div>

                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>
                  {isComplete ? (
                    reportObj?.summary || 'Analysis complete.'
                  ) : isRunning ? (
                    <span className="animate-pulse" style={{ color: 'var(--accent-blue)' }}>Processing…</span>
                  ) : isFailed ? (
                    <span style={{ color: 'var(--risk-critical)' }}>Failed to complete.</span>
                  ) : (
                    'Waiting…'
                  )}
                </div>

                {/* Evidence count pill if complete */}
                {isComplete && reportObj?.evidence?.length > 0 && (
                  <div style={{ marginTop: 6, display: 'flex' }}>
                    <span style={{
                      fontSize: '0.65rem', fontWeight: 600, color: 'var(--accent-teal)',
                      background: 'var(--accent-teal-light)', padding: '2px 8px', borderRadius: 99
                    }}>
                      {reportObj.evidence.length} evidence items
                    </span>
                  </div>
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
