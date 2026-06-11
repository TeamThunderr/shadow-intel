import { useState, useEffect } from 'react'
import { motion, useSpring, useTransform } from 'framer-motion'

const getRiskInfo = (value) => {
  const pct = value * 100
  if (pct <= 25) return { level: 'LOW',      color: 'var(--risk-low)' }
  if (pct <= 55) return { level: 'MEDIUM',   color: 'var(--risk-medium)' }
  if (pct <= 80) return { level: 'HIGH',     color: 'var(--risk-high)' }
  return             { level: 'CRITICAL', color: 'var(--risk-critical)' }
}

/**
 * ConfidenceMeter — animated circular SVG gauge with count-up number.
 * The arc fills from 0 → value on mount. Number counts up.
 */
export default function ConfidenceMeter({ value = 0, size = 60, sourceCount }) {
  const [displayed, setDisplayed] = useState(0)
  const radius      = (size / 2) - 6
  const cx          = size / 2
  const cy          = size / 2
  const circumference = 2 * Math.PI * radius
  const arc         = circumference * Math.min(1, Math.max(0, value))
  const { level, color } = getRiskInfo(value)

  // Count-up animation
  useEffect(() => {
    if (value === 0) { setDisplayed(0); return }
    let start = 0
    const target = Math.round(value * 100)
    const step   = target / 35
    const id     = setInterval(() => {
      start += step
      if (start >= target) { setDisplayed(target); clearInterval(id) }
      else setDisplayed(Math.round(start))
    }, 20)
    return () => clearInterval(id)
  }, [value])

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <div style={{ position: 'relative', width: size, height: size, flexShrink: 0 }}>
        <svg
          width={size} height={size}
          style={{ transform: 'rotate(-90deg)', position: 'absolute', top: 0, left: 0 }}
        >
          {/* Track */}
          <circle cx={cx} cy={cy} r={radius} fill="none" stroke="var(--border)" strokeWidth={4} />
          {/* Filled arc */}
          <motion.circle
            cx={cx} cy={cy} r={radius}
            fill="none"
            stroke={color}
            strokeWidth={4}
            strokeLinecap="round"
            initial={{ strokeDasharray: `0 ${circumference}` }}
            animate={{ strokeDasharray: `${arc} ${circumference}` }}
            transition={{ duration: 1.1, ease: 'easeOut' }}
            style={{ filter: `drop-shadow(0 0 5px ${color}90)` }}
          />
        </svg>
        {/* Center percentage */}
        <div style={{
          position: 'absolute', inset: 0,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: size > 56 ? '0.9rem' : '0.72rem',
          fontWeight: 800, color, fontFamily: 'var(--font-mono)',
          letterSpacing: '-0.03em',
        }}>
          {displayed}
        </div>
      </div>

      {/* Text labels */}
      <div>
        <div style={{
          fontSize: '0.62rem', color: 'var(--text-muted)',
          textTransform: 'uppercase', letterSpacing: '0.07em', fontWeight: 600,
        }}>Risk</div>
        <div style={{ fontSize: '0.82rem', fontWeight: 800, color }}>{level}</div>
        {sourceCount !== undefined && (
          <div style={{ fontSize: '0.62rem', color: 'var(--text-muted)', marginTop: 1 }}>
            {sourceCount} sources
          </div>
        )}
      </div>
    </div>
  )
}
