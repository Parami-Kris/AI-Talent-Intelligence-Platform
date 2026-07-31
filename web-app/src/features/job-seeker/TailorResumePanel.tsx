import { useState } from 'react'
import { ApiError, detailMessage } from '../../api/client'
import { tailorResume } from '../../api/endpoints'
import type { Candidate, Jd, TailorResumeResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { LoadingSpinner } from '../../components/LoadingSpinner'

interface TailorResumePanelProps {
  jd: Jd
  candidate: Candidate
  targetRole?: string
}

export function TailorResumePanel({ jd, candidate, targetRole }: TailorResumePanelProps) {
  const [phase, setPhase] = useState<'idle' | 'loading' | 'done'>('idle')
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<TailorResumeResponse | null>(null)

  const handleTailor = async () => {
    setError(null)
    setPhase('loading')
    try {
      const response = await tailorResume({ jd, candidate, target_role: targetRole })
      if (!response.tailored_resume_text) {
        setError('Could not generate a tailored resume right now. Try again in a moment.')
        setPhase('idle')
        return
      }
      setResult(response)
      setPhase('done')
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to tailor your resume.')
      setPhase('idle')
    }
  }

  const handleCopy = () => {
    if (result?.tailored_resume_text) {
      navigator.clipboard.writeText(result.tailored_resume_text).catch(() => {})
    }
  }

  const handleDownload = () => {
    if (!result?.tailored_resume_text) return
    const blob = new Blob([result.tailored_resume_text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = 'tailored-resume.txt'
    link.click()
    URL.revokeObjectURL(url)
  }

  if (phase === 'done' && result) {
    return (
      <div className="space-y-3 border-t border-gray-200 pt-4 dark:border-gray-800">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold">Tailored resume</h4>
          <button
            type="button"
            onClick={() => {
              setResult(null)
              setPhase('idle')
            }}
            className="text-xs font-medium text-gray-500 hover:underline"
          >
            Start over
          </button>
        </div>

        {result.summary_of_changes.length > 0 && (
          <div>
            <p className="mb-1 text-xs font-medium text-gray-500 dark:text-gray-400">What changed</p>
            <ul className="list-inside list-disc text-xs text-gray-600 dark:text-gray-400">
              {result.summary_of_changes.map((change) => (
                <li key={change}>{change}</li>
              ))}
            </ul>
          </div>
        )}

        <pre className="max-h-96 overflow-y-auto whitespace-pre-wrap rounded-md border border-gray-200 bg-gray-50 p-3 text-xs text-gray-700 dark:border-gray-800 dark:bg-gray-950 dark:text-gray-300">
          {result.tailored_resume_text}
        </pre>

        <div className="flex gap-2">
          <button
            type="button"
            onClick={handleCopy}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
          >
            Copy
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium hover:bg-gray-50 dark:border-gray-700 dark:hover:bg-gray-800"
          >
            Download .txt
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="border-t border-gray-200 pt-4 dark:border-gray-800">
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <button
        type="button"
        disabled={phase === 'loading'}
        onClick={() => void handleTailor()}
        className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        Tailor my resume for this job
      </button>
      {phase === 'loading' && (
        <div className="mt-2">
          <LoadingSpinner label="Tailoring your resume…" />
        </div>
      )}
    </div>
  )
}
