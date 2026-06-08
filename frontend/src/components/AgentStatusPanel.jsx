import { useEffect, useState } from 'react'
import { CheckCircle2, Clock, Activity, AlertTriangle } from 'lucide-react'

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

const StatusIcon = ({ status, color }) => {
  if (status === 'complete') return <CheckCircle2 size={14} color={color} />
  if (status === 'running') return <Activity size={14} color={color} className="animate-pulse" />
  if (status === 'failed') return <AlertTriangle size={14} color="#ef4444" />
  return <Clock size={14} color="#64748b" />
}

export default function AgentStatusPanel({ agents }) {
  const [lastUpdate, setLastUpdate] = useState(null)

  useEffect(() => {
    if (agents) {
      setLastUpdate(new Date().toLocaleTimeString())
    }
  }, [agents])

  if (!agents) return null

  return (
    <div style={{ marginBottom: '1.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ fontSize: '0.85rem', fontWeight: 600, color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Agent Network Status
        </h3>
        {lastUpdate && (
          <div style={{ fontSize: '0.75rem', color: '#64748b', display: 'flex', alignItems: 'center', gap: 4 }}>
            <Clock size={12} /> Last updated: {lastUpdate}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
        {Object.entries(agents).map(([key, status]) => {
          const meta = AGENT_META[key] || { label: key, icon: '🤖', color: '#64748b' }
          const isRunning = status === 'running'
          const isComplete = status === 'complete'
          
          return (
            <div
              key={key}
              className="glass-card"
              style={{
                padding: '0.75rem 1rem',
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                flex: '1 1 160px',
                minWidth: 160,
                borderColor: isRunning ? `${meta.color}50` : isComplete ? 'rgba(16,185,129,0.3)' : undefined,
                boxShadow: isRunning ? `0 0 15px ${meta.color}25` : undefined,
                background: isRunning ? `linear-gradient(145deg, rgba(13,20,36,0.9), ${meta.color}15)` : undefined,
                transition: 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)',
              }}
            >
              <span style={{ fontSize: '1.25rem', opacity: status === 'pending' ? 0.5 : 1 }}>{meta.icon}</span>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, color: isComplete ? '#e2e8f0' : '#cbd5e1', letterSpacing: '0.02em', marginBottom: 2 }}>
                  {meta.label}
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <StatusIcon status={status} color={meta.color} />
                  <span style={{ 
                    fontSize: '0.72rem', 
                    color: isRunning ? meta.color : isComplete ? '#10b981' : status === 'failed' ? '#ef4444' : '#64748b',
                    fontWeight: isRunning || isComplete ? 600 : 400
                  }}>
                    {STATUS_LABELS[status]}
                  </span>
                </div>
                {isRunning && (
                  <div style={{ height: 2, background: 'rgba(255,255,255,0.1)', borderRadius: 2, marginTop: 6, overflow: 'hidden' }}>
                    <div style={{ height: '100%', background: meta.color, width: '60%', animation: 'pulse-ring 1.5s infinite' }} />
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
