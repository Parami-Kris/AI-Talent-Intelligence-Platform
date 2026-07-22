import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, detailMessage } from '../../api/client'
import { clearJobHistory, getMyJobs } from '../../api/endpoints'
import type { MyJobEntry, MyJobsResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { getCandidateId } from '../../lib/candidateId'

type Section = 'liked' | 'applied'

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
  const [confirmingClear, setConfirmingClear] = useState<Section | null>(null)
  const [isClearing, setIsClearing] = useState(false)

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

  const confirmClear = async (section: Section) => {
    setIsClearing(true)
    try {
      await clearJobHistory(getCandidateId(), section)
      setData((current) => (current ? { ...current, [section]: [] } : current))
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : `Failed to clear your ${section} history.`)
    } finally {
      setIsClearing(false)
      setConfirmingClear(null)
    }
  }

  const sections: { key: Section; title: string; emptyMessage: string }[] = [
    { key: 'liked', title: 'Liked', emptyMessage: 'No liked jobs yet.' },
    { key: 'applied', title: 'Applied', emptyMessage: 'No applications logged yet.' },
  ]

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
          {sections.map(({ key, title, emptyMessage }) => (
            <section key={key} className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                  {title} ({data[key].length})
                </h3>
                {data[key].length > 0 && confirmingClear !== key && (
                  <button
                    type="button"
                    onClick={() => setConfirmingClear(key)}
                    className="text-xs font-medium text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400"
                  >
                    Clear
                  </button>
                )}
              </div>

              {confirmingClear === key && (
                <div className="flex items-center gap-2 rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs dark:border-gray-800 dark:bg-gray-800/50">
                  <span className="text-gray-600 dark:text-gray-400">Clear all {title.toLowerCase()} history?</span>
                  <button
                    type="button"
                    disabled={isClearing}
                    onClick={() => confirmClear(key)}
                    className="rounded-md bg-red-600 px-2 py-1 font-medium text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    Yes, clear
                  </button>
                  <button
                    type="button"
                    disabled={isClearing}
                    onClick={() => setConfirmingClear(null)}
                    className="rounded-md px-2 py-1 font-medium text-gray-500 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-700"
                  >
                    Cancel
                  </button>
                </div>
              )}

              <JobList jobs={data[key]} emptyMessage={emptyMessage} />
            </section>
          ))}
        </div>
      )}
    </div>
  )
}
