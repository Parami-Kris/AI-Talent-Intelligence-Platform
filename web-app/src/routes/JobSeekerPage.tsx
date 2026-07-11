import { useState } from 'react'
import type { ProfileGapResponse } from '../api/types'
import { ProfileGapForm } from '../features/job-seeker/ProfileGapForm'
import { ProfileGapResult } from '../features/job-seeker/ProfileGapResult'

export function JobSeekerPage() {
  const [result, setResult] = useState<ProfileGapResponse | null>(null)

  return result ? (
    <ProfileGapResult result={result} onStartOver={() => setResult(null)} />
  ) : (
    <ProfileGapForm onResult={setResult} />
  )
}
