import { useEffect, useRef } from 'react'
import * as d3 from 'd3'

export default function OwnershipGraph({ graph }) {
  const svgRef = useRef(null)

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

    node.append('circle')
      .attr('r', 14)
      .attr('fill', d => d.entity_type === 'person' ? 'rgba(236,72,153,0.25)' : 'rgba(99,102,241,0.25)')
      .attr('stroke', d => d.entity_type === 'person' ? '#ec4899' : '#6366f1')
      .attr('stroke-width', 1.5)

    node.append('text')
      .attr('text-anchor', 'middle')
      .attr('dy', 28)
      .attr('fill', '#94a3b8')
      .attr('font-size', 10)
      .text(d => (d.name || d.id || '').slice(0, 16))

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
    <svg
      ref={svgRef}
      width="100%"
      height={320}
      style={{ background: 'rgba(0,0,0,0.2)', borderRadius: 8 }}
    />
  )
}
