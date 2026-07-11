import { useState, type FormEvent } from 'react'
import { analyzeProfileGap, parseUpload } from '../../api/endpoints'
import { ApiError, detailMessage } from '../../api/client'
import type { ProfileGapResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'

interface ProfileGapFormProps {
  onResult: (result: ProfileGapResponse) => void
}

type Phase = 'idle' | 'parsing' | 'analyzing'

export function ProfileGapForm({ onResult }: ProfileGapFormProps) {
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [jdText, setJdText] = useState('')
  const [targetRole, setTargetRole] = useState('')
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)

  const isBusy = phase !== 'idle'

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    setError(null)

    if (!resumeFile || !jdText.trim()) {
      setError('Upload your resume and paste a job description.')
      return
    }

    setPhase('parsing')
    try {
      const jdFile = new File([jdText], 'job_description.txt', { type: 'text/plain' })
      const parsed = await parseUpload(jdFile, [resumeFile])
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
      <div>
        <h2 className="text-xl font-semibold">Check your fit for a role</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Upload your resume and paste a job description to see what you're missing.
        </p>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <form onSubmit={handleSubmit} className="space-y-4">
        <label className="block text-sm font-medium">
          Your resume
          <input
            type="file"
            accept=".txt,.pdf,.docx"
            disabled={isBusy}
            onChange={(event) => setResumeFile(event.target.files?.[0] ?? null)}
            className="mt-1 block w-full text-sm"
          />
        </label>

        <label className="block text-sm font-medium">
          Job description
          <textarea
            rows={8}
            value={jdText}
            disabled={isBusy}
            onChange={(event) => setJdText(event.target.value)}
            placeholder="Paste the job description here…"
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </label>

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
