import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'

const RISK_COLORS = {
  clean: 'var(--color-risk-clean)',
  placement: 'var(--color-risk-placement)',
  layering: 'var(--color-risk-layering)',
  integration: 'var(--color-risk-integration)',
}

/**
 * FinancialFlowGraph — Sankey-style flow diagram for money trail data.
 * Renders transaction hops as a directed flow chart using D3.
 */
export default function FinancialFlowGraph({ flows }) {
  const svgRef = useRef(null)
  const containerRef = useRef(null)
  const [tooltip, setTooltip] = useState(null)

  useEffect(() => {
    if (!flows || !flows.nodes?.length) return

    const width = 500, height = 300
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    // Add arrow markers for each risk color
    const defs = svg.append('defs')
    Object.entries(RISK_COLORS).forEach(([risk, color]) => {
      defs.append('marker')
        .attr('id', `arrow-${risk}`)
        .attr('viewBox', '0 -5 10 10')
        .attr('refX', 22)
        .attr('refY', 0)
        .attr('markerWidth', 6)
        .attr('markerHeight', 6)
        .attr('orient', 'auto')
        .append('path')
        .attr('d', 'M0,-5L10,0L0,5')
        .attr('fill', color)
    })

    // Default arrow marker for unknown/none
    defs.append('marker')
      .attr('id', 'arrow-default')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 22)
      .attr('refY', 0)
      .attr('markerWidth', 6)
      .attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'rgba(148,163,184,0.6)')

    const g = svg.append('g').attr('transform', 'translate(20,20)')

    const simulation = d3.forceSimulation(flows.nodes)
      .force('link', d3.forceLink(flows.edges).id(d => d.id).distance(120))
      .force('charge', d3.forceManyBody().strength(-300))
      .force('center', d3.forceCenter((width - 40) / 2, (height - 40) / 2))

    const link = g.append('g')
      .selectAll('path')
      .data(flows.edges)
      .join('path')
      .attr('fill', 'none')
      .attr('stroke', d => RISK_COLORS[d.risk_flag] || 'rgba(148,163,184,0.35)')
      .attr('stroke-width', d => {
        const baseWidth = Math.max(1.5, Math.min(8, (d.amount || 1) / 1e5))
        return d.risk_flag && d.risk_flag !== 'clean' ? baseWidth * 1.5 : baseWidth
      })
      .attr('marker-end', d => `url(#arrow-${d.risk_flag || 'default'})`)
      .style('cursor', 'pointer')
      .on('mouseenter', (event, d) => {
        d3.select(event.currentTarget).attr('stroke-opacity', 1).attr('filter', 'drop-shadow(0 0 4px rgba(255,255,255,0.4))')
        
        // Find source and target names safely (D3 link source/target objects)
        const sourceName = typeof d.source === 'object' ? (d.source.label || d.source.id) : d.source
        const targetName = typeof d.target === 'object' ? (d.target.label || d.target.id) : d.target
        
        setTooltip({
          x: event.clientX,
          y: event.clientY,
          data: {
            title: 'Transaction Details',
            rows: [
              { label: 'From', value: sourceName },
              { label: 'To', value: targetName },
              { label: 'Amount', value: `$${Number(d.amount).toLocaleString()}` },
              { label: 'Jurisdiction', value: d.jurisdiction || 'N/A' },
              { label: 'Risk Flag', value: d.risk_flag ? d.risk_flag.toUpperCase() : 'NONE' },
            ]
          }
        })
      })
      .on('mouseleave', (event) => {
        d3.select(event.currentTarget).attr('stroke-opacity', 0.8).attr('filter', null)
        setTooltip(null)
      })

    const node = g.append('g')
      .selectAll('rect')
      .data(flows.nodes)
      .join('rect')
      .attr('width', 80).attr('height', 28).attr('rx', 5)
      .attr('fill', d => d.type === 'wallet' ? 'rgba(139,92,246,0.3)' : 'rgba(59,130,246,0.3)')
      .attr('stroke', d => d.type === 'wallet' ? '#8b5cf6' : '#3b82f6')
      .attr('stroke-width', 1.5)
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
      )

    const label = g.append('g')
      .selectAll('text')
      .data(flows.nodes)
      .join('text')
      .attr('fill', '#e2e8f0')
      .attr('font-size', 9)
      .attr('font-weight', 600)
      .attr('text-anchor', 'middle')
      .style('pointer-events', 'none')
      .text(d => (d.label || d.id || '').slice(0, 14))

    simulation.on('tick', () => {
      // Adjusted path calculation to end at the edge of the rect node (approx 40px left/right, 14px up/down)
      link.attr('d', d => {
        const dx = d.target.x - d.source.x
        const dy = d.target.y - d.source.y
        const dr = Math.sqrt(dx * dx + dy * dy) * 1.5 // gentle curve
        return `M${d.source.x},${d.source.y} A${dr},${dr} 0 0,1 ${d.target.x},${d.target.y}`
      })
      node.attr('x', d => d.x - 40).attr('y', d => d.y - 14)
      label.attr('x', d => d.x).attr('y', d => d.y + 3)
    })
    
    // Zoom
    svg.call(d3.zoom().scaleExtent([0.5, 3]).on('zoom', (e) => g.attr('transform', e.transform)))
  }, [flows])

  if (!flows?.nodes?.length) {
    return (
      <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: '0.875rem' }}>
        No financial flow data yet
      </div>
    )
  }

  return (
    <div ref={containerRef} style={{ position: 'relative', width: '100%', height: 300 }}>
      <svg ref={svgRef} width="100%" height="100%" style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, cursor: 'grab' }} />
      
      {/* Tooltip */}
      {tooltip && (
        <div 
          className="d3-tooltip" 
          style={{ 
            opacity: 1, 
            left: tooltip.x - (containerRef.current?.getBoundingClientRect().left || 0) + 15,
            top: tooltip.y - (containerRef.current?.getBoundingClientRect().top || 0) + 15,
            minWidth: 200
          }}
        >
          <div className="d3-tooltip-title">{tooltip.data.title}</div>
          {tooltip.data.rows.map((r, i) => (
            <div key={i} className="d3-tooltip-row">
              <span className="d3-tooltip-label">{r.label}</span>
              <span className="d3-tooltip-value" style={{ 
                color: r.label === 'Risk Flag' && r.value !== 'NONE' ? RISK_COLORS[r.value.toLowerCase()] || '#cbd5e1' : '#cbd5e1' 
              }}>
                {r.value}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
