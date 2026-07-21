import type { CandidateResult, CandidateSummary, ScoreDetail } from '../../../api/types'
import { ScoreRing } from '../../../components/ScoreRing'
import { joinCandidateDetail } from '../lib/joinCandidateDetail'

interface CandidateDetailPanelProps {
  summaryRow: CandidateSummary
  fullResults: CandidateResult[]
  onClose?: () => void
}

function ScoreSection({ title, detail }: { title: string; detail: ScoreDetail | undefined }) {
  if (!detail) return null
  return (
    <div className="space-y-1">
      <h4 className="text-sm font-semibold">
        {title} {detail.score !== null && detail.score !== undefined ? `— ${detail.score}/100` : ''}
      </h4>
      {detail.matched && detail.matched.length > 0 && (
        <p className="text-xs text-green-700 dark:text-green-400">Matched: {detail.matched.join(', ')}</p>
      )}
      {detail.missing && detail.missing.length > 0 && (
        <p className="text-xs text-red-700 dark:text-red-400">Missing: {detail.missing.join(', ')}</p>
      )}
      {detail.evidence && detail.evidence.length > 0 && (
        <ul className="list-inside list-disc text-xs text-gray-600 dark:text-gray-400">
          {detail.evidence.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      )}
    </div>
  )
}

function EducationSection({
  detail,
  educationSummary,
}: {
  detail: ScoreDetail | undefined
  educationSummary: string[] | undefined
}) {
  const hasRequirement = detail?.score !== null && detail?.score !== undefined

  return (
    <div className="space-y-1">
      <h4 className="text-sm font-semibold">
        Education {hasRequirement ? `— ${detail!.score}/100` : '— not specified in JD'}
      </h4>
      {educationSummary && educationSummary.length > 0 ? (
        <ul className="list-inside list-disc text-xs text-gray-600 dark:text-gray-400">
          {educationSummary.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      ) : (
        <p className="text-xs text-gray-500 dark:text-gray-400">No education listed on this resume.</p>
      )}
      {hasRequirement && detail?.matched && detail.matched.length > 0 && (
        <p className="text-xs text-green-700 dark:text-green-400">Matched: {detail.matched.join(', ')}</p>
      )}
      {hasRequirement && detail?.missing && detail.missing.length > 0 && (
        <p className="text-xs text-red-700 dark:text-red-400">Missing: {detail.missing.join(', ')}</p>
      )}
    </div>
  )
}

export function CandidateDetailPanel({ summaryRow, fullResults, onClose }: CandidateDetailPanelProps) {
  const detail = joinCandidateDetail(summaryRow, fullResults)
  const score = summaryRow.final_score ?? summaryRow.overall_score
  const jobStabilityFlag = summaryRow.job_stability_flag ?? detail?.job_stability?.flag
  const avgTenure = summaryRow.average_tenure_years ?? detail?.job_stability?.average_tenure_years
  const shortStints = summaryRow.short_stints_count ?? detail?.job_stability?.short_stints_count ?? 0

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900 lg:sticky lg:top-4">
      <div className="mb-4 flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h3 className="truncate text-lg font-semibold">{summaryRow.candidate_name}</h3>
        </div>
        <div className="flex items-center gap-3">
          <ScoreRing score={score} size={48} />
          {onClose && (
            <button
              type="button"
              onClick={onClose}
              className="text-sm text-gray-500 hover:text-gray-800 dark:hover:text-gray-200"
            >
              Close
            </button>
          )}
        </div>
      </div>

      {jobStabilityFlag === 'frequent_job_changes' && (
        <div className="mb-4 rounded-md border border-orange-300 bg-orange-50 px-3 py-2 text-xs text-orange-800 dark:border-orange-800 dark:bg-orange-950/40 dark:text-orange-300">
          <span className="font-semibold">Frequent job changes — </span>
          {shortStints} role{shortStints === 1 ? '' : 's'} under 1 year
          {avgTenure != null ? ` · ~${avgTenure} yrs average tenure` : ''}. Worth asking about the reasons for these
          moves during screening; not an automatic disqualifier.
        </div>
      )}

      {!detail && <p className="text-sm text-gray-500 dark:text-gray-400">No detailed record found for this candidate.</p>}

      {detail && (
        <div className="space-y-4">
          {detail.manually_added && (
            <div className="rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
              Manually added by {detail.added_by ?? 'a reviewer'}: {detail.override_reason}
            </div>
          )}
          {detail.eligibility && detail.eligibility.missing_must_haves.length > 0 && (
            <p className="text-xs text-red-700 dark:text-red-400">
              Missing must-haves: {detail.eligibility.missing_must_haves.join(', ')}
            </p>
          )}
          <ScoreSection title="Skills" detail={detail.match_scores?.skills} />
          <ScoreSection title="Experience" detail={detail.match_scores?.experience} />
          <EducationSection detail={detail.match_scores?.education} educationSummary={detail.education_summary} />
          {detail.experience_relevance && (
            <div className="space-y-1">
              <h4 className="text-sm font-semibold">
                LLM experience relevance — {detail.experience_relevance.experience_relevance_score}
              </h4>
              <p className="text-xs text-gray-600 dark:text-gray-400">{detail.experience_relevance.reason}</p>
            </div>
          )}
          {detail.raw_text && (
            <details className="group">
              <summary className="cursor-pointer text-sm font-semibold text-gray-700 hover:text-gray-900 dark:text-gray-300 dark:hover:text-gray-100">
                Original resume text
              </summary>
              <pre className="mt-2 max-h-96 overflow-y-auto whitespace-pre-wrap rounded-md border border-gray-200 bg-gray-50 p-3 text-xs text-gray-600 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-400">
                {detail.raw_text}
              </pre>
            </details>
          )}
        </div>
      )}
    </div>
  )
}
