import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getInvestigationStatus, getInvestigationReport } from '../api/client'
import AgentStatusPanel from '../components/AgentStatusPanel'
import OwnershipGraph from '../components/OwnershipGraph'
import FinancialFlowGraph from '../components/FinancialFlowGraph'
import EvidenceFeed from '../components/EvidenceFeed'
import ConfidenceMeter from '../components/ConfidenceMeter'

const RISK_COLORS = {
  critical: '#f87171',
  high: '#fbbf24',
  medium: '#60a5fa',
  low: '#34d399',
}

export default function Investigation() {
  const { entityId } = useParams()

  const { data: status } = useQuery({
    queryKey: ['status', entityId],
    queryFn: () => getInvestigationStatus(entityId).then(r => r.data),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data || data?.overall_status === 'running') return 2000
      return false
    },
  })

  const { data: report } = useQuery({
    queryKey: ['report', entityId],
    queryFn: () => getInvestigationReport(entityId).then(r => r.data),
    enabled: status?.overall_status === 'complete',
    retry: false,
  })

  const isRunning = !status || status?.overall_status === 'running'
  const isFailed = status?.overall_status === 'failed'
  const riskColor = report ? RISK_COLORS[report.risk_level] : '#3b82f6'

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '2rem' }}>
      {/* Header */}
      <div style={{ marginBottom: '2rem', display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#475569', fontFamily: 'JetBrains Mono, monospace', marginBottom: '0.4rem' }}>
            Investigation ID: {entityId}
          </div>
          <h1 style={{ fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.02em', color: '#e2e8f0' }}>
            {report ? report.entity_name : 'Investigation in progress…'}
          </h1>
        </div>
        {report && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <span className={`badge badge-${report.risk_level}`}>
              {report.risk_level}
            </span>
            <ConfidenceMeter value={report.unified_confidence} color={riskColor} />
          </div>
        )}
      </div>

      {/* Agent status row */}
      <AgentStatusPanel agents={status?.agents} />

      {/* Main content */}
      {isRunning && (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', marginTop: '2rem' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>🔍</div>
          <div style={{ fontWeight: 600, color: '#94a3b8', marginBottom: '0.5rem' }}>Agents running…</div>
          <div style={{ fontSize: '0.85rem', color: '#475569' }}>Querying sanctions lists, corporate registries, blockchain explorers</div>
          <div className="progress-bar" style={{ marginTop: '1.5rem', maxWidth: 300, margin: '1.5rem auto 0' }}>
            <div className="progress-bar-fill" style={{ width: '60%', animation: 'none' }} />
          </div>
        </div>
      )}

      {isFailed && (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', marginTop: '2rem', border: '1px solid #ef4444' }}>
          <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>❌</div>
          <div style={{ fontWeight: 600, color: '#ef4444', marginBottom: '0.5rem' }}>Investigation Failed</div>
          <div style={{ fontSize: '0.85rem', color: '#475569' }}>An error occurred while running the agents. Please check the backend logs.</div>
        </div>
      )}

      {report && (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem', marginTop: '1.5rem' }}>
          {/* Narrative */}
          <div className="glass-card" style={{ padding: '1.5rem', gridColumn: '1 / -1' }}>
            <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
              Intelligence Summary
            </h2>
            <p style={{ color: '#cbd5e1', lineHeight: 1.75, fontSize: '0.95rem', whiteSpace: 'pre-wrap' }}>
              {report.narrative_summary}
            </p>
          </div>

          {/* Ownership graph */}
          {report.ownership_unwind?.data?.ownership_graph && (
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#6366f1', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
                Ownership Structure
              </h2>
              <OwnershipGraph graph={report.ownership_unwind.data.ownership_graph} />
            </div>
          )}

          {/* Evidence feed */}
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ec4899', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
              Evidence Chain ({report.evidence_chain?.length ?? 0} findings)
            </h2>
            <EvidenceFeed chain={report.evidence_chain} />
          </div>
        </div>
      )}
    </div>
  )
}
