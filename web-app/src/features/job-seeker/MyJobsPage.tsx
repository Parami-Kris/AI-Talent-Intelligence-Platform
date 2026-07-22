import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, detailMessage } from '../../api/client'
import { getMyJobs } from '../../api/endpoints'
import type { MyJobEntry, MyJobsResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { getCandidateId } from '../../lib/candidateId'

function JobList({ jobs, emptyMessage }: { jobs: MyJobEntry[]; emptyMessage: string }) {
  if (jobs.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">{emptyMessage}</p>
  }

  return (
    <ul className="space-y-2">
      {jobs.map((job) => (
        <li
          key={`${job.source}-${job.id}`}
          className="rounded-md border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900"
        >
          <p className="font-medium">{job.title ?? 'Untitled role'}</p>
          <p className="text-xs text-gray-500 dark:text-gray-400">
            {[job.company, job.location].filter(Boolean).join(' · ')}
          </p>
          {job.url && (
            <a
              href={job.url}
              target="_blank"
              rel="noopener noreferrer"
              className="mt-1 inline-block text-xs text-indigo-600 hover:underline dark:text-indigo-400"
            >
              View posting ↗
            </a>
          )}
        </li>
      ))}
    </ul>
  )
}

export function MyJobsPage() {
  const [data, setData] = useState<MyJobsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    setIsLoading(true)
    setError(null)
    getMyJobs(getCandidateId())
      .then((response) => {
        if (!cancelled) setData(response)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to load your jobs.')
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  return (
    <div className="space-y-4">
      <Link to="/job-seeker/search" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
        ← Back to job search
      </Link>

      <h2 className="text-xl font-semibold">My Jobs</h2>

      {isLoading && <LoadingSpinner label="Loading your jobs…" />}
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      {data && !isLoading && (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
          <section className="space-y-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Liked ({data.liked.length})
            </h3>
            <JobList jobs={data.liked} emptyMessage="No liked jobs yet." />
          </section>

          <section className="space-y-2">
            <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              Applied ({data.applied.length})
            </h3>
            <JobList jobs={data.applied} emptyMessage="No applications logged yet." />
          </section>
        </div>
      )}
    </div>
  )
}
