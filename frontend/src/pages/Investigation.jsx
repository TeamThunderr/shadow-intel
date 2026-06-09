import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getInvestigationStatus, getInvestigationReport } from '../api/client'
import AgentStatusPanel from '../components/AgentStatusPanel'
import OwnershipGraph from '../components/OwnershipGraph'
import FinancialFlowGraph from '../components/FinancialFlowGraph'
import EvidenceFeed from '../components/EvidenceFeed'
import ConfidenceMeter from '../components/ConfidenceMeter'
import { FileText, Download } from 'lucide-react'

const RISK_COLORS = {
  critical: '#ef4444',
  high: '#f97316',
  medium: '#eab308',
  low: '#22c55e'
}

// MOCK DATA TO DEMONSTRATE UI WHILE BACKEND (TASK B) IS NOT YET BUILT
const MOCK_REPORT = {
  entity_name: "Mossack Fonseca (Demo)",
  risk_level: "critical",
  unified_confidence: 0.92,
  narrative_summary: "This is a demo intelligence summary. High risk flags detected in Panama and BVI jurisdictions involving shell company layering. Agents have uncovered strong ties to sanctioned entities.",
  ownership_unwind: {
    data: {
      ownership_graph: {
        nodes: [
          { id: '1', name: 'Mossack Fonseca', entity_type: 'company', jurisdiction: 'PA' },
          { id: '2', name: 'John Doe Shell', entity_type: 'company', jurisdiction: 'VG' },
          { id: '3', name: 'Jane Smith', entity_type: 'person', jurisdiction: 'US', ownership_pct: 0.85 },
          { id: '4', name: 'Secret Holdings', entity_type: 'company', jurisdiction: 'KY' }
        ],
        edges: [
          { source: '1', target: '2' },
          { source: '3', target: '2' },
          { source: '2', target: '4' }
        ]
      }
    }
  },
  money_trail: {
    data: {
      financial_flows: {
        nodes: [
          { id: 'Wallet A', type: 'wallet', label: 'Wallet A' },
          { id: 'Offshore Bank', type: 'bank', label: 'Offshore Bank' },
          { id: 'Crypto Mixer', type: 'wallet', label: 'Crypto Mixer' }
        ],
        edges: [
          { source: 'Wallet A', target: 'Offshore Bank', amount: 5000000, risk_flag: 'placement' },
          { source: 'Offshore Bank', target: 'Crypto Mixer', amount: 4800000, risk_flag: 'layering' }
        ]
      }
    }
  },
  evidence_chain: [
    { step: 1, source_module: 'ghost_tracker', finding: 'Identified entity in Panama Papers leak.', confidence: 0.99 },
    { step: 2, source_module: 'money_trail', finding: 'Suspicious $5M wire transfer detected.', confidence: 0.85 },
    { step: 3, source_module: 'ownership_unwind', finding: 'Uncovered BVI shell company.', confidence: 0.92 }
  ]
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

  const { data: rawReport } = useQuery({
    queryKey: ['report', entityId],
    queryFn: () => getInvestigationReport(entityId).then(r => r.data),
    enabled: status?.overall_status === 'complete',
    retry: false,
  })

  // Use mock data if the backend returns an empty object (since backend isn't built yet)
  const report = (rawReport && rawReport.ownership_unwind?.data?.ownership_graph) ? rawReport : MOCK_REPORT

  const isRunning = !status || status?.overall_status === 'running'
  const isFailed = status?.overall_status === 'failed'
  const riskColor = report ? RISK_COLORS[report.risk_level] : '#3b82f6'

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '2rem' }}>
      {/* Header - Top */}
      <div className="glass-card" style={{ padding: '1.5rem 2rem', marginBottom: '1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: '#475569', fontFamily: 'JetBrains Mono, monospace', marginBottom: '0.4rem' }}>
            Investigation ID: {entityId}
          </div>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 800, letterSpacing: '-0.02em', color: '#e2e8f0', display: 'flex', alignItems: 'center', gap: '10px' }}>
            {report ? report.entity_name : 'Investigation in progress…'}
          </h1>
        </div>
        {report && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem' }}>
            <ConfidenceMeter value={report.unified_confidence} size={64} />
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '280px 1fr 340px', gap: '1.5rem', alignItems: 'start' }}>
        
        {/* Left Column: Status Panel */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <AgentStatusPanel agents={status?.agents} />
          
          {report && (
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#3b82f6', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
                Intelligence Summary
              </h2>
              <p style={{ color: '#cbd5e1', lineHeight: 1.6, fontSize: '0.85rem', whiteSpace: 'pre-wrap' }}>
                {report.narrative_summary}
              </p>
            </div>
          )}
        </div>

        {/* Center Column: Graphs */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem', minWidth: 0 }}>
          {isRunning ? (
            <div className="glass-card" style={{ padding: '4rem', textAlign: 'center' }}>
              <div style={{ fontSize: '3rem', marginBottom: '1rem', animation: 'pulse-ring 2s infinite', display: 'inline-block' }}>🔍</div>
              <div style={{ fontWeight: 600, color: '#94a3b8', fontSize: '1.2rem', marginBottom: '0.5rem' }}>Agents running…</div>
              <div style={{ fontSize: '0.9rem', color: '#475569' }}>Querying sanctions lists, corporate registries, and blockchain networks.</div>
              <div className="progress-bar" style={{ marginTop: '2rem', maxWidth: 300, margin: '2rem auto 0' }}>
                <div className="progress-bar-fill" style={{ width: '60%' }} />
              </div>
            </div>
          ) : isFailed ? (
            <div className="glass-card" style={{ padding: '3rem', textAlign: 'center', marginTop: '2rem', border: '1px solid #ef4444' }}>
              <div style={{ fontSize: '2.5rem', marginBottom: '1rem' }}>❌</div>
              <div style={{ fontWeight: 600, color: '#ef4444', marginBottom: '0.5rem' }}>Investigation Failed</div>
              <div style={{ fontSize: '0.85rem', color: '#475569' }}>An error occurred while running the agents. Please check the backend logs.</div>
            </div>
          ) : (
            <>
              {/* Ownership Graph */}
              <div className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
                <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#6366f1', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
                  Ownership Structure
                </h2>
                <div style={{ flex: 1, minHeight: 320 }}>
                  <OwnershipGraph graph={report?.ownership_unwind?.data?.ownership_graph} />
                </div>
              </div>

              {/* Financial Flow Graph */}
              {report?.money_trail?.data?.financial_flows && (
                <div className="glass-card" style={{ padding: '1.5rem', display: 'flex', flexDirection: 'column' }}>
                  <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#8b5cf6', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
                    Financial Flows
                  </h2>
                  <div style={{ flex: 1, minHeight: 300 }}>
                    <FinancialFlowGraph flows={report.money_trail.data.financial_flows} />
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Right Column: Evidence Feed */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div className="glass-card" style={{ padding: '1.5rem' }}>
            <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#ec4899', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
              Evidence Chain
            </h2>
            <EvidenceFeed chain={report?.evidence_chain || []} />
          </div>
          
          {/* Bottom/Right Download Section */}
          {report && (
            <div className="glass-card" style={{ padding: '1.5rem' }}>
              <h2 style={{ fontSize: '0.85rem', fontWeight: 700, color: '#e2e8f0', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '1rem' }}>
                Export Report
              </h2>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                <a href={`http://localhost:8000/report/${entityId}/pdf`} target="_blank" rel="noreferrer" className="btn-primary" style={{ justifyContent: 'center', background: '#334155' }}>
                  <Download size={16} /> Download PDF
                </a>
                <a href={`http://localhost:8000/report/${entityId}/markdown`} target="_blank" rel="noreferrer" className="btn-ghost" style={{ justifyContent: 'center' }}>
                  <FileText size={16} /> View Markdown
                </a>
              </div>
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
