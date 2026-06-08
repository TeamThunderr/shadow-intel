import { motion } from 'framer-motion'

const getRiskInfo = (value) => {
  const pct = value * 100
  if (pct <= 40) return { level: 'Low', color: '#34d399' }
  if (pct <= 70) return { level: 'Medium', color: '#60a5fa' }
  if (pct <= 85) return { level: 'High', color: '#fbbf24' }
  return { level: 'Critical', color: '#f87171' }
}

/**
 * ConfidenceMeter — circular arc gauge showing unified confidence score.
 * Uses SVG arc path for crisp rendering at any size.
 */
export default function ConfidenceMeter({ value = 0, size = 72 }) {
  const radius = 28
  const cx = size / 2
  const cy = size / 2
  const circumference = 2 * Math.PI * radius
  const arc = circumference * Math.min(1, Math.max(0, value))
  const { level, color } = getRiskInfo(value)

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
      <div style={{ position: 'relative', width: size, height: size }}>
        <svg width={size} height={size} style={{ transform: 'rotate(-90deg)', position: 'absolute', top: 0, left: 0 }}>
          {/* Background track */}
          <circle
            cx={cx} cy={cy} r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.07)"
            strokeWidth={5}
          />
          {/* Filled arc */}
          <motion.circle
            cx={cx} cy={cy} r={radius}
            fill="none"
            stroke={color}
            strokeWidth={5}
            strokeLinecap="round"
            initial={{ strokeDasharray: `0 ${circumference}` }}
            animate={{ strokeDasharray: `${arc} ${circumference}` }}
            transition={{ duration: 1, ease: "easeOut" }}
            style={{ filter: `drop-shadow(0 0 6px ${color}70)` }}
          />
        </svg>
      </div>
      <div>
        <div style={{ fontSize: '1.4rem', fontWeight: 800, color, lineHeight: 1, fontVariantNumeric: 'tabular-nums', display: 'flex', alignItems: 'baseline', gap: '4px' }}>
          {(value * 100).toFixed(0)}<span style={{ fontSize: '0.85rem' }}>%</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '2px' }}>
          <span style={{ fontSize: '0.7rem', color: '#475569', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Risk:
          </span>
          <span style={{ fontSize: '0.75rem', fontWeight: 700, color }}>
            {level}
          </span>
        </div>
      </div>
    </div>
  )
}
