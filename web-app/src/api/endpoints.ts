import { deleteJson, getJson, patchJson, postForm, postJson, putJson } from './client'
import type {
  Candidate,
  CandidateComment,
  CommentListResponse,
  Jd,
  JobEventRequest,
  JobEventType,
  JobMatchesResponse,
  JobSearchResponse,
  LoginPayload,
  ManualAddition,
  MyJobsResponse,
  ParseUploadJobResponse,
  ParseUploadResponse,
  ParseUploadStatusResponse,
  PipelineResumeResponse,
  PipelineRunResponse,
  ProfileGapRequest,
  ProfileGapResponse,
  RegisterPayload,
  RunDetail,
  RunListResponse,
  SavedResumeResponse,
  SaveResumePayload,
  TailorResumePayload,
  TailorResumeResponse,
  TokenResponse,
  User,
} from './types'

export function login(payload: LoginPayload): Promise<TokenResponse> {
  return postJson<TokenResponse>('/auth/login', payload)
}

export function register(payload: RegisterPayload): Promise<TokenResponse> {
  return postJson<TokenResponse>('/auth/register', payload)
}

export function getMe(): Promise<User> {
  return getJson<User>('/auth/me')
}

export function listRuns(): Promise<RunListResponse> {
  return getJson<RunListResponse>('/runs')
}

export function getRun(runId: number): Promise<RunDetail> {
  return getJson<RunDetail>(`/runs/${runId}`)
}

export function setCandidateShortlisted(runId: number, candidateId: number, isShortlisted: boolean): Promise<unknown> {
  return patchJson(`/runs/${runId}/candidates/${candidateId}/shortlist`, { is_shortlisted: isShortlisted })
}

export function getCandidateComments(candidateId: number): Promise<CommentListResponse> {
  return getJson<CommentListResponse>(`/candidates/${candidateId}/comments`)
}

export function addCandidateComment(
  candidateId: number,
  commentText: string,
  isCaution: boolean,
): Promise<CandidateComment> {
  return postJson<CandidateComment>(`/candidates/${candidateId}/comments`, {
    comment_text: commentText,
    is_caution: isCaution,
  })
}

export function getSavedResume(): Promise<SavedResumeResponse> {
  return getJson<SavedResumeResponse>('/job-seeker/resume')
}

export function saveResume(payload: SaveResumePayload): Promise<SavedResumeResponse> {
  return putJson<SavedResumeResponse>('/job-seeker/resume', payload)
}

export function parseJdOnly(jdFile: File): Promise<{ jd: Jd }> {
  const form = new FormData()
  form.append('jd_file', jdFile)
  return postForm<{ jd: Jd }>('/upload/parse-jd', form)
}

export function parseResumeOnly(resumeFile: File): Promise<{ candidate: Candidate }> {
  const form = new FormData()
  form.append('resume_file', resumeFile)
  return postForm<{ candidate: Candidate }>('/upload/parse-resume', form)
}

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

export function tailorResume(payload: TailorResumePayload): Promise<TailorResumeResponse> {
  return postJson<TailorResumeResponse>('/tailor-resume', payload)
}

export function getJobMatches(
  query: string,
  location?: string,
  country = 'us',
  topN = 10,
): Promise<JobMatchesResponse> {
  return getJson<JobMatchesResponse>('/job-seeker/matches', {
    query,
    location,
    country,
    top_n: topN,
  })
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

export function clearJobHistory(candidateId: string, eventType: JobEventType): Promise<void> {
  return deleteJson<unknown>('/jobs/events', { candidate_id: candidateId, event_type: eventType }).then(
    () => undefined,
  )
}
