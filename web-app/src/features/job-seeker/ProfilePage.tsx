import { useEffect, useState } from 'react'
import { ApiError, detailMessage } from '../../api/client'
import { getSavedResume, parseResumeOnly, saveResume } from '../../api/endpoints'
import type { Candidate } from '../../api/types'
import { ErrorBanner } from '../../components/ErrorBanner'
import { FileInput } from '../../components/FileInput'
import { LoadingSpinner } from '../../components/LoadingSpinner'

type Phase = 'idle' | 'parsing' | 'saving'

export function ProfilePage() {
  const [loading, setLoading] = useState(true)
  const [savedCandidate, setSavedCandidate] = useState<Candidate | null>(null)
  const [savedFilename, setSavedFilename] = useState<string | null>(null)
  const [updatedAt, setUpdatedAt] = useState<string | null>(null)
  const [resumeFile, setResumeFile] = useState<File | null>(null)
  const [phase, setPhase] = useState<Phase>('idle')
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  useEffect(() => {
    getSavedResume()
      .then((saved) => {
        if (saved.parsed_resume) {
          setSavedCandidate(saved.parsed_resume)
          setSavedFilename(saved.resume_filename ?? null)
          setUpdatedAt(saved.updated_at ?? null)
        }
      })
      .catch(() => {})
      .finally(() => setLoading(false))
  }, [])

  const handleSave = async () => {
    if (!resumeFile) {
      setError('Choose a resume file first.')
      return
    }
    setError(null)
    setSuccessMessage(null)
    setPhase('parsing')
    try {
      const { candidate } = await parseResumeOnly(resumeFile)
      setPhase('saving')
      await saveResume({ resume_filename: resumeFile.name, parsed_resume: candidate })
      setSavedCandidate(candidate)
      setSavedFilename(resumeFile.name)
      setUpdatedAt(new Date().toISOString())
      setResumeFile(null)
      setSuccessMessage('Resume saved.')
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to save your resume.')
    } finally {
      setPhase('idle')
    }
  }

  const isBusy = phase !== 'idle'

  if (loading) {
    return <LoadingSpinner label="Loading your profile…" />
  }

  return (
    <div className="mx-auto max-w-xl space-y-6">
      <div>
        <h2 className="text-xl font-semibold">Profile</h2>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          Save a resume here once, then reuse it across the fit checker, job matches, and resume tailoring instead
          of re-uploading it every time.
        </p>
      </div>

      {savedCandidate ? (
        <div className="rounded-md border border-gray-200 bg-white p-4 dark:border-gray-800 dark:bg-gray-900">
          <p className="text-sm font-medium">Currently saved: {savedFilename ?? 'your resume'}</p>
          {savedCandidate.name && (
            <p className="text-xs text-gray-500 dark:text-gray-400">Parsed as: {savedCandidate.name}</p>
          )}
          {updatedAt && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Last updated {new Date(updatedAt).toLocaleString()}
            </p>
          )}
        </div>
      ) : (
        <p className="text-sm text-gray-600 dark:text-gray-400">No resume saved yet.</p>
      )}

      {successMessage && (
        <div className="rounded-md border border-green-300 bg-green-50 px-4 py-3 text-sm text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300">
          {successMessage}
        </div>
      )}
      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <div className="space-y-3">
        <label htmlFor="profile-resume-file" className="block text-sm font-medium">
          {savedCandidate ? 'Replace your resume' : 'Upload your resume'}
        </label>
        <FileInput
          id="profile-resume-file"
          accept=".txt,.pdf,.docx"
          disabled={isBusy}
          value={resumeFile ? [resumeFile] : []}
          onChange={(files) => setResumeFile(files[0] ?? null)}
        />
        <button
          type="button"
          disabled={isBusy || !resumeFile}
          onClick={() => void handleSave()}
          className="w-full rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Save resume
        </button>
        {isBusy && <LoadingSpinner label={phase === 'parsing' ? 'Parsing your resume…' : 'Saving…'} />}
      </div>
    </div>
  )
}
