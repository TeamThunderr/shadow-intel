import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getWatchlist, addToWatchlist, removeFromWatchlist } from '../api/client'

export default function Watchlist() {
  const queryClient = useQueryClient()
  const [newName, setNewName] = useState('')

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

      {/* List */}
      {isLoading ? (
        <div style={{ textAlign: 'center', color: '#475569', padding: '3rem' }}>Loading watchlist…</div>
      ) : watchlist.length === 0 ? (
        <div className="glass-card" style={{ padding: '3rem', textAlign: 'center' }}>
          <div style={{ fontSize: '2rem', marginBottom: '0.75rem' }}>👁️</div>
          <div style={{ color: '#64748b', fontSize: '0.95rem' }}>No entities on watchlist yet.</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {watchlist.map((entry) => (
            <div key={entry.entity_id} className="glass-card" style={{ padding: '1rem 1.5rem', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: '0.95rem', marginBottom: '0.2rem' }}>{entry.entity_name}</div>
                <div style={{ fontSize: '0.78rem', color: '#475569', fontFamily: 'JetBrains Mono, monospace' }}>
                  ID: {entry.entity_id.slice(0, 8)}… | Threshold: {(entry.confidence_threshold * 100).toFixed(0)}%
                </div>
              </div>
              <button
                className="btn-ghost"
                style={{ color: '#f87171', borderColor: 'rgba(248,113,113,0.3)' }}
                onClick={() => removeMutation.mutate(entry.entity_id)}
              >
                Remove
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
