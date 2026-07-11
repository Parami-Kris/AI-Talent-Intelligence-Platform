interface SkillChipsProps {
  items: string[]
  tone: 'matched' | 'missing'
  limit?: number
}

export function SkillChips({ items, tone, limit = 6 }: SkillChipsProps) {
  if (!items || items.length === 0) return null

  const shown = items.slice(0, limit)
  const remaining = items.length - shown.length
  const toneClass =
    tone === 'matched'
      ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
      : 'bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300'

  return (
    <div className="flex flex-wrap gap-1">
      {shown.map((item) => (
        <span
          key={item}
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${toneClass}`}
        >
          {item}
        </span>
      ))}
      {remaining > 0 && (
        <span className="inline-flex items-center rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-600 dark:bg-gray-800 dark:text-gray-400">
          +{remaining} more
        </span>
      )}
    </div>
  )
}
