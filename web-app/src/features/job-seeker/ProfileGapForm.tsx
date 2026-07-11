import { useState, type FormEvent, type KeyboardEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { analyzeProfileGap, parseUpload } from '../../api/endpoints'
import { ApiError, detailMessage } from '../../api/client'
import type { ProfileGapResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { FileInput } from '../../components/FileInput'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { ADZUNA_COUNTRIES } from '../../lib/adzunaCountries'

interface ProfileGapFormProps {
  onResult: (result: ProfileGapResponse) => void
}

type Phase = 'idle' | 'parsing' | 'analyzing'
type JdMode = 'paste' | 'upload'

function segmentButtonClass(active: boolean) {
  return `rounded-md px-3 py-1 text-xs font-medium ${
    active
      ? 'bg-indigo-600 text-white'
      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
  }`
}

export function ProfileGapForm({ onResult }: ProfileGapFormProps) {
  const navigate = useNavigate()
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jdMode, setJdMode] = useState<JdMode>('upload')
  const [jdText, setJdText] = useState('')
  const [jdFile, setJdFile] = useState<File | null>(null)
  const [targetRole, setTargetRole] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)

  const [showJobSearch, setShowJobSearch] = useState(false)
  const [searchQuery, setSearchQuery] = useState('')
  const [searchLocation, setSearchLocation] = useState('')
  const [searchCountry, setSearchCountry] = useState('in')

  const isBusy = phase !== 'idle'

  const goToSearchResults = () => {
    if (!searchQuery.trim()) return
    const params = new URLSearchParams({ query: searchQuery.trim(), country: searchCountry })
    if (searchLocation.trim()) params.set('location', searchLocation.trim())
    navigate(`/job-seeker/search?${params.toString()}`)
  }

  const handleSearchKeyDown = (event: KeyboardEvent) => {
    if (event.key === 'Enter') {
      event.preventDefault()
      goToSearchResults()
    }
  }

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    if (!resumeFile) {
      setError('Upload your resume.')
      return
    }
    if (jdMode === 'paste' && !jdText.trim()) {
      setError('Paste a job description, or switch to file upload.')
      return
    }
    if (jdMode === 'upload' && !jdFile) {
      setError('Upload a job description file, or switch to paste text.')
      return
    }

    setPhase('parsing')
    try {
      const jdFileToSend =
        jdMode === 'upload' ? jdFile! : new File([jdText], 'job_description.txt', { type: 'text/plain' })
      const parsed = await parseUpload(jdFileToSend, [resumeFile])
      if (parsed.candidates.length === 0) {
        setError('Could not parse your resume. Try a different file.')
        setPhase('idle')
        return
      }

      setPhase('analyzing')
      const result = await analyzeProfileGap({
        jd: parsed.jd,
        candidate: parsed.candidates[0],
        target_role: targetRole.trim() || undefined,
      })
      onResult(result)
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to analyze your profile.')
      setPhase('idle')
    }
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div className="space-y-3">
        <button
          type="button"
          onClick={() => setShowJobSearch((current) => !current)}
          className="w-full rounded-md border border-indigo-300 bg-indigo-50 px-4 py-2 text-center text-sm font-medium text-indigo-700 hover:bg-indigo-100 dark:border-indigo-800 dark:bg-indigo-950/30 dark:text-indigo-300 dark:hover:bg-indigo-950/50"
        >
          {showJobSearch ? 'Hide job search' : 'Search real jobs'}
        </button>

        {showJobSearch && (
          <div className="flex flex-col gap-2 sm:flex-row">
            <input
              type="text"
              value={searchQuery}
              onChange={(event) => setSearchQuery(event.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="Job title or keywords"
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
            />
            <input
              type="text"
              value={searchLocation}
              onChange={(event) => setSearchLocation(event.target.value)}
              onKeyDown={handleSearchKeyDown}
              placeholder="Location (optional)"
              className="flex-1 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
            />
            <select
              value={searchCountry}
              onChange={(event) => setSearchCountry(event.target.value)}
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
              onClick={goToSearchResults}
              className="shrink-0 rounded-md bg-indigo-600 px-6 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Search
            </button>
          </div>
        )}

        <div className="flex items-center gap-2 text-xs text-gray-400 dark:text-gray-600">
          <span className="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
          <span>or</span>
          <span className="h-px flex-1 bg-gray-200 dark:bg-gray-800" />
        </div>
      </div>

      <div>
        <h2 className="text-xl font-semibold">Check your fit for a role</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Upload your resume and paste a job description to see what you're missing.
        </p>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="resume-file" className="block text-sm font-medium">
            Your resume
          </label>
          <FileInput
            id="resume-file"
            accept=".txt,.pdf,.docx"
            disabled={isBusy}
            value={resumeFile ? [resumeFile] : []}
            onChange={(files) => setResumeFile(files[0] ?? null)}
          />
        </div>

        <div>
          <div className="flex items-center justify-between">
            <label className="block text-sm font-medium">Job description</label>
            <div className="flex gap-1">
              <button
                type="button"
                disabled={isBusy}
                onClick={() => setJdMode('paste')}
                className={segmentButtonClass(jdMode === 'paste')}
              >
                Paste text
              </button>
              <button
                type="button"
                disabled={isBusy}
                onClick={() => setJdMode('upload')}
                className={segmentButtonClass(jdMode === 'upload')}
              >
                Upload file
              </button>
            </div>
          </div>

          {jdMode === 'paste' ? (
            <textarea
              rows={8}
              value={jdText}
              disabled={isBusy}
              onChange={(event) => setJdText(event.target.value)}
              placeholder="Paste the job description here…"
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
            />
          ) : (
            <FileInput
              id="jd-file"
              accept=".txt,.pdf,.docx"
              disabled={isBusy}
              value={jdFile ? [jdFile] : []}
              onChange={(files) => setJdFile(files[0] ?? null)}
            />
          )}
        </div>

        <label className="block text-sm font-medium">
          Target role (optional)
          <input
            type="text"
            value={targetRole}
            disabled={isBusy}
            onChange={(event) => setTargetRole(event.target.value)}
            placeholder="e.g. Machine Learning Engineer"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </label>

        <button
          type="submit"
          disabled={isBusy}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Analyze my fit
        </button>

        {isBusy && (
          <LoadingSpinner label={phase === 'parsing' ? 'Parsing your resume…' : 'Analyzing qualification gaps…'} />
        )}
      </form>
    </div>
  )
}
