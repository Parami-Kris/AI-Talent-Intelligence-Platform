import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { ApiError, detailMessage } from '../../api/client'
import { logJobEvent, searchJobs } from '../../api/endpoints'
import type { JobEventType, JobSearchResult } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { ADZUNA_COUNTRIES } from '../../lib/adzunaCountries'
import { getCandidateId } from '../../lib/candidateId'
import { JobFitCheck } from './JobFitCheck'

function jobKey(job: JobSearchResult): string {
  return `${job.source}-${job.id}`
}

export function JobSearchResultsPage() {
  const [searchParams] = useSearchParams()
  const [query, setQuery] = useState(() => searchParams.get('query') ?? '')
  const [location, setLocation] = useState(() => searchParams.get('location') ?? '')
  const [country, setCountry] = useState(() => searchParams.get('country') ?? 'in')
  const [results, setResults] = useState<JobSearchResult[] | null>(null)
  const [expandedTitles, setExpandedTitles] = useState<string[]>([])
  const [recommended, setRecommended] = useState(false)
  const [selected, setSelected] = useState<JobSearchResult | null>(null)
  const [likedKeys, setLikedKeys] = useState<Set<string>>(new Set())
  const [isSearching, setIsSearching] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Cancels a still-in-flight search (rather than just ignoring its result) when a
  // newer one starts - e.g. React StrictMode's dev-only double-invoked effect, or a
  // user re-searching before the first call resolves. Actually aborting (not just
  // ignoring) avoids doubling up real outbound API load against rate-limited keys.
  const activeSearchController = useRef<AbortController | null>(null)

  const logEvent = (eventType: JobEventType, job: JobSearchResult) => {
    // Fire-and-forget - history logging must never block or interrupt the actual
    // job-search flow.
    logJobEvent({
      candidate_id: getCandidateId(),
      event_type: eventType,
      job_source: job.source,
      job_external_id: job.id,
      job_title: job.title,
      company: job.company,
      location: job.location,
    }).catch(() => {})
  }

  const selectJob = (job: JobSearchResult) => {
    setSelected(job)
    logEvent('viewed', job)
  }

  const handleLike = (job: JobSearchResult) => {
    if (likedKeys.has(jobKey(job))) return
    setLikedKeys((prev) => new Set(prev).add(jobKey(job)))
    logEvent('liked', job)
  }

  const handleSearch = async () => {
    activeSearchController.current?.abort()
    const controller = new AbortController()
    activeSearchController.current = controller

    setError(null)
    setIsSearching(true)
    try {
      const response = await searchJobs(
        query.trim(),
        location.trim() || undefined,
        country,
        controller.signal,
        getCandidateId(),
      )
      setResults(response.results)
      setExpandedTitles(response.expanded_titles)
      setRecommended(response.recommended)
      if (response.recommended) setQuery(response.used_query)
      const first = response.results[0] ?? null
      setSelected(first)
      if (first) logEvent('viewed', first)
    } catch (err) {
      if (err instanceof DOMException && err.name === 'AbortError') return // superseded by a newer search
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to search jobs.')
    } finally {
      if (activeSearchController.current === controller) setIsSearching(false)
    }
  }

  // Auto-run the search once if we arrived here via the inline search bar on the
  // main job-seeker page - either with a query, or deliberately blank to trigger
  // the recommended-from-history search (searchParams still carries `country` in
  // that case, which is how we tell "navigated here" apart from a cold direct
  // visit to this URL with nothing to search). Aborts on cleanup so StrictMode's
  // synthetic dev-mode remount cancels the first invocation's request instead of
  // leaving it to run to completion in the background.
  useEffect(() => {
    if (query.trim() || searchParams.toString()) {
      void handleSearch()
    }
    return () => activeSearchController.current?.abort()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      void handleSearch()
    }
  }

  return (
    <div className="space-y-4">
      <Link to="/job-seeker" className="text-sm text-indigo-600 hover:underline dark:text-indigo-400">
        ← Back to profile check
      </Link>

      <div className="flex flex-col gap-2 rounded-lg border border-gray-200 bg-white p-3 dark:border-gray-800 dark:bg-gray-900 sm:flex-row">
        <input
          type="text"
          value={query}
          disabled={isSearching}
          onChange={(event) => setQuery(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Job title or keywords (leave blank once you've liked a few jobs)"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        />
        <input
          type="text"
          value={location}
          disabled={isSearching}
          onChange={(event) => setLocation(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Location (optional)"
          className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        />
        <select
          value={country}
          disabled={isSearching}
          onChange={(event) => setCountry(event.target.value)}
          className="shrink-0 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        >
          {ADZUNA_COUNTRIES.map((option) => (
            <option key={option.code} value={option.code}>
              {option.label}
            </option>
          ))}
        </select>
        <button
          type="button"
          disabled={isSearching}
          onClick={() => void handleSearch()}
          className="shrink-0 rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Find jobs
        </button>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      {isSearching && <LoadingSpinner label="Searching job boards…" />}

      {!isSearching && recommended && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          No keyword entered — showing results for <span className="font-medium">{query}</span>, based on jobs
          you've liked, applied to, or viewed.
        </p>
      )}

      {!isSearching && expandedTitles.length > 0 && (
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Also searching related titles: <span className="font-medium">{expandedTitles.join(', ')}</span>
        </p>
      )}

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
                  onClick={() => selectJob(job)}
                  className={`block w-full rounded-md border p-3 text-left text-sm ${
                    isSelected
                      ? 'border-indigo-400 bg-indigo-50 dark:border-indigo-700 dark:bg-indigo-950/30'
                      : 'border-gray-200 hover:border-indigo-300 hover:bg-indigo-50 dark:border-gray-800 dark:hover:border-indigo-700 dark:hover:bg-indigo-950/30'
                  }`}
                >
                  <p className="truncate font-medium">{job.title ?? 'Untitled role'}</p>
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
                    <button
                      type="button"
                      onClick={() => handleLike(selected)}
                      title="Like this job — helps us recommend similar roles"
                      className={`shrink-0 rounded-md border px-2 py-1 text-xs font-medium ${
                        likedKeys.has(jobKey(selected))
                          ? 'border-pink-300 bg-pink-100 text-pink-700 dark:border-pink-800 dark:bg-pink-950/40 dark:text-pink-300'
                          : 'border-gray-300 text-gray-500 hover:border-pink-300 hover:text-pink-600 dark:border-gray-700 dark:text-gray-400'
                      }`}
                    >
                      {likedKeys.has(jobKey(selected)) ? '♥ Liked' : '♡ Like'}
                    </button>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    {[selected.company, selected.location].filter(Boolean).join(' · ')}
                  </p>
                  {selected.url && (
                    <a
                      href={selected.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      onClick={() => logEvent('applied', selected)}
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

                <JobFitCheck key={`${selected.source}-${selected.id}`} job={selected} />
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
