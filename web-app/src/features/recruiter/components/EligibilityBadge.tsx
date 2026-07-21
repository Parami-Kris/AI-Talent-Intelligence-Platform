export function EligibilityBadge({ isEligible }: { isEligible: boolean }) {
  return (
    <span
      className={
        'inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ' +
        (isEligible
          ? 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
          : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400')
      }
    >
      {isEligible ? 'Eligible' : 'Not eligible'}
    </span>
  )
}

export function ScoreBadge({ label, score }: { label: string; score: number | null | undefined }) {
  if (score === null || score === undefined) return null
  return (
    <span className="inline-flex items-center rounded-full bg-indigo-100 px-2 py-0.5 text-xs font-medium text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300">
      {label}: {score}
    </span>
  )
}

export function JobStabilityBadge({ flag }: { flag: string | null | undefined }) {
  if (flag !== 'frequent_job_changes') return null
  return (
    <span
      title="Multiple short stints (under 1 year) in this candidate's work history — worth a closer look, not an automatic disqualifier."
      className="inline-flex items-center rounded-full bg-orange-100 px-2 py-0.5 text-xs font-medium text-orange-800 dark:bg-orange-900/40 dark:text-orange-300"
    >
      Frequent job changes
    </span>
  )
}
