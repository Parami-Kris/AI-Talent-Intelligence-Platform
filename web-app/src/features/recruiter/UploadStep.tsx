import { useState } from 'react'
import { ApiError, detailMessage } from '../../api/client'
import { parseUpload, runPipeline } from '../../api/endpoints'
import type { Candidate, Jd, PipelineRunResponse } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { FileInput } from '../../components/FileInput'
import { LoadingSpinner } from '../../components/LoadingSpinner'
import { ParseFailuresList } from './components/ParseFailuresList'

interface UploadStepProps {
  onPipelineRun: (result: PipelineRunResponse) => void
}

type Phase = 'idle' | 'parsing' | 'running'

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
    try {
      const parsedResult = await parseUpload(jdFile, resumeFiles)
      setFailures(parsedResult.failures)
      setParsed({ jd: parsedResult.jd, candidates: parsedResult.candidates })
      await runFromParsed(parsedResult.jd, parsedResult.candidates)
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to parse the uploaded files.')
      setPhase('idle')
    }
  }

  const isBusy = phase !== 'idle'

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

        {isBusy && (
          <LoadingSpinner label={phase === 'parsing' ? 'Parsing files…' : 'Running ranking pipeline…'} />
        )}
      </form>
    </div>
  )
}
