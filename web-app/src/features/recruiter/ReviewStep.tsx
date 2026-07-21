import { useState } from 'react'
import { ApiError, detailMessage } from '../../api/client'
import { resumePipeline } from '../../api/endpoints'
import type {
  BatchRankingResult,
  CandidateSummary,
  ManualAddition,
  PipelineResumeResponse,
  ReviewPayload,
} from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { ActionBar } from './components/ActionBar'
import { CandidateSplitView } from './components/CandidateSplitView'
import { ManualAddModal } from './components/ManualAddModal'
import { ScoreBadge } from './components/EligibilityBadge'

interface ReviewStepProps {
  threadId: string
  batchRanking: BatchRankingResult
  reviewPayload: ReviewPayload
  onResumed: (result: PipelineResumeResponse) => void
}

export function ReviewStep({ threadId, batchRanking, reviewPayload, onResumed }: ReviewStepProps) {
  const [addCandidate, setAddCandidate] = useState<CandidateSummary | null>(null)
  const [pendingManualAdditions, setPendingManualAdditions] = useState<ManualAddition[]>([])
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const submit = async (action: 'approve' | 'edit' | 'reject') => {
    setIsSubmitting(true)
    setError(null)
    try {
      const result = await resumePipeline({
        thread_id: threadId,
        action,
        manual_additions: action === 'edit' ? pendingManualAdditions : undefined,
      })
      onResumed(result)
    } catch (err) {
      // Preserve pending manual additions so a submit failure doesn't lose work.
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to submit the review decision.')
      setIsSubmitting(false)
    }
  }

  const handleApprove = () => submit(pendingManualAdditions.length > 0 ? 'edit' : 'approve')
  const handleReject = () => submit('reject')

  const removePending = (candidateName: string) => {
    setPendingManualAdditions((prev) => prev.filter((item) => item.candidate_name !== candidateName))
  }

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-xl font-semibold">Review shortlist — {reviewPayload.job_title ?? 'Untitled role'}</h2>
        {reviewPayload.used_relative_fallback ? (
          <div className="mt-2 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
            {reviewPayload.message}
          </div>
        ) : (
          <p className="text-sm text-gray-600 dark:text-gray-400">{reviewPayload.message}</p>
        )}
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <CandidateSplitView
        fullResults={batchRanking.results}
        groups={[
          {
            title: 'Shortlisted — LLM reranked',
            rows: reviewPayload.shortlist,
            extraColumns: [
              {
                header: 'Relevance',
                render: (row) => <ScoreBadge label="Relevance" score={row.experience_relevance_score} />,
              },
            ],
          },
          {
            title: 'Other candidates — first-pass only',
            rows: reviewPayload.other_candidates,
            emptyMessage: 'Every candidate made the shortlist.',
            rowActions: (row) => {
              const alreadyPending = pendingManualAdditions.some(
                (item) => item.candidate_name === row.candidate_name,
              )
              return alreadyPending ? (
                <button
                  type="button"
                  onClick={() => removePending(row.candidate_name)}
                  className="text-xs font-medium text-red-600 hover:underline"
                >
                  Remove
                </button>
              ) : (
                <button
                  type="button"
                  onClick={() => setAddCandidate(row)}
                  className="text-xs font-medium text-indigo-600 hover:underline"
                >
                  Add to shortlist
                </button>
              )
            },
          },
        ]}
      />

      {pendingManualAdditions.length > 0 && (
        <section className="space-y-2 rounded-md border border-indigo-200 bg-indigo-50 p-4 dark:border-indigo-900 dark:bg-indigo-950/30">
          <h3 className="text-sm font-semibold">Pending manual additions</h3>
          <ul className="space-y-1 text-sm">
            {pendingManualAdditions.map((addition) => (
              <li key={addition.candidate_name} className="flex items-center justify-between">
                <span>
                  <strong>{addition.candidate_name}</strong> — {addition.override_reason}
                </span>
                <button
                  type="button"
                  onClick={() => removePending(addition.candidate_name)}
                  className="text-xs text-red-600 hover:underline"
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </section>
      )}

      <ActionBar
        pendingCount={pendingManualAdditions.length}
        isSubmitting={isSubmitting}
        onApprove={handleApprove}
        onReject={handleReject}
      />

      {addCandidate && (
        <ManualAddModal
          candidate={addCandidate}
          pending={pendingManualAdditions}
          onConfirm={(addition) => {
            setPendingManualAdditions((prev) => [...prev, addition])
            setAddCandidate(null)
          }}
          onCancel={() => setAddCandidate(null)}
        />
      )}
    </div>
  )
}
