import type { ReactNode } from 'react'
import type { CandidateResult, CandidateSummary } from '../../../api/types'
import { ScoreRing } from '../../../components/ScoreRing'
import { useEscapeKey } from '../../../lib/useEscapeKey'
import { joinCandidateDetail } from '../lib/joinCandidateDetail'
import { EligibilityBadge, JobStabilityBadge } from './EligibilityBadge'

interface CandidateComparisonPanelProps {
  rows: CandidateSummary[]
  fullResults: CandidateResult[]
  onClose: () => void
  onRemove: (candidateName: string) => void
}

function RowLabel({ children }: { children: ReactNode }) {
  return (
    <th className="sticky left-0 whitespace-nowrap bg-white px-3 py-2 text-left text-xs font-medium text-gray-500 dark:bg-gray-900 dark:text-gray-400">
      {children}
    </th>
  )
}

function Cell({ children }: { children: ReactNode }) {
  return <td className="min-w-[220px] px-3 py-2 align-top text-xs text-gray-700 dark:text-gray-300">{children}</td>
}

export function CandidateComparisonPanel({ rows, fullResults, onClose, onRemove }: CandidateComparisonPanelProps) {
  useEscapeKey(onClose)

  return (
    <div
      className="fixed inset-0 z-30 flex items-start justify-center overflow-y-auto bg-black/40 p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="mt-8 mb-8 w-full max-w-6xl rounded-lg bg-white p-6 shadow-xl dark:bg-gray-900"
        onClick={(event) => event.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="compare-modal-title"
      >
        <div className="mb-4 flex items-center justify-between">
          <h3 id="compare-modal-title" className="text-lg font-semibold">
            Compare candidates ({rows.length})
          </h3>
          <button
            type="button"
            onClick={onClose}
            className="text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
          >
            Close
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead>
              <tr>
                <RowLabel> </RowLabel>
                {rows.map((row) => (
                  <th key={row.candidate_name} className="min-w-[220px] px-3 py-2 align-top">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate font-semibold">{row.candidate_name}</p>
                        <div className="mt-1 flex flex-wrap gap-1">
                          <EligibilityBadge isEligible={row.is_eligible} />
                          <JobStabilityBadge flag={row.job_stability_flag} />
                        </div>
                      </div>
                      <button
                        type="button"
                        onClick={() => onRemove(row.candidate_name)}
                        title="Remove from comparison"
                        className="shrink-0 text-xs text-gray-400 hover:text-red-600"
                      >
                        Remove
                      </button>
                    </div>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
              <tr>
                <RowLabel>Score</RowLabel>
                {rows.map((row) => (
                  <Cell key={row.candidate_name}>
                    <ScoreRing score={row.final_score ?? row.overall_score} size={40} strokeWidth={4} />
                  </Cell>
                ))}
              </tr>
              <tr>
                <RowLabel>Skills matched</RowLabel>
                {rows.map((row) => {
                  const detail = joinCandidateDetail(row, fullResults)
                  const matched = detail?.match_scores?.skills?.matched ?? []
                  return <Cell key={row.candidate_name}>{matched.length > 0 ? matched.join(', ') : '—'}</Cell>
                })}
              </tr>
              <tr>
                <RowLabel>Missing must-haves</RowLabel>
                {rows.map((row) => {
                  const missing = row.top_missing_must_haves ?? []
                  return <Cell key={row.candidate_name}>{missing.length > 0 ? missing.join(', ') : '—'}</Cell>
                })}
              </tr>
              <tr>
                <RowLabel>Experience</RowLabel>
                {rows.map((row) => {
                  const detail = joinCandidateDetail(row, fullResults)
                  const years = detail?.match_scores?.experience?.years_experience
                  return <Cell key={row.candidate_name}>{years != null ? `${years} years` : '—'}</Cell>
                })}
              </tr>
              <tr>
                <RowLabel>Education</RowLabel>
                {rows.map((row) => {
                  const detail = joinCandidateDetail(row, fullResults)
                  const summary = detail?.education_summary ?? []
                  return (
                    <Cell key={row.candidate_name}>
                      {summary.length > 0 ? summary.join('; ') : 'No education listed'}
                    </Cell>
                  )
                })}
              </tr>
              <tr>
                <RowLabel>LLM experience relevance</RowLabel>
                {rows.map((row) => (
                  <Cell key={row.candidate_name}>
                    {row.experience_relevance_score ?? '—'}
                    {row.domain_fit ? ` · ${row.domain_fit} domain fit` : ''}
                  </Cell>
                ))}
              </tr>
              <tr>
                <RowLabel>Job stability</RowLabel>
                {rows.map((row) => (
                  <Cell key={row.candidate_name}>
                    {row.job_stability_flag === 'frequent_job_changes'
                      ? `Frequent job changes (${row.short_stints_count ?? '?'} short stints)`
                      : row.job_stability_flag === 'stable'
                        ? 'Stable'
                        : 'Not enough data'}
                  </Cell>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
