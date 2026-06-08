import { useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

const MODULE_COLORS = {
  ghost_tracker: '#3b82f6',
  money_trail: '#8b5cf6',
  ownership_unwind: '#6366f1',
  dark_signal: '#ec4899',
  resurface_engine: '#f59e0b',
}

const MODULE_ICONS = {
  ghost_tracker: '👻',
  money_trail: '💸',
  ownership_unwind: '🕸️',
  dark_signal: '📡',
  resurface_engine: '🔔',
}

export default function EvidenceFeed({ chain = [] }) {
  const containerRef = useRef(null)

  useEffect(() => {
    // If newest first is at top, we don't strictly need to scroll to bottom,
    // but just in case, we can ensure the top is visible.
    if (containerRef.current) {
      containerRef.current.scrollTop = 0
    }
  }, [chain])

  if (!chain.length) {
    return (
      <div style={{ color: '#475569', fontSize: '0.875rem', textAlign: 'center', padding: '2rem 0' }}>
        No evidence collected yet
      </div>
    )
  }

  // Sort newest first (highest step number)
  const sortedChain = [...chain].sort((a, b) => b.step - a.step)

  return (
    <div ref={containerRef} style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', maxHeight: 360, overflowY: 'auto', paddingRight: '0.5rem' }}>
      <AnimatePresence initial={false}>
        {sortedChain.map((step) => {
          const color = MODULE_COLORS[step.source_module] || '#64748b'
          const icon = MODULE_ICONS[step.source_module] || '📋'

          return (
            <motion.div
              key={step.step}
              initial={{ opacity: 0, y: -20, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.3, ease: 'easeOut' }}
              style={{
                padding: '0.875rem 1rem',
                background: 'rgba(0,0,0,0.25)',
                borderRadius: 8,
                borderLeft: `3px solid ${color}`,
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.85rem' }}>{icon}</span>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
                  Step {step.step} — {step.source_module.replace('_', ' ')}
                </span>
                <span style={{ marginLeft: 'auto', fontSize: '0.72rem', color: '#475569' }}>
                  {(step.confidence * 100).toFixed(0)}% confidence
                </span>
              </div>
              <div style={{ fontSize: '0.85rem', color: '#cbd5e1', marginBottom: '0.3rem', lineHeight: 1.5 }}>
                {step.finding}
              </div>
              <div style={{ fontSize: '0.72rem', color: '#475569' }}>
                Sources: {step.sources?.join(', ') || '—'}
              </div>
            </motion.div>
          )
        })}
      </AnimatePresence>
    </div>
  )
}
