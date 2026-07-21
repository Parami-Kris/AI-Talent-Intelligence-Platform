import { useEffect, useRef, useState } from 'react'
import { ApiError, detailMessage } from '../../api/client'
import { getParseUploadStatus, runPipeline, startParseUpload } from '../../api/endpoints'
import type { Candidate, Jd, PipelineRunResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { FileInput } from '../../components/FileInput'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { ParseFailuresList } from './components/ParseFailuresList'

interface UploadStepProps {
  onPipelineRun: (result: PipelineRunResponse) => void
}

type Phase = 'idle' | 'parsing' | 'running'

interface ParseProgress {
  processed: number
  total: number
  currentFilename: string | null
}

const POLL_INTERVAL_MS = 3000

function formatDuration(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  if (minutes === 0) return `${seconds}s`
  if (seconds === 0) return `${minutes}m`
  return `${minutes}m ${seconds}s`
}

export function UploadStep({ onPipelineRun }: UploadStepProps) {
  const [jdFile, setJdFile] = useState<File | null>(null)
  const [resumeFiles, setResumeFiles] = useState<File[]>([])
  const [runName, setRunName] = useState('')
  const [topN, setTopN] = useState(10)
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [failures, setFailures] = useState<{ filename: string; reason: string }[]>([])

  // Cached so a failure in the pipeline-run phase doesn't require re-uploading files.
  const [parsed, setParsed] = useState<{ jd: Jd; candidates: Candidate[] } | null>(null)

  const [parseProgress, setParseProgress] = useState<ParseProgress | null>(null)
  const pollTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    return () => {
      if (pollTimeoutRef.current) clearTimeout(pollTimeoutRef.current)
    }
  }, [])

  const pollParseJob = (jobId: string) =>
    new Promise<{ jd: Jd; candidates: Candidate[]; failures: { filename: string; reason: string }[] }>(
      (resolve, reject) => {
        const poll = async () => {
          let status
          try {
            status = await getParseUploadStatus(jobId)
          } catch (err) {
            reject(err)
            return
          }

          setParseProgress({
            processed: status.processed,
            total: status.total,
            currentFilename: status.current_filename,
          })

          if (status.status === 'done') {
            resolve({ jd: status.jd!, candidates: status.candidates!, failures: status.failures })
          } else if (status.status === 'error') {
            reject(new Error(status.error ?? 'Failed to parse the uploaded files.'))
          } else {
            pollTimeoutRef.current = setTimeout(poll, POLL_INTERVAL_MS)
          }
        }
        poll()
      },
    )

  const runFromParsed = async (jd: Jd, candidates: Candidate[]) => {
    setPhase('running')
    try {
      const result = await runPipeline({
        jd,
        candidates,
        run_name: runName || jd.job_title || 'Recruiter screening run',
        source_file: jdFile?.name ?? 'upload',
        top_n: topN,
      })
      onPipelineRun(result)
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to run the ranking pipeline.')
      setPhase('idle')
    }
  }

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)

    if (parsed) {
      // Retry path: files already parsed, just re-run the pipeline.
      await runFromParsed(parsed.jd, parsed.candidates)
      return
    }

    if (!jdFile || resumeFiles.length === 0) {
      setError('Select a job description file and at least one resume.')
      return
    }

    setPhase('parsing')
    setParseProgress({ processed: 0, total: resumeFiles.length, currentFilename: null })
    try {
      const { job_id, total } = await startParseUpload(jdFile, resumeFiles)
      setParseProgress({ processed: 0, total, currentFilename: null })
      const parsedResult = await pollParseJob(job_id)
      setFailures(parsedResult.failures)
      setParsed({ jd: parsedResult.jd, candidates: parsedResult.candidates })
      await runFromParsed(parsedResult.jd, parsedResult.candidates)
    } catch (err) {
      setError(
        err instanceof ApiError
          ? detailMessage(err.detail)
          : err instanceof Error
            ? err.message
            : 'Failed to parse the uploaded files.',
      )
      setPhase('idle')
    } finally {
      setParseProgress(null)
    }
  }

  const isBusy = phase !== 'idle'

  const [elapsedSeconds, setElapsedSeconds] = useState(0)

  useEffect(() => {
    if (!isBusy) {
      setElapsedSeconds(0)
      return
    }
    const startedAt = Date.now()
    const id = setInterval(() => setElapsedSeconds(Math.floor((Date.now() - startedAt) / 1000)), 1000)
    return () => clearInterval(id)
  }, [isBusy])

  const resumeCount = resumeFiles.length || 1
  const estimateLow = resumeCount * 8
  const estimateHigh = resumeCount * 15 + 10

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Start a screening run</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Upload a job description and a batch of resumes to rank candidates.
        </p>
      </div>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}
      <ParseFailuresList failures={failures} />

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="jd-file" className="block text-sm font-medium">
            Job description file
          </label>
          <FileInput
            id="jd-file"
            accept=".txt,.pdf,.docx"
            disabled={isBusy || !!parsed}
            value={jdFile ? [jdFile] : []}
            onChange={(files) => setJdFile(files[0] ?? null)}
          />
        </div>

        <div>
          <label htmlFor="resume-files" className="block text-sm font-medium">
            Resume files
          </label>
          <FileInput
            id="resume-files"
            accept=".txt,.pdf,.docx"
            multiple
            disabled={isBusy || !!parsed}
            value={resumeFiles}
            onChange={setResumeFiles}
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <label className="block text-sm font-medium">
            Run name (optional)
            <input
              type="text"
              value={runName}
              disabled={isBusy}
              onChange={(event) => setRunName(event.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
            />
          </label>
          <label className="block text-sm font-medium">
            Shortlist size (top N)
            <input
              type="number"
              min={1}
              value={topN}
              disabled={isBusy}
              onChange={(event) => setTopN(Number(event.target.value))}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
            />
          </label>
        </div>

        <button
          type="submit"
          disabled={isBusy}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {parsed ? 'Retry ranking' : 'Upload & rank candidates'}
        </button>

        {phase === 'parsing' && parseProgress && (
          <div className="space-y-2">
            <LoadingSpinner label="Parsing resumes…" />
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-200 dark:bg-gray-800">
              <div
                className="h-full rounded-full bg-indigo-600 transition-[width] duration-300 dark:bg-indigo-400"
                style={{
                  width: parseProgress.total
                    ? `${Math.round((parseProgress.processed / parseProgress.total) * 100)}%`
                    : '0%',
                }}
              />
            </div>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {parseProgress.processed} of {parseProgress.total} resume
              {parseProgress.total === 1 ? '' : 's'} parsed
              {parseProgress.currentFilename ? ` — currently: ${parseProgress.currentFilename}` : ''}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {formatDuration(elapsedSeconds)} elapsed
              {parseProgress.processed > 0
                ? ` — about ${formatDuration(
                    Math.round(
                      (elapsedSeconds / parseProgress.processed) * (parseProgress.total - parseProgress.processed),
                    ),
                  )} remaining (est.)`
                : ' — estimating time remaining…'}
            </p>
          </div>
        )}

        {phase === 'running' && (
          <div className="space-y-1">
            <LoadingSpinner label="Running ranking pipeline…" />
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {formatDuration(elapsedSeconds)} elapsed — usually takes about {formatDuration(estimateLow)}–
              {formatDuration(estimateHigh)} for {resumeCount} resume
              {resumeCount === 1 ? '' : 's'}.
            </p>
          </div>
        )}
      </form>
    </div>
  )
}
