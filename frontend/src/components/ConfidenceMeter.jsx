/**
 * ConfidenceMeter — circular arc gauge showing unified confidence score.
 * Uses SVG arc path for crisp rendering at any size.
 */
export default function ConfidenceMeter({ value = 0, color = '#3b82f6', size = 72 }) {
  const radius = 28
  const cx = size / 2
  const cy = size / 2
  const circumference = 2 * Math.PI * radius
  const arc = circumference * Math.min(1, Math.max(0, value))

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <svg width={size} height={size} style={{ transform: 'rotate(-90deg)' }}>
        {/* Background track */}
        <circle
          cx={cx} cy={cy} r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.07)"
          strokeWidth={5}
        />
        {/* Filled arc */}
        <circle
          cx={cx} cy={cy} r={radius}
          fill="none"
          stroke={color}
          strokeWidth={5}
          strokeDasharray={`${arc} ${circumference}`}
          strokeLinecap="round"
          style={{ transition: 'stroke-dasharray 0.8s cubic-bezier(0.4, 0, 0.2, 1)', filter: `drop-shadow(0 0 6px ${color}70)` }}
        />
      </svg>
      <div>
        <div style={{ fontSize: '1.3rem', fontWeight: 800, color, lineHeight: 1, fontVariantNumeric: 'tabular-nums' }}>
          {(value * 100).toFixed(0)}%
        </div>
        <div style={{ fontSize: '0.68rem', color: '#475569', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
          Confidence
        </div>
      </div>
    </div>
  )
}
