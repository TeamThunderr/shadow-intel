import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getInvestigationStatus, getInvestigationReport } from '../api/client'
import AgentStatusPanel from '../components/AgentStatusPanel'
import OwnershipGraph from '../components/OwnershipGraph'
import ConfidenceMeter from '../components/ConfidenceMeter'
import EvidenceFeed from '../components/EvidenceFeed'
import { Download, FileText, ArrowLeft, ExternalLink, Activity, ShieldAlert, Zap, Building2, Search } from 'lucide-react'

const TABS = ['Overview', 'Ownership Graph', 'Money Trail', 'OSINT Signals']

const RISK_COLORS = {
  critical: 'var(--risk-critical)',
  high:     'var(--risk-high)',
  medium:   'var(--risk-medium)',
  low:      'var(--risk-low)',
}

const SOURCE_BADGE_COLORS = {
  'OFAC SDN':            { bg: 'var(--risk-critical-bg)', color: 'var(--risk-critical)' },
  'UN Security Council': { bg: 'var(--accent-blue-light)', color: 'var(--accent-blue)' },
  'OpenSanctions':       { bg: 'var(--accent-purple-light)', color: 'var(--accent-purple)' },
  'ICIJ':                { bg: 'var(--accent-amber-light)', color: 'var(--accent-amber)' },
  'OCCRP':               { bg: 'var(--risk-high-bg)', color: 'var(--risk-high)' },
  'Etherscan':           { bg: 'var(--accent-teal-light)', color: 'var(--accent-teal)' },
  'FATF':                { bg: 'var(--risk-medium-bg)', color: 'var(--risk-medium)' },
  'Money Trail Agent':   { bg: 'var(--accent-purple-light)', color: 'var(--accent-purple)' },
}

function SourceBadge({ source }) {
  const style = SOURCE_BADGE_COLORS[source] || { bg: 'var(--bg-hover)', color: 'var(--text-secondary)' }
  return (
    <span className="source-badge" style={{ background: style.bg, color: style.color }}>
      {source}
    </span>
  )
}

function PatternBadge({ label, active }) {
  if (!active) return null
  const colors = {
    PLACEMENT:   { bg: 'var(--accent-blue-light)',  color: 'var(--accent-blue)' },
    LAYERING:    { bg: 'var(--accent-amber-light)',  color: 'var(--accent-amber)' },
    INTEGRATION: { bg: 'var(--risk-critical-bg)',  color: 'var(--risk-critical)' },
  }
  const c = colors[label] || { bg: 'var(--bg-hover)', color: 'var(--text-secondary)' }
  return (
    <span className="badge" style={{ background: c.bg, color: c.color, border: `1px solid ${c.color}40` }}>
      <ShieldAlert size={10} /> {label}
    </span>
  )
}

// ── Overview Tab ──────────────────────────────────────────────────────────────
function OverviewTab({ report }) {
  const allEvidence = [
    ...(report?.ghost_tracker?.evidence   || []),
    ...(report?.money_trail?.evidence     || []),
    ...(report?.ownership_unwind?.evidence || []),
    ...(report?.dark_signal?.evidence     || []),
    ...(report?.resurface_watch?.evidence || []),
  ].sort((a, b) => b.confidence - a.confidence)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
        {[
          { label: 'Evidence Items',   value: allEvidence.length },
          { label: 'Sources Hit',      value: new Set(allEvidence.map(e => e.source)).size },
          { label: 'Jurisdictions',    value: (report?.ghost_tracker?.data?.fingerprint?.jurisdictions || []).length },
          { label: 'Aliases Found',    value: (report?.ghost_tracker?.data?.fingerprint?.aliases || []).length },
        ].map(({ label, value }) => (
          <div key={label} style={{
            background: 'var(--bg-secondary)', border: '1px solid var(--border)',
            borderRadius: 8, padding: '12px 14px', textAlign: 'center',
          }}>
            <div style={{ fontSize: '1.5rem', fontWeight: 800, color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>
              {value}
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2, textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600 }}>
              {label}
            </div>
          </div>
        ))}
      </div>

      {/* Narrative */}
      <div className="card" style={{ padding: '1.25rem', boxShadow: 'none' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
          <h3 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--accent-purple)', textTransform: 'uppercase', letterSpacing: '0.07em', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Zap size={14} /> Foundry IQ — Intelligence Summary
          </h3>
          <span style={{ fontSize: '0.65rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>Powered by Azure AI Foundry</span>
        </div>
        <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, fontSize: '0.87rem', whiteSpace: 'pre-wrap' }}>
          {report?.narrative_summary || 'Narrative not available.'}
        </p>
      </div>

      {/* Evidence chain */}
      {(report?.evidence_chain || []).length > 0 && (
        <div className="card" style={{ padding: '1.25rem', boxShadow: 'none' }}>
          <h3 style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--accent-teal)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '0.75rem', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Activity size={14} /> Evidence Chain
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {report.evidence_chain.map((step, i) => (
              <div key={i} style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
                <div style={{
                  width: 22, height: 22, borderRadius: '50%', flexShrink: 0,
                  background: 'var(--accent-teal-light)', border: '1px solid var(--accent-teal)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontSize: '0.65rem', fontWeight: 700, color: 'var(--accent-teal)',
                  fontFamily: 'var(--font-mono)',
                }}>{step.step}</div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', marginBottom: 2 }}>{step.finding}</div>
                  <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                    <SourceBadge source={step.source_module?.replace('_', ' ')} />
                    <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                      {(step.confidence * 100).toFixed(0)}% confidence
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Money Trail Tab ───────────────────────────────────────────────────────────
function MoneyTrailTab({ report }) {
  const data     = report?.money_trail?.data || {}
  const patterns = data.laundering_patterns || {}
  const flows    = (data.financial_flows    || []).slice(0, 20)
  const hasData  = flows.length > 0 || data.sanctions_hits?.length > 0

  if (!hasData) {
    return (
      <div className="empty-state" style={{ minHeight: 300 }}>
        <div className="empty-state-icon"><Activity size={24} /></div>
        <div className="empty-state-title">No Money Trail Data</div>
        <div className="empty-state-desc">No blockchain addresses or financial flows linked to this entity were found.</div>
      </div>
    )
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Pattern badges */}
      {(patterns.placement_detected || patterns.layering_detected || patterns.integration_detected) && (
        <div className="card" style={{ padding: '1rem 1.25rem', boxShadow: 'none' }}>
          <div className="section-label" style={{ marginBottom: 8 }}>Detected Patterns</div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <PatternBadge label="PLACEMENT"   active={patterns.placement_detected} />
            <PatternBadge label="LAYERING"    active={patterns.layering_detected} />
            <PatternBadge label="INTEGRATION" active={patterns.integration_detected} />
          </div>
          {patterns.placement_evidence && (
            <div style={{ marginTop: 8, fontSize: '0.78rem', color: 'var(--text-secondary)' }}>
              {patterns.placement_evidence} {patterns.layering_evidence} {patterns.integration_evidence}
            </div>
          )}
        </div>
      )}

      {/* High-risk jurisdictions */}
      {(data.high_risk_jurisdictions || []).length > 0 && (
        <div className="card" style={{ padding: '1rem 1.25rem', boxShadow: 'none' }}>
          <div className="section-label" style={{ color: 'var(--risk-medium)', marginBottom: 8, display: 'flex', alignItems: 'center', gap: 6 }}>
            <ShieldAlert size={12} /> High-Risk FATF Jurisdictions
          </div>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
            {data.high_risk_jurisdictions.map(j => (
              <span key={j} style={{
                padding: '3px 10px', borderRadius: 5,
                background: 'var(--risk-medium-bg)', color: 'var(--risk-medium)',
                border: '1px solid rgba(202,138,4,0.3)',
                fontSize: '0.75rem', fontWeight: 700,
              }}>{j}</span>
            ))}
          </div>
        </div>
      )}

      {/* Transaction hops */}
      {flows.length > 0 && (
        <div className="card" style={{ padding: '1rem 1.25rem', boxShadow: 'none' }}>
          <div className="section-label" style={{ marginBottom: 10 }}>
            Transaction Hops ({data.total_hops_traced} total traced)
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {flows.map((f, i) => (
              <div key={i} style={{
                display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 10px', borderRadius: 7,
                background: 'var(--bg-secondary)', border: '1px solid var(--border)',
                fontSize: '0.76rem',
              }}>
                <span style={{
                  padding: '2px 7px', borderRadius: 4, flexShrink: 0, fontSize: '0.65rem', fontWeight: 700,
                  ...{
                    placement:   { background: 'var(--accent-blue-light)',  color: 'var(--accent-blue)' },
                    layering:    { background: 'var(--accent-amber-light)',  color: 'var(--accent-amber)' },
                    integration: { background: 'var(--risk-critical-bg)', color: 'var(--risk-critical)' },
                    clean:       { background: 'var(--risk-low-bg)', color: 'var(--risk-low)' },
                  }[f.risk_flag] || {},
                }}>{f.risk_flag?.toUpperCase()}</span>
                <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
                  {String(f.from).slice(0, 8)}…
                </span>
                <span style={{ color: 'var(--text-muted)' }}>→</span>
                <span style={{ color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', fontSize: '0.7rem' }}>
                  {String(f.to).slice(0, 8)}…
                </span>
                <span style={{ marginLeft: 'auto', color: 'var(--text-primary)', fontWeight: 600 }}>
                  ${(f.amount_usd || 0).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
                {f.tx_hash && (
                  <a href={`https://etherscan.io/tx/${f.tx_hash}`} target="_blank" rel="noreferrer"
                     style={{ color: 'var(--accent-teal)', flexShrink: 0 }}>
                    <ExternalLink size={14} />
                  </a>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── OSINT Tab ─────────────────────────────────────────────────────────────────
function OsintTab({ report }) {
  const signals = report?.dark_signal?.data?.signals || []
  const evidence = report?.dark_signal?.evidence || []

  if (!signals.length && !evidence.length) {
    return (
      <div className="empty-state" style={{ minHeight: 300 }}>
        <div className="empty-state-icon"><Activity size={24} /></div>
        <div className="empty-state-title">No OSINT Signals</div>
        <div className="empty-state-desc">No news articles or leaks found for this entity.</div>
      </div>
    )
  }

  const items = evidence.length ? evidence : signals.map(s => ({
    source: s.source, detail: `[${s.title}] ${s.summary}`,
    confidence: s.confidence, url: s.url,
  }))

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.85rem' }}>
      {items.map((item, i) => (
        <div key={i} className="card" style={{ padding: '1rem', display: 'flex', flexDirection: 'column', gap: 8, boxShadow: 'none' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <SourceBadge source={item.source} />
            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              {(item.confidence * 100).toFixed(0)}%
            </span>
          </div>
          <p style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.55, flex: 1 }}>
            {item.detail?.slice(0, 200)}{item.detail?.length > 200 ? '…' : ''}
          </p>
          {item.url && (
            <a href={item.url} target="_blank" rel="noreferrer"
               style={{ fontSize: '0.72rem', color: 'var(--accent-blue)', display: 'flex', alignItems: 'center', gap: 4, fontWeight: 500 }}>
              <ExternalLink size={12} /> View source
            </a>
          )}
        </div>
      ))}
    </div>
  )
}

// ── Main Investigation Page ───────────────────────────────────────────────────
export default function Investigation() {
  const { entityId } = useParams()
  const navigate     = useNavigate()
  const [activeTab,  setActiveTab]  = useState(0)

  const { data: status } = useQuery({
    queryKey:       ['status', entityId],
    queryFn:        () => getInvestigationStatus(entityId).then(r => r.data),
    refetchInterval: (query) => {
      const d = query.state.data
      if (!d || d?.overall_status === 'running') return 2000
      return false
    },
  })

  const { data: report } = useQuery({
    queryKey: ['report', entityId],
    queryFn:  () => getInvestigationReport(entityId).then(r => r.data),
    enabled:  status?.overall_status === 'complete',
    retry:    false,
  })

  const isRunning = !status || status?.overall_status === 'running'
  const isFailed  = status?.overall_status === 'failed'

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '1.5rem 2rem', minHeight: '100vh' }}>
      {/* ── Header ──────────────────────────────────────────────────────────── */}
      <div className="card" style={{
        padding: '1rem 1.5rem', marginBottom: '1.25rem',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '1rem',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button onClick={() => navigate('/')} className="btn-ghost" style={{ padding: '6px 10px', height: 34 }}>
            <ArrowLeft size={16} />
          </button>
          <div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)', marginBottom: 2 }}>
              {entityId}
            </div>
            <h1 className="page-title">
              {report ? report.entity_name : isRunning ? 'Investigation in progress…' : 'Investigation'}
            </h1>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem' }}>
          {report && (
            <>
              <span className={`badge badge-${report.risk_level}`}>
                {report.risk_level?.toUpperCase()}
              </span>
              <ConfidenceMeter value={report.unified_confidence} size={56} />
            </>
          )}
          {report && (
            <div style={{ display: 'flex', gap: 8 }}>
              <a
                href={`http://localhost:8000/investigate/${entityId}/report/markdown`}
                target="_blank" rel="noreferrer"
                className="btn-ghost"
                style={{ padding: '7px 12px', fontSize: '0.78rem' }}
              >
                <FileText size={14} /> MD
              </a>
            </div>
          )}
        </div>
      </div>

      {/* ── Two-column layout ────────────────────────────────────────────────── */}
      <div style={{ display: 'grid', gridTemplateColumns: '240px 1fr', gap: '1.25rem', alignItems: 'start' }}>

        {/* Left: Agent pipeline */}
        <div>
          <AgentStatusPanel agents={status?.agents} report={report} />
        </div>

        {/* Right: Tab content */}
        <div className="card" style={{ overflow: 'hidden', minHeight: 500 }}>
          {/* Tab bar */}
          <div className="tab-bar">
            {TABS.map((tab, i) => (
              <button
                key={tab}
                className={`tab-btn${activeTab === i ? ' active' : ''}`}
                onClick={() => setActiveTab(i)}
                disabled={isRunning}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* Tab content */}
          <div style={{ padding: '1.25rem' }}>
            {isRunning ? (
              <div className="agent-runner-loader">
                <div className="agent-runner-orbs">
                  <div className="agent-orb" style={{ background: 'var(--accent-blue)' }} />
                  <div className="agent-orb" style={{ background: 'var(--accent-purple)' }} />
                  <div className="agent-orb" style={{ background: 'var(--accent-teal)' }} />
                  <div className="agent-orb" style={{ background: 'var(--risk-high)' }} />
                  <div className="agent-orb" style={{ background: 'var(--accent-amber)' }} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '1.1rem', marginBottom: 6 }}>
                    Agents running…
                  </div>
                  <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', maxWidth: 380, lineHeight: 1.5 }}>
                    Querying sanctions lists, corporate registries, and blockchain networks simultaneously.
                  </div>
                </div>
              </div>
            ) : isFailed ? (
              <div className="empty-state">
                <div className="empty-state-icon" style={{ background: 'var(--risk-critical-bg)', color: 'var(--risk-critical)' }}><ShieldAlert size={24} /></div>
                <div className="empty-state-title" style={{ color: 'var(--risk-critical)' }}>Investigation Failed</div>
                <div className="empty-state-desc">Check the backend logs for details.</div>
              </div>
            ) : (
              <>
                {activeTab === 0 && report && <OverviewTab report={report} />}
                {activeTab === 1 && (
                  <OwnershipGraph
                    graphData={report?.ownership_unwind?.data?.ownership_graph}
                    onNodeClick={(node) => console.log('Node clicked:', node)}
                  />
                )}
                {activeTab === 2 && report && <MoneyTrailTab report={report} />}
                {activeTab === 3 && report && <OsintTab report={report} />}
                {!report && (
                  <div className="empty-state">
                    <div className="spinner-dark" style={{ width: 24, height: 24 }} />
                    <div className="empty-state-title">Loading report…</div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </div>

      {/* ── Evidence Feed (below) ─────────────────────────────────────────── */}
      {report && (
        <div style={{ marginTop: '1.25rem' }}>
          <EvidenceFeed report={report} />
        </div>
      )}
    </div>
  )
}
