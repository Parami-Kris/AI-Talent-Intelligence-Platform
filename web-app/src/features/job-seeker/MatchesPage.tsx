import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { ApiError, detailMessage } from '../../api/client'
import { getJobMatches, getSavedResume } from '../../api/endpoints'
import type { Candidate, JobMatchResult } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { JOB_SEARCH_COUNTRIES } from '../../lib/jobSearchCountries'
import { TailorResumePanel } from './TailorResumePanel'

const TOP_N_OPTIONS = [5, 10, 20, 25]

function jobKey(job: JobMatchResult): string {
  return `${job.source}-${job.id}`
}

function matchBadgeClass(pct: number | null): string {
  if (pct === null) return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
  if (pct >= 75) return 'bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300'
  if (pct >= 50) return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
  return 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
}

export function MatchesPage() {
  const [hasSavedResume, setHasSavedResume] = useState<boolean | null>(null)
  const [savedResume, setSavedResume] = useState<Candidate | null>(null)
  const [query, setQuery] = useState('')
  const [location, setLocation] = useState('')
  const [country, setCountry] = useState('in')
  const [topN, setTopN] = useState(10)
  const [results, setResults] = useState<JobMatchResult[] | null>(null)
  const [quotaRemaining, setQuotaRemaining] = useState<number | null>(null)
  const [selected, setSelected] = useState<JobMatchResult | null>(null)
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    getSavedResume()
      .then((saved) => {
        setHasSavedResume(!!saved.parsed_resume)
        setSavedResume(saved.parsed_resume ?? null)
      })
      .catch(() => setHasSavedResume(false))
  }, [])

  const handleSearch = async () => {
    setError(null)
    setIsSearching(true)
    try {
      const response = await getJobMatches(query.trim(), location.trim() || undefined, country, topN)
      setResults(response.results)
      setQuotaRemaining(response.quota_remaining_today)
      setSelected(response.results[0] ?? null)
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to load job matches.')
    } finally {
      setIsSearching(false)
    }
  }

  if (hasSavedResume === null) {
    return <LoadingSpinner label="Loading…" />
  }

  if (!hasSavedResume) {
    return (
      <div className="space-y-3">
        <h2 className="text-xl font-semibold">Job Matches</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Save a resume first to see jobs sorted by how well they match you.
        </p>
        <Link to="/job-seeker" className="inline-block text-sm text-indigo-600 hover:underline dark:text-indigo-400">
          Go check your fit and save a resume →
        </Link>
      </div>
    )
  }

  const maxTopN = quotaRemaining !== null ? Math.min(25, quotaRemaining) : 25
  const quotaExhausted = quotaRemaining !== null && quotaRemaining <= 0

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-xl font-semibold">Job Matches</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Jobs sorted by how well they match your saved resume.
          {quotaRemaining !== null && ` ${quotaRemaining} match${quotaRemaining === 1 ? '' : 'es'} left today.`}
        </p>
      </div>

      <div className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900 sm:flex-row">
        <input
          type="text"
          value={query}
          disabled={isSearching}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Job title or keywords (optional)"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        />
        <input
          type="text"
          value={location}
          disabled={isSearching}
          onChange={(event) => setLocation(event.target.value)}
          placeholder="Location (optional)"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        />
        <select
          value={country}
          disabled={isSearching}
          onChange={(event) => setCountry(event.target.value)}
          className="shrink-0 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          {JOB_SEARCH_COUNTRIES.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </select>
        <select
          value={topN}
          disabled={isSearching}
          onChange={(event) => setTopN(Number(event.target.value))}
          className="shrink-0 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          {TOP_N_OPTIONS.filter((n) => n <= maxTopN || n === TOP_N_OPTIONS[0]).map((n) => (
            <option key={n} value={n}>
              Top {n}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={isSearching || quotaExhausted}
          onClick={() => void handleSearch()}
          className="shrink-0 rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Find matches
        </button>
      </div>

      {quotaExhausted && (
        <p className="text-xs text-amber-700 dark:text-amber-400">
          You've used today's job-matching limit — come back tomorrow for more.
        </p>
      )}

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      {isSearching && <LoadingSpinner label="Scoring jobs against your resume…" />}

      {results && !isSearching && (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[380px_1fr]">
          <div className="max-h-[70vh] space-y-2 overflow-y-auto">
            {results.length === 0 && (
              <p className="text-sm text-gray-500 dark:text-gray-400">No results. Try different keywords.</p>
            )}
            {results.map((job) => {
              const isSelected = selected?.source === job.source && selected?.id === job.id
              return (
                <button
                  type="button"
                  key={jobKey(job)}
                  onClick={() => setSelected(job)}
                  className={`block w-full rounded-md border p-3 text-left text-sm ${
                    isSelected
                      ? 'border-indigo-400 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-950/30'
                      : 'border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 dark:border-gray-800 dark:hover:border-indigo-700 dark:hover:bg-indigo-950/30'
                  }`}
                >
                  <div className="flex items-start justify-between gap-2">
                    <p className="truncate font-medium">{job.title ?? 'Untitled role'}</p>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${matchBadgeClass(job.match_percentage)}`}
                    >
                      {job.match_percentage !== null ? `${job.match_percentage}%` : '—'}
                    </span>
                  </div>
                  <p className="truncate text-xs text-gray-500 dark:text-gray-400">
                    {[job.company, job.location].filter(Boolean).join(' · ')}
                  </p>
                </button>
              )
            })}
          </div>

          <div className="rounded-lg border border-gray-200 bg-white p-6 dark:border-gray-800 dark:bg-gray-900">
            {selected ? (
              <div className="space-y-4">
                <div>
                  <div className="flex items-start justify-between gap-3">
                    <h2 className="text-lg font-semibold">{selected.title ?? 'Untitled role'}</h2>
                    <span
                      className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${matchBadgeClass(selected.match_percentage)}`}
                    >
                      {selected.match_percentage !== null ? `${selected.match_percentage}% match` : 'Not scored'}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {[selected.company, selected.location].filter(Boolean).join(' · ')}
                  </p>
                  {selected.match_reason && (
                    <p className="mt-2 text-xs text-gray-600 dark:text-gray-400">{selected.match_reason}</p>
                  )}
                  {selected.url && (
                    <a
                      href={selected.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="mt-2 inline-block text-sm text-indigo-600 hover:underline dark:text-indigo-400"
                    >
                      View original posting ↗
                    </a>
                  )}
                </div>

                <div>
                  <h3 className="mb-1 text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    Job details
                  </h3>
                  <p className="whitespace-pre-wrap text-sm text-gray-700 dark:text-gray-300">
                    {selected.description ?? 'No description available.'}
                  </p>
                </div>

                {savedResume && (
                  <TailorResumePanel
                    key={jobKey(selected)}
                    jd={{
                      job_title: selected.title ?? undefined,
                      company: selected.company ?? undefined,
                      location: selected.location ?? undefined,
                      description: selected.description ?? undefined,
                    }}
                    candidate={savedResume}
                    targetRole={selected.title ?? undefined}
                  />
                )}
              </div>
            ) : (
              <p className="text-sm text-gray-500 dark:text-gray-400">Select a job to see details.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
