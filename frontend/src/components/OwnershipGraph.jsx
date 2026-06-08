import { useEffect, useRef, useState } from 'react'
import * as d3 from 'd3'
import { Info, X } from 'lucide-react'

const OPACITY_JURISDICTIONS = ['PA', 'VG', 'KY', 'Panama', 'BVI', 'Cayman Islands']

export default function OwnershipGraph({ graph }) {
  const svgRef = useRef(null)
  const [selectedNode, setSelectedNode] = useState(null)

  useEffect(() => {
    if (!graph || !graph.nodes?.length) return

    const width = 500, height = 320
    const svg = d3.select(svgRef.current)
    svg.selectAll('*').remove()

    const g = svg.append('g')

    const simulation = d3.forceSimulation(graph.nodes)
      .force('link', d3.forceLink(graph.edges).id(d => d.id).distance(80))
      .force('charge', d3.forceManyBody().strength(-200))
      .force('center', d3.forceCenter(width / 2, height / 2))

    const link = g.append('g')
      .selectAll('line')
      .data(graph.edges)
      .join('line')
      .attr('stroke', 'rgba(99,102,241,0.4)')
      .attr('stroke-width', 1.5)
      .attr('marker-end', 'url(#arrow)')

    // Arrow marker
    svg.append('defs').append('marker')
      .attr('id', 'arrow')
      .attr('viewBox', '0 -5 10 10')
      .attr('refX', 20).attr('refY', 0)
      .attr('markerWidth', 6).attr('markerHeight', 6)
      .attr('orient', 'auto')
      .append('path')
      .attr('d', 'M0,-5L10,0L0,5')
      .attr('fill', 'rgba(99,102,241,0.6)')

    const node = g.append('g')
      .selectAll('g')
      .data(graph.nodes)
      .join('g')
      .call(d3.drag()
        .on('start', (event, d) => { if (!event.active) simulation.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y })
        .on('end', (event, d) => { if (!event.active) simulation.alphaTarget(0); d.fx = null; d.fy = null })
      )
      .on('click', (event, d) => {
        event.stopPropagation()
        setSelectedNode(d)
      })

    // Persons are circles
    node.filter(d => d.entity_type === 'person')
      .append('circle')
      .attr('r', 16)
      .attr('fill', 'rgba(236,72,153,0.25)')
      .attr('stroke', d => OPACITY_JURISDICTIONS.includes(d.jurisdiction) ? '#f59e0b' : '#ec4899')
      .attr('stroke-width', d => OPACITY_JURISDICTIONS.includes(d.jurisdiction) ? 3 : 1.5)

    // Companies are rects
    node.filter(d => d.entity_type !== 'person')
      .append('rect')
      .attr('x', -24).attr('y', -16)
      .attr('width', 48).attr('height', 32).attr('rx', 4)
      .attr('fill', 'rgba(99,102,241,0.25)')
      .attr('stroke', d => OPACITY_JURISDICTIONS.includes(d.jurisdiction) ? '#f59e0b' : '#6366f1')
      .attr('stroke-width', d => OPACITY_JURISDICTIONS.includes(d.jurisdiction) ? 3 : 1.5)

    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', d => d.entity_type === 'person' ? 28 : 32)
      .attr('fill', d => OPACITY_JURISDICTIONS.includes(d.jurisdiction) ? '#fbbf24' : '#94a3b8')
      .attr('font-size', 10)
      .attr('font-weight', d => OPACITY_JURISDICTIONS.includes(d.jurisdiction) ? 700 : 400)
      .text(d => (d.name || d.id || '').slice(0, 16))

    svg.on('click', () => setSelectedNode(null))

    simulation.on('tick', () => {
      link
        .attr('x1', d => d.source.x).attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x).attr('y2', d => d.target.y)
      node.attr('transform', d => `translate(${d.x},${d.y})`)
    })

    // Zoom
    svg.call(d3.zoom().scaleExtent([0.5, 3]).on('zoom', (e) => g.attr('transform', e.transform)))
  }, [graph])

  if (!graph?.nodes?.length) {
    return (
      <div style={{ height: 200, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#475569', fontSize: '0.875rem' }}>
        No ownership graph data yet
      </div>
    )
  }

  return (
    <div style={{ position: 'relative', width: '100%', height: 320 }}>
      <svg
        ref={svgRef}
        width="100%"
        height="100%"
        style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8, cursor: 'grab' }}
      />
      {selectedNode && (
        <div className="glass-card animate-fade-in" style={{
          position: 'absolute', top: 12, right: 12, width: 240, padding: '1rem',
          boxShadow: '0 10px 25px -5px rgba(0,0,0,0.5)', zIndex: 10
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.5rem' }}>
            <h4 style={{ fontWeight: 600, fontSize: '0.9rem', color: '#e2e8f0', lineHeight: 1.2 }}>
              {selectedNode.name || selectedNode.id}
            </h4>
            <button onClick={() => setSelectedNode(null)} style={{ background: 'none', border: 'none', color: '#64748b', cursor: 'pointer' }}>
              <X size={14} />
            </button>
          </div>
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem', fontSize: '0.75rem', color: '#cbd5e1' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#64748b' }}>Type</span>
              <span style={{ textTransform: 'capitalize' }}>{selectedNode.entity_type || 'Unknown'}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span style={{ color: '#64748b' }}>Jurisdiction</span>
              <span style={{ color: OPACITY_JURISDICTIONS.includes(selectedNode.jurisdiction) ? '#fbbf24' : '#cbd5e1', fontWeight: OPACITY_JURISDICTIONS.includes(selectedNode.jurisdiction) ? 700 : 400 }}>
                {selectedNode.jurisdiction || 'N/A'}
                {OPACITY_JURISDICTIONS.includes(selectedNode.jurisdiction) && ' ⚠️'}
              </span>
            </div>
            {selectedNode.ownership_pct && (
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <span style={{ color: '#64748b' }}>Ownership</span>
                <span>{(selectedNode.ownership_pct * 100).toFixed(1)}%</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
