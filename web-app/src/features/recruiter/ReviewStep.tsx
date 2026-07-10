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
import { CandidateDetailDrawer } from './components/CandidateDetailDrawer'
import { CandidateTable } from './components/CandidateTable'
import { ManualAddModal } from './components/ManualAddModal'
import { ScoreBadge } from './components/EligibilityBadge'

interface ReviewStepProps {
  threadId: string
  batchRanking: BatchRankingResult
  reviewPayload: ReviewPayload
  onResumed: (result: PipelineResumeResponse) => void
}

export function ReviewStep({ threadId, batchRanking, reviewPayload, onResumed }: ReviewStepProps) {
  const [detailRow, setDetailRow] = useState<CandidateSummary | null>(null)
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
        <p className="text-sm text-gray-600 dark:text-gray-400">{reviewPayload.message}</p>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Shortlisted — LLM reranked ({reviewPayload.shortlist.length})
        </h3>
        <CandidateTable
          rows={reviewPayload.shortlist}
          onRowClick={setDetailRow}
          extraColumns={[
            {
              header: 'Relevance',
              render: (row) => <ScoreBadge label="Relevance" score={row.experience_relevance_score} />,
            },
          ]}
        />
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
          Other candidates — first-pass only ({reviewPayload.other_candidates.length})
        </h3>
        <CandidateTable
          rows={reviewPayload.other_candidates}
          onRowClick={setDetailRow}
          emptyMessage="Every candidate made the shortlist."
          rowActions={(row) => {
            const alreadyPending = pendingManualAdditions.some((item) => item.candidate_name === row.candidate_name)
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
          }}
        />
      </section>

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

      {detailRow && (
        <CandidateDetailDrawer
          summaryRow={detailRow}
          fullResults={batchRanking.results}
          onClose={() => setDetailRow(null)}
        />
      )}

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
