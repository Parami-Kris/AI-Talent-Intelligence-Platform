import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, detailMessage } from '../../api/client'
import { listRuns } from '../../api/endpoints'
import type { RunSummary } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'

export function ShortlistsPage() {
  const [runs, setRuns] = useState<RunSummary[] | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    listRuns()
      .then((result) => setRuns(result.runs))
      .catch((err) =>
        setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to load your shortlists.'),
      )
  }, [])

  if (error) return <ErrorBanner message={error} />
  if (runs === null) return <LoadingSpinner label="Loading your shortlists…" />

  return (
    <div className="space-y-4">
      <h2 className="text-xl font-semibold">My Shortlists</h2>

      {runs.length === 0 ? (
        <p className="text-sm text-gray-600 dark:text-gray-400">
          No screening runs yet. Once you persist a run from the Recruiter Dashboard, it'll show up here so you can
          revisit it later.
        </p>
      ) : (
        <div className="divide-y divide-gray-200 rounded-md border border-gray-200 dark:divide-gray-800 dark:border-gray-800">
          {runs.map((run) => (
            <Link
              key={run.id}
              to={`/recruiter/shortlists/${run.id}`}
              className="flex items-center justify-between gap-3 px-4 py-3 hover:bg-gray-50 dark:hover:bg-gray-900"
            >
              <div className="min-w-0">
                <p className="truncate font-medium">{run.run_name}</p>
                <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                  {run.job_title ?? 'No job title'} · {new Date(run.created_at).toLocaleString()}
                </p>
              </div>
              <span className="shrink-0 text-sm text-gray-500 dark:text-gray-400">
                {run.candidate_count} shortlisted
              </span>
            </Link>
          ))}
        </div>
      )}
    </div>
  )
}
