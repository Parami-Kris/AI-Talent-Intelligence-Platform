interface ScoreRingProps {
  score: number | null | undefined
  size?: number
  strokeWidth?: number
}

export function ScoreRing({ score, size = 56, strokeWidth = 5 }: ScoreRingProps) {
  const hasScore = score !== null && score !== undefined
  const clamped = Math.max(0, Math.min(100, hasScore ? score : 0))
  const radius = (size - strokeWidth) / 2
  const circumference = 2 * Math.PI * radius
  const offset = circumference - (clamped / 100) * circumference

  const colorClass = !hasScore
    ? 'text-gray-300 dark:text-gray-700'
    : clamped >= 70
      ? 'text-green-500 dark:text-green-400'
      : clamped >= 40
        ? 'text-amber-500 dark:text-amber-400'
        : 'text-red-500 dark:text-red-400'

  return (
    <div className="relative inline-flex shrink-0 items-center justify-center" style={{ width: size, height: size }}>
      <svg width={size} height={size} className="-rotate-90">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
          stroke="currentColor"
          className="text-gray-200 dark:text-gray-800"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          strokeWidth={strokeWidth}
          fill="none"
          stroke="currentColor"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          className={`${colorClass} transition-[stroke-dashoffset] duration-500`}
        />
      </svg>
      <span className="absolute text-xs font-semibold">{hasScore ? Math.round(clamped) : '—'}</span>
    </div>
  )
}
