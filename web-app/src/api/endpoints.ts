import { getJson, postForm, postJson } from './client'
import type {
  Candidate,
  Jd,
  JobEventRequest,
  JobSearchResponse,
  ManualAddition,
  MyJobsResponse,
  ParseUploadJobResponse,
  ParseUploadResponse,
  ParseUploadStatusResponse,
  PipelineResumeResponse,
  PipelineRunResponse,
  ProfileGapRequest,
  ProfileGapResponse,
} from './types'

export function parseUpload(jdFile: File, resumeFiles: File[]): Promise<ParseUploadResponse> {
  const form = new FormData()
  form.append('jd_file', jdFile)
  resumeFiles.forEach((file) => form.append('resume_files', file))
  return postForm<ParseUploadResponse>('/upload/parse', form)
}

export function startParseUpload(jdFile: File, resumeFiles: File[]): Promise<ParseUploadJobResponse> {
  const form = new FormData()
  form.append('jd_file', jdFile)
  resumeFiles.forEach((file) => form.append('resume_files', file))
  return postForm<ParseUploadJobResponse>('/upload/parse/start', form)
}

export function getParseUploadStatus(jobId: string): Promise<ParseUploadStatusResponse> {
  return getJson<ParseUploadStatusResponse>(`/upload/parse/status/${jobId}`)
}

export interface RunPipelinePayload {
  jd: Jd
  candidates: Candidate[]
  run_name: string
  source_file: string
  top_n: number
}

export function runPipeline(payload: RunPipelinePayload): Promise<PipelineRunResponse> {
  return postJson<PipelineRunResponse>('/pipeline/run', payload)
}

export interface ResumePipelinePayload {
  thread_id: string
  action: 'approve' | 'edit' | 'reject'
  manual_additions?: ManualAddition[]
}

export function resumePipeline(payload: ResumePipelinePayload): Promise<PipelineResumeResponse> {
  return postJson<PipelineResumeResponse>('/pipeline/resume', payload)
}

export function analyzeProfileGap(payload: ProfileGapRequest): Promise<ProfileGapResponse> {
  return postJson<ProfileGapResponse>('/analyze-profile-gap', payload)
}

export function searchJobs(
  query: string,
  location?: string,
  country = 'us',
  signal?: AbortSignal,
  candidateId?: string,
): Promise<JobSearchResponse> {
  return getJson<JobSearchResponse>('/jobs/search', { query, location, country, candidate_id: candidateId }, signal)
}

export function logJobEvent(payload: JobEventRequest): Promise<void> {
  return postJson<unknown>('/jobs/events', payload).then(() => undefined)
}

export function getMyJobs(candidateId: string): Promise<MyJobsResponse> {
  return getJson<MyJobsResponse>('/jobs/my-jobs', { candidate_id: candidateId })
}
