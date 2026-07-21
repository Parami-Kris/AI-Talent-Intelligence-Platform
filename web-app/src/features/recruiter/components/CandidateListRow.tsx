import type { ReactNode } from 'react'
import type { CandidateSummary } from '../../../api/types'
import { ScoreRing } from '../../../components/ScoreRing'
import { EligibilityBadge, JobStabilityBadge } from './EligibilityBadge'

interface CandidateListRowProps {
  row: CandidateSummary
  selected: boolean
  onClick: () => void
  actions?: ReactNode
  compareChecked?: boolean
  onToggleCompare?: (row: CandidateSummary) => void
}

export function CandidateListRow({
  row,
  selected,
  onClick,
  actions,
  compareChecked,
  onToggleCompare,
}: CandidateListRowProps) {
  const score = row.final_score ?? row.overall_score

  return (
    <div
      onClick={onClick}
      className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 transition-colors ${
        selected
          ? 'border-indigo-400 bg-indigo-50 dark:border-indigo-600 dark:bg-indigo-950/30'
          : 'border-transparent hover:bg-gray-50 dark:hover:bg-gray-900'
      }`}
    >
      {onToggleCompare && (
        <input
          type="checkbox"
          checked={!!compareChecked}
          onChange={() => onToggleCompare(row)}
          onClick={(event) => event.stopPropagation()}
          title="Select for comparison"
          className="h-4 w-4 shrink-0 accent-indigo-600"
        />
      )}
      <ScoreRing score={score} size={36} strokeWidth={4} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{row.candidate_name}</p>
        <div className="mt-0.5 flex flex-wrap items-center gap-1">
          <EligibilityBadge isEligible={row.is_eligible} />
          <JobStabilityBadge flag={row.job_stability_flag} />
        </div>
      </div>
      {actions && (
        <div onClick={(event) => event.stopPropagation()} className="shrink-0">
          {actions}
        </div>
      )}
    </div>
  )
}
