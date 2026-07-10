import type { CandidateResult, CandidateSummary, ScoreDetail } from '../../../api/types'
import { joinCandidateDetail } from '../lib/joinCandidateDetail'

interface CandidateDetailDrawerProps {
  summaryRow: CandidateSummary
  fullResults: CandidateResult[]
  onClose: () => void
}

function ScoreSection({ title, detail }: { title: string; detail: ScoreDetail | undefined }) {
  if (!detail) return null
  return (
    <div className="space-y-1">
      <h4 className="text-sm font-semibold">
        {title} {detail.score !== null && detail.score !== undefined ? `— ${detail.score}` : ''}
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

export function CandidateDetailDrawer({ summaryRow, fullResults, onClose }: CandidateDetailDrawerProps) {
  const detail = joinCandidateDetail(summaryRow, fullResults)

  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-black/30" onClick={onClose}>
      <div
        className="h-full w-full max-w-md overflow-y-auto bg-white p-6 shadow-xl dark:bg-gray-900"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="mb-4 flex items-start justify-between">
          <h3 className="text-lg font-semibold">{summaryRow.candidate_name}</h3>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-gray-800 dark:hover:text-gray-200">
            Close
          </button>
        </div>

        {!detail && (
          <p className="text-sm text-gray-500 dark:text-gray-400">
            No detailed record found for this candidate.
          </p>
        )}

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
            <ScoreSection title="Education" detail={detail.match_scores?.education} />
            {detail.experience_relevance && (
              <div className="space-y-1">
                <h4 className="text-sm font-semibold">
                  LLM experience relevance — {detail.experience_relevance.experience_relevance_score}
                </h4>
                <p className="text-xs text-gray-600 dark:text-gray-400">{detail.experience_relevance.reason}</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
