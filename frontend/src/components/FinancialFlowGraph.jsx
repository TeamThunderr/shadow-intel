import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

/**
 * FinancialFlowGraph — Sankey-style flow diagram for money trail data.
 * Renders transaction hops as a directed flow chart using D3.
 */
export default function FinancialFlowGraph({ flows }) {
  const svgRef = useRef(null)

  useEffect(() => {
    if (!flows || !flows.nodes?.length) return

    const width = 500, height = 300
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const g = svg.append('g').attr('transform', 'translate(20,20)')

    const simulation = d3.forceSimulation(flows.nodes)
      .force('link', d3.forceLink(flows.edges).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-250))
      .force('center', d3.forceCenter((width - 40) / 2, (height - 40) / 2))

    const link = g.append('g')
      .selectAll('path')
      .data(flows.edges)
      .join('path')
      .attr('fill', 'none')
      .attr('stroke', d => d.suspicious ? 'rgba(248,113,113,0.5)' : 'rgba(59,130,246,0.35)')
      .attr('stroke-width', d => Math.max(1, Math.min(6, (d.amount || 1) / 1e5)))

    const node = g.append('g')
      .selectAll('rect')
      .data(flows.nodes)
      .join('rect')
      .attr('width', 80).attr('height', 28).attr('rx', 5)
      .attr('fill', d => d.type === 'wallet' ? 'rgba(139,92,246,0.3)' : 'rgba(59,130,246,0.3)')
      .attr('stroke', d => d.type === 'wallet' ? '#8b5cf6' : '#3b82f6')
      .attr('stroke-width', 1)

    const label = g.append('g')
      .selectAll('text')
      .data(flows.nodes)
      .join('text')
      .attr('fill', '#94a3b8')
      .attr('font-size', 9)
      .attr('text-anchor', 'middle')
      .text(d => (d.label || d.id || '').slice(0, 14))

    simulation.on('tick', () => {
      link.attr('d', d =>
        `M${d.source.x},${d.source.y} C${(d.source.x + d.target.x) / 2},${d.source.y} ${(d.source.x + d.target.x) / 2},${d.target.y} ${d.target.x},${d.target.y}`
      )
      node.attr('x', d => d.x - 40).attr('y', d => d.y - 14)
      label.attr('x', d => d.x).attr('y', d => d.y + 4)
    })
  }, [flows])

  if (!flows?.nodes?.length) {
    return (
      <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: '0.875rem' }}>
        No financial flow data yet
      </div>
    )
  }

  return (
    <svg ref={svgRef} width="100%" height={300} style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8 }} />
  )
}
