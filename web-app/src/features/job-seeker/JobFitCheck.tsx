import { useEffect, useState } from 'react'
import { ApiError, detailMessage } from '../../api/client'
import { analyzeProfileGap, getSavedResume, parseJdOnly, parseUpload } from '../../api/endpoints'
import type { Candidate, Jd, JobSearchResult, ProfileGapResponse } from '../../api/types'
import { useAuth } from '../../auth/AuthContext'
import { ErrorBanner } from '../../components/ErrorBanner'
import { FileInput } from '../../components/FileInput'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { ProfileGapResult } from './ProfileGapResult'
import { TailorResumePanel } from './TailorResumePanel'

interface JobFitCheckProps {
  job: JobSearchResult
}

type Phase = 'idle' | 'collecting' | 'parsing' | 'analyzing' | 'done'

function buildJdFile(job: JobSearchResult): File {
  return new File(
    [[job.title, job.company ? `at ${job.company}` : null, '', job.description].filter(Boolean).join('\n')],
    'job_description.txt',
    { type: 'text/plain' },
  )
}

export function JobFitCheck({ job }: JobFitCheckProps) {
  const { user } = useAuth()
  const isJobSeeker = user?.role === 'job_seeker'
  const [phase, setPhase] = useState<Phase>('idle')
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [savedResume, setSavedResume] = useState<Candidate | null>(null)
  const [useSavedResume, setUseSavedResume] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [result, setResult] = useState<ProfileGapResponse | null>(null)
  const [tailorContext, setTailorContext] = useState<{ jd: Jd; candidate: Candidate } | null>(null)

  const isBusy = phase === 'parsing' || phase === 'analyzing'

  useEffect(() => {
    if (!isJobSeeker) return
    let cancelled = false
    getSavedResume()
      .then((saved) => {
        if (cancelled || !saved.parsed_resume) return
        setSavedResume(saved.parsed_resume)
        setUseSavedResume(true)
      })
      .catch(() => {})
    return () => {
      cancelled = true
    }
  }, [isJobSeeker])

  const handleAnalyze = async () => {
    const reusingSavedResume = useSavedResume && !!savedResume
    if (!reusingSavedResume && !resumeFile) {
      setError('Upload your resume to check your fit for this job.')
      return
    }
    setError(null)
    setPhase('parsing')
    try {
      const jdFile = buildJdFile(job)

      let jd: Jd
      let candidate: Candidate
      if (reusingSavedResume) {
        jd = (await parseJdOnly(jdFile)).jd
        candidate = savedResume!
      } else {
        const parsed = await parseUpload(jdFile, [resumeFile!])
        if (parsed.candidates.length === 0) {
          setError('Could not parse your resume. Try a different file.')
          setPhase('collecting')
          return
        }
        jd = parsed.jd
        candidate = parsed.candidates[0]
      }

      setPhase('analyzing')
      const response = await analyzeProfileGap({
        jd,
        candidate,
        target_role: job.title ?? undefined,
      })
      setResult(response)
      setTailorContext({ jd, candidate })
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
            setTailorContext(null)
            setPhase('idle')
          }}
        />
        {tailorContext && (
          <div className="mt-6">
            <TailorResumePanel jd={tailorContext.jd} candidate={tailorContext.candidate} targetRole={job.title ?? undefined} />
          </div>
        )}
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
            {savedResume && useSavedResume ? (
              <div className="mt-1 flex items-center justify-between gap-3 rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800">
                <span>Using your saved resume</span>
                <button
                  type="button"
                  disabled={isBusy}
                  onClick={() => setUseSavedResume(false)}
                  className="shrink-0 text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  Upload a different one
                </button>
              </div>
            ) : (
              <>
                <FileInput
                  id="fit-check-resume"
                  accept=".txt,.pdf,.docx"
                  disabled={isBusy}
                  value={resumeFile ? [resumeFile] : []}
                  onChange={(files) => setResumeFile(files[0] ?? null)}
                />
                {savedResume && (
                  <button
                    type="button"
                    disabled={isBusy}
                    onClick={() => setUseSavedResume(true)}
                    className="mt-1 text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                  >
                    Use saved resume instead
                  </button>
                )}
              </>
            )}
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
