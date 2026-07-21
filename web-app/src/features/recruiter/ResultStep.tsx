import type { BatchRankingResult, PersistenceResult, RerankedResult } from '../../api/types'
import { CandidateSplitView } from './components/CandidateSplitView'

interface ResultStepProps {
  status: 'persisted' | 'rejected'
  reranked: RerankedResult | null
  persistenceResult: PersistenceResult | null
  onStartNew: () => void
}

interface NoEligibleStepProps {
  batchRanking: BatchRankingResult
  onStartNew: () => void
}

export function ResultStep({ status, reranked, persistenceResult, onStartNew }: ResultStepProps) {
  return (
    <div className="space-y-6">
      {status === 'persisted' ? (
        <div className="rounded-md border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300">
          Screening run persisted — run #{persistenceResult?.run_id}, {persistenceResult?.saved_rankings}{' '}
          candidate(s) saved.
        </div>
      ) : (
        <div className="rounded-md border border-gray-300 bg-gray-50 px-4 py-3 text-sm text-gray-700 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-300">
          This screening run was discarded — nothing was persisted.
        </div>
      )}

      {reranked && (
        <CandidateSplitView
          fullResults={reranked.results}
          groups={[
            {
              title: 'Final results',
              rows: reranked.summary,
              extraColumns: [
                {
                  header: 'Manual add',
                  render: (row) =>
                    row.manually_added ? <span title={row.override_reason as string}>Yes</span> : '—',
                },
              ],
            },
          ]}
        />
      )}

      <button
        type="button"
        onClick={onStartNew}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
      >
        Start new screening
      </button>
    </div>
  )
}

export function NoEligibleStep({ batchRanking, onStartNew }: NoEligibleStepProps) {
  return (
    <div className="space-y-6">
      <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
        No candidate met the hard eligibility requirements for{' '}
        <strong>{batchRanking.job_title ?? 'this role'}</strong> — the shortlist reranking step was skipped.
      </div>

      <CandidateSplitView
        fullResults={batchRanking.results}
        groups={[{ title: 'Candidates', rows: batchRanking.summary, emptyMessage: 'No candidates were ranked.' }]}
      />

      <button
        type="button"
        onClick={onStartNew}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
      >
        Start new screening
      </button>
    </div>
  )
}
