import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { ApiError, detailMessage } from '../../api/client'
import { getRun, setCandidateShortlisted } from '../../api/endpoints'
import type { CandidateResult, RunDetail } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { CandidateSplitView } from './components/CandidateSplitView'

export function ShortlistDetailPage() {
  const { runId } = useParams<{ runId: string }>()
  const [run, setRun] = useState<RunDetail | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!runId) return
    getRun(Number(runId))
      .then(setRun)
      .catch((err) => setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to load this run.'))
  }, [runId])

  if (error) return <ErrorBanner message={error} />
  if (run === null) return <LoadingSpinner label="Loading run…" />

  const toggleShortlisted = async (row: CandidateResult) => {
    if (row.candidate_id == null || !runId) return
    const nextValue = !row.is_shortlisted
    await setCandidateShortlisted(Number(runId), row.candidate_id, nextValue)
    setRun((current) =>
      current
        ? {
            ...current,
            candidates: current.candidates.map((item) =>
              item.candidate_id === row.candidate_id ? { ...item, is_shortlisted: nextValue } : item,
            ),
          }
        : current,
    )
  }

  const shortlisted = run.candidates.filter((candidate) => candidate.is_shortlisted)
  const pruned = run.candidates.filter((candidate) => !candidate.is_shortlisted)

  return (
    <div className="space-y-6">
      <div>
        <Link
          to="/recruiter/shortlists"
          className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
        >
          ← Back to My Shortlists
        </Link>
        <h2 className="mt-1 text-xl font-semibold">{run.run_name}</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">{run.job_title ?? 'No job title'}</p>
      </div>

      <CandidateSplitView
        groups={[
          {
            title: 'Shortlisted',
            rows: shortlisted,
            rowActions: (row) => (
              <button
                type="button"
                onClick={() => toggleShortlisted(row as unknown as CandidateResult)}
                className="text-xs font-medium text-gray-500 hover:underline"
              >
                Remove from shortlist
              </button>
            ),
            emptyMessage: 'No candidates currently shortlisted.',
          },
          {
            title: 'Removed from shortlist',
            rows: pruned,
            rowActions: (row) => (
              <button
                type="button"
                onClick={() => toggleShortlisted(row as unknown as CandidateResult)}
                className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
              >
                Re-add to shortlist
              </button>
            ),
            emptyMessage: 'Nothing pruned yet.',
          },
        ]}
        fullResults={run.candidates}
      />
    </div>
  )
}
