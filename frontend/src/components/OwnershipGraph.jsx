import React, { useEffect, useRef } from 'react'
import * as d3 from 'd3'
import { Building2, User, HelpCircle, Expand } from 'lucide-react'

// Map entity types to SVG icons manually for D3 usage
const typeToIcon = {
  company: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="4" y="2" width="16" height="20" rx="2" ry="2"></rect><path d="M9 22v-4h6v4"></path><path d="M8 6h.01"></path><path d="M16 6h.01"></path><path d="M12 6h.01"></path><path d="M12 10h.01"></path><path d="M12 14h.01"></path><path d="M16 10h.01"></path><path d="M16 14h.01"></path><path d="M8 10h.01"></path><path d="M8 14h.01"></path></svg>`,
  person:  `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>`,
  unknown: `<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>`
}

export default function OwnershipGraph({ graphData, onNodeClick }) {
  const containerRef = useRef(null)

  useEffect(() => {
    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) return
    if (!containerRef.current) return

    const width = containerRef.current.clientWidth
    const height = 500

    // Clear previous
    d3.select(containerRef.current).selectAll('*').remove()

    const svg = d3.select(containerRef.current)
      .append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('background', 'var(--bg-canvas)')
      .style('border-radius', 'var(--radius-md)')
      .style('cursor', 'grab')
      
    // Defs for gradients/markers
    const defs = svg.append('defs')
    
    // Drop shadow
    const filter = defs.append('filter')
      .attr('id', 'drop-shadow')
      .attr('x', '-20%').attr('y', '-20%').attr('width', '140%').attr('height', '140%')
    filter.append('feDropShadow')
      .attr('dx', '0').attr('dy', '2').attr('stdDeviation', '4')
      .attr('flood-color', '#0f1221').attr('flood-opacity', '0.08')

    // Arrow marker
    defs.append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 24)
      .attr('refY', 0)
      .attr('markerWidth', 5)
      .attr('markerHeight', 5)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'var(--border-bright)')

    const g = svg.append('g')

    // Zoom
    const zoom = d3.zoom()
      .scaleExtent([0.3, 3])
      .on('zoom', (event) => g.attr('transform', event.transform))
    svg.call(zoom)

    // Data setup
    const nodes = graphData.nodes.map(d => ({ ...d }))
    const links = graphData.edges.map(d => ({
      source: d.from,
      target: d.to,
      pct: d.ownership_percentage
    }))

    // Simulation
    const simulation = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(100))
      .force('charge', d3.forceManyBody().strength(-400))
      .force('center', d3.forceCenter(width / 2, height / 2))
      .force('collide', d3.forceCollide().radius(40))

    // Edges
    const edgeGroup = g.append('g').attr('class', 'links')
    const edge = edgeGroup.selectAll('.link')
      .data(links)
      .enter().append('g')
      .attr('class', 'link')

    edge.append('line')
      .attr('stroke', 'var(--border-bright)')
      .attr('stroke-width', d => Math.max(1.5, (d.pct || 0) / 25))
      .attr('marker-end', 'url(#arrow)')

    edge.append('text')
      .text(d => d.pct > 0 ? `${d.pct}%` : '')
      .attr('fill', 'var(--text-muted)')
      .attr('font-size', '10px')
      .attr('font-weight', '600')
      .attr('text-anchor', 'middle')
      .attr('dy', -4)
      .style('pointer-events', 'none')

    // Nodes
    const nodeGroup = g.append('g').attr('class', 'nodes')
    const node = nodeGroup.selectAll('.node')
      .data(nodes)
      .enter().append('g')
      .attr('class', 'node')
      .style('cursor', 'pointer')
      .call(d3.drag()
        .on('start', dragstarted)
        .on('drag', dragged)
        .on('end', dragended))
      .on('click', (event, d) => onNodeClick && onNodeClick(d))

    // Node circles
    node.append('circle')
      .attr('r', 18)
      .attr('fill', 'var(--bg-card)')
      .attr('stroke', 'var(--accent-blue)')
      .attr('stroke-width', 2)
      .attr('filter', 'url(#drop-shadow)')

    // Node icons (HTML within SVG)
    node.append('foreignObject')
      .attr('x', -8)
      .attr('y', -8)
      .attr('width', 16)
      .attr('height', 16)
      .html(d => `<div style="color:var(--accent-blue); display:flex;">${typeToIcon[d.type] || typeToIcon.unknown}</div>`)

    // Node labels
    node.append('text')
      .text(d => d.name)
      .attr('dy', 30)
      .attr('text-anchor', 'middle')
      .attr('font-size', '11px')
      .attr('font-weight', '600')
      .attr('fill', 'var(--text-primary)')
      .style('pointer-events', 'none')

    // Node subtitle
    node.append('text')
      .text(d => d.source_system || '')
      .attr('dy', 42)
      .attr('text-anchor', 'middle')
      .attr('font-size', '9px')
      .attr('fill', 'var(--text-muted)')
      .style('pointer-events', 'none')

    // Tick
    simulation.on('tick', () => {
      edge.selectAll('line')
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)
        
      edge.selectAll('text')
        .attr('x', d => (d.source.x + d.target.x) / 2)
        .attr('y', d => (d.source.y + d.target.y) / 2)

      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    // Drag handlers
    function dragstarted(event, d) {
      if (!event.active) simulation.alphaTarget(0.3).restart()
      d.fx = d.x
      d.fy = d.y
      d3.select(this).select('circle').attr('stroke', 'var(--accent-purple)').attr('stroke-width', 3)
    }
    
    function dragged(event, d) {
      d.fx = event.x
      d.fy = event.y
    }
    
    function dragended(event, d) {
      if (!event.active) simulation.alphaTarget(0)
      d.fx = null
      d.fy = null
      d3.select(this).select('circle').attr('stroke', 'var(--accent-blue)').attr('stroke-width', 2)
    }

    return () => simulation.stop()
  }, [graphData])

  if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
    return (
      <div className="empty-state" style={{ minHeight: 400 }}>
        <div className="empty-state-icon"><Expand size={24} /></div>
        <div className="empty-state-title">No Ownership Data</div>
        <div className="empty-state-desc">Could not generate a corporate graph for this entity.</div>
      </div>
    )
  }

  return (
    <div style={{ position: 'relative' }}>
      <div ref={containerRef} style={{ width: '100%', height: 500 }} />
      <div style={{
        position: 'absolute', top: 12, right: 12,
        background: 'var(--bg-card)', padding: '6px 12px',
        borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)',
        boxShadow: 'var(--shadow-sm)',
        fontSize: '0.7rem', color: 'var(--text-muted)',
        display: 'flex', flexDirection: 'column', gap: 4
      }}>
        <div style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>Legend</div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--accent-blue)' }} /> Target / Nodes
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div style={{ width: 12, height: 2, background: 'var(--border-bright)' }} /> Ownership Link
        </div>
      </div>
    </div>
  )
}
