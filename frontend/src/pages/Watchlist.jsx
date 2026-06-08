import { useState, useMemo } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '../api/client'
import { Search, ArrowUpDown, Trash2, Activity } from 'lucide-react'

export default function Watchlist() {
  const queryClient = useQueryClient()
  const [newName, setNewName] = useState('')
  const [searchQuery, setSearchQuery] = useState('')
  const [sortField, setSortField] = useState('entity_name')
  const [sortDir, setSortDir] = useState('asc')

  const { data: watchlist = [], isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => getWatchlist().then(r => r.data),
  })

  const addMutation = useMutation({
    mutationFn: (name) => addToWatchlist({ name, entity_type: 'unknown', confidence_threshold: 0.8 }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['watchlist'] })
      setNewName('')
    },
  })

  const removeMutation = useMutation({
    mutationFn: (entityId) => removeFromWatchlist(entityId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['watchlist'] }),
  })

  const filteredAndSortedWatchlist = useMemo(() => {
    let result = [...watchlist]
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      result = result.filter(w => w.entity_name.toLowerCase().includes(q))
    }
    result.sort((a, b) => {
      let aVal = a[sortField]
      let bVal = b[sortField]
      if (typeof aVal === 'string') aVal = aVal.toLowerCase()
      if (typeof bVal === 'string') bVal = bVal.toLowerCase()
      if (aVal < bVal) return sortDir === 'asc' ? -1 : 1
      if (aVal > bVal) return sortDir === 'asc' ? 1 : -1
      return 0
    })
    return result
  }, [watchlist, searchQuery, sortField, sortDir])

  const handleSort = (field) => {
    if (sortField === field) setSortDir(prev => prev === 'asc' ? 'desc' : 'asc')
    else { setSortField(field); setSortDir('asc') }
  }

  return (
    <div style={{ maxWidth: 900, margin: '0 auto', padding: '2rem' }}>
      <div style={{ marginBottom: '2rem' }}>
        <h1 style={{ fontSize: '1.6rem', fontWeight: 700, letterSpacing: '-0.02em', marginBottom: '0.5rem' }}>
          Watchlist
        </h1>
        <p style={{ color: '#64748b', fontSize: '0.9rem' }}>
          Entities monitored for resurface events. The Resurface Engine polls these every hour.
        </p>
      </div>

      {/* Add entity */}
      <div className="glass-card" style={{ padding: '1.25rem 1.5rem', marginBottom: '1.5rem', display: 'flex', gap: '1rem' }}>
        <input
          className="input-field"
          placeholder="Entity name to watch…"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && newName.trim() && addMutation.mutate(newName.trim())}
          style={{ flex: 1 }}
        />
        <button
          className="btn-primary"
          disabled={!newName.trim() || addMutation.isPending}
          onClick={() => addMutation.mutate(newName.trim())}
        >
          {addMutation.isPending ? 'Adding…' : '+ Add to Watchlist'}
        </button>
      </div>

      {/* Controls */}
      <div style={{ display: 'flex', gap: '1rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
        <div className="glass-card" style={{ padding: '0.75rem 1rem', display: 'flex', gap: '1rem', flex: 1, minWidth: 300 }}>
          <Search size={18} color="#64748b" style={{ marginTop: 2 }} />
          <input
            placeholder="Search watchlist…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ background: 'transparent', border: 'none', color: '#e2e8f0', outline: 'none', width: '100%' }}
          />
        </div>
      </div>

      {/* List */}
      {isLoading ? (
        <div style={{ textAlign: 'center', color: '#475569', padding: '3rem' }}>Loading watchlist…</div>
      ) : watchlist.length === 0 ? (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>👁️</div>
          <div style={{ color: '#64748b', fontSize: '0.95rem' }}>No entities on watchlist yet.</div>
        </div>
      ) : (
        <div className="glass-card" style={{ overflow: 'hidden' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: '1rem', padding: '1rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.05)', background: 'rgba(0,0,0,0.2)' }}>
            {['entity_name', 'last_alert', 'confidence_threshold', 'status'].map(field => {
              const labels = { entity_name: 'Entity', last_alert: 'Last Alert', confidence_threshold: 'Confidence', status: 'Monitoring Status' }
              return (
                <div key={field} onClick={() => handleSort(field)} style={{ fontSize: '0.75rem', fontWeight: 700, color: '#94a3b8', textTransform: 'uppercase', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4 }}>
                  {labels[field]} <ArrowUpDown size={12} opacity={sortField === field ? 1 : 0.3} />
                </div>
              )
            })}
            <div />
          </div>
          
          {filteredAndSortedWatchlist.map((entry) => (
            <div key={entry.entity_id} style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr 1fr auto', gap: '1rem', padding: '1rem 1.5rem', borderBottom: '1px solid rgba(255,255,255,0.02)', alignItems: 'center' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.95rem', color: '#e2e8f0' }}>{entry.entity_name}</div>
                <div style={{ fontSize: '0.75rem', color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>ID: {entry.entity_id.slice(0, 8)}</div>
              </div>
              <div style={{ fontSize: '0.85rem', color: '#cbd5e1' }}>
                {entry.last_alert ? new Date(entry.last_alert).toLocaleDateString() : '—'}
              </div>
              <div style={{ fontSize: '0.85rem', color: '#60a5fa', fontWeight: 600 }}>
                {(entry.confidence_threshold * 100).toFixed(0)}%
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.85rem', color: '#10b981' }}>
                <Activity size={14} className="animate-pulse" /> Active
              </div>
              <button
                className="btn-ghost"
                style={{ padding: '6px' }}
                onClick={() => removeMutation.mutate(entry.entity_id)}
                title="Remove from watchlist"
              >
                <Trash2 size={16} color="#ef4444" opacity={0.8} />
              </button>
            </div>
          ))}
          {filteredAndSortedWatchlist.length === 0 && (
            <div style={{ padding: '2rem', textAlign: 'center', color: '#64748b' }}>No matching entities found.</div>
          )}
        </div>
      )}
    </div>
  )
}
