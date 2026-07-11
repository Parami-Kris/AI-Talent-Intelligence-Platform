import type { ReactNode } from 'react'
import type { CandidateSummary } from '../../../api/types'
import { ScoreRing } from '../../../components/ScoreRing'
import { SkillChips } from '../../../components/SkillChips'
import { EligibilityBadge } from './EligibilityBadge'

interface CandidateCardProps {
  row: CandidateSummary
  onClick?: (row: CandidateSummary) => void
  actions?: ReactNode
}

export function CandidateCard({ row, onClick, actions }: CandidateCardProps) {
  const score = row.final_score ?? row.overall_score

  return (
    <div
      onClick={() => onClick?.(row)}
      className={`flex flex-col gap-3 rounded-lg border border-gray-200 bg-white p-4 shadow-sm transition-shadow dark:border-gray-800 dark:bg-gray-900 ${
        onClick ? 'cursor-pointer hover:border-indigo-300 hover:shadow-md dark:hover:border-indigo-700' : ''
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate font-semibold">{row.candidate_name}</p>
          <div className="mt-1 flex flex-wrap items-center gap-1">
            <EligibilityBadge isEligible={row.is_eligible} />
            {row.manually_added ? (
              <span
                title={typeof row.override_reason === 'string' ? row.override_reason : undefined}
                className="inline-flex items-center rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-800 dark:bg-amber-900/40 dark:text-amber-300"
              >
                Manually added
              </span>
            ) : null}
          </div>
        </div>
        <ScoreRing score={score} />
      </div>

      {row.top_missing_must_haves && row.top_missing_must_haves.length > 0 && (
        <div>
          <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">Missing must-haves</p>
          <SkillChips items={row.top_missing_must_haves} tone="missing" limit={4} />
        </div>
      )}

      {row.experience_relevance_score !== null && row.experience_relevance_score !== undefined && (
        <p className="text-xs text-gray-600 dark:text-gray-400">
          LLM relevance: <span className="font-medium">{row.experience_relevance_score}</span>
          {row.domain_fit ? ` · ${row.domain_fit} domain fit` : ''}
        </p>
      )}

      {actions && (
        <div onClick={(event) => event.stopPropagation()} className="mt-1 flex justify-end">
          {actions}
        </div>
      )}
    </div>
  )
}
