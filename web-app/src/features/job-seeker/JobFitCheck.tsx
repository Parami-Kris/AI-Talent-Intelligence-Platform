import { useState } from 'react'
import { ApiError, detailMessage } from '../../api/client'
import { analyzeProfileGap, parseUpload } from '../../api/endpoints'
import type { JobSearchResult, ProfileGapResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { FileInput } from '../../components/FileInput'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { ProfileGapResult } from './ProfileGapResult'

interface JobFitCheckProps {
  job: JobSearchResult
}

type Phase = 'idle' | 'collecting' | 'parsing' | 'analyzing' | 'done'

export function JobFitCheck({ job }: JobFitCheckProps) {
  const [phase, setPhase] = useState<Phase>('idle')
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ProfileGapResponse | null>(null)

  const isBusy = phase === 'parsing' || phase === 'analyzing'

  const handleAnalyze = async () => {
    if (!resumeFile) {
      setError('Upload your resume to check your fit for this job.')
      return
    }
    setError(null)
    setPhase('parsing')
    try {
      const jdFile = new File(
        [[job.title, job.company ? `at ${job.company}` : null, '', job.description].filter(Boolean).join('\n')],
        'job_description.txt',
        { type: 'text/plain' },
      )
      const parsed = await parseUpload(jdFile, [resumeFile])
      if (parsed.candidates.length === 0) {
        setError('Could not parse your resume. Try a different file.')
        setPhase('collecting')
        return
      }

      setPhase('analyzing')
      const response = await analyzeProfileGap({
        jd: parsed.jd,
        candidate: parsed.candidates[0],
        target_role: job.title ?? undefined,
      })
      setResult(response)
      setPhase('done')
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to analyze your profile.')
      setPhase('collecting')
    }
  }

  if (phase === 'done' && result) {
    return (
      <div className="border-t border-gray-200 pt-6 dark:border-gray-800">
        <ProfileGapResult
          result={result}
          onStartOver={() => {
            setResult(null)
            setPhase('idle')
          }}
        />
      </div>
    )
  }

  return (
    <div className="border-t border-gray-200 pt-6 dark:border-gray-800">
      {phase === 'idle' ? (
        <button
          type="button"
          onClick={() => setPhase('collecting')}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Analyze your fit for this job
        </button>
      ) : (
        <div className="space-y-3">
          <div>
            <label htmlFor="fit-check-resume" className="block text-sm font-medium">
              Your resume
            </label>
            <FileInput
              id="fit-check-resume"
              accept=".txt,.pdf,.docx"
              disabled={isBusy}
              value={resumeFile ? [resumeFile] : []}
              onChange={(files) => setResumeFile(files[0] ?? null)}
            />
          </div>

          {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

          <button
            type="button"
            disabled={isBusy}
            onClick={() => void handleAnalyze()}
            className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Analyze my fit
          </button>

          {isBusy && (
            <LoadingSpinner label={phase === 'parsing' ? 'Parsing your resume…' : 'Analyzing qualification gaps…'} />
          )}
        </div>
      )}
    </div>
  )
}
