export interface Jd {
  job_title?: string | null
  required_skills?: string[]
  preferred_skills?: string[]
  experience_required?: string
  education_required?: string
  responsibilities?: string[]
  [key: string]: unknown
}

export interface Candidate {
  name?: string
  email?: string | null
  normalized_skills?: string[]
  experience?: unknown[]
  education?: unknown[]
  [key: string]: unknown
}

export interface ParseUploadResponse {
  jd: Jd
  candidates: Candidate[]
  failures: { filename: string; reason: string }[]
}

export interface ParseUploadJobResponse {
  job_id: string
  total: number
}

export interface ParseUploadStatusResponse {
  status: 'running' | 'done' | 'error'
  total: number
  processed: number
  current_filename: string | null
  failures: { filename: string; reason: string }[]
  error?: string | null
  jd?: Jd | null
  candidates?: Candidate[] | null
}

export interface ScoreDetail {
  score: number | null
  matched?: string[]
  missing?: string[]
  evidence?: string[]
  [key: string]: unknown
}

export interface ExperienceRelevance {
  experience_relevance_score: number | null
  seniority_fit?: string | null
  domain_fit?: string | null
  reason?: string
  matched?: string[]
  missing?: string[]
  evidence?: string[]
}

export type JobStabilityFlag = 'stable' | 'frequent_job_changes' | 'insufficient_data'

export interface JobStability {
  job_count: number
  average_tenure_years: number | null
  short_stints_count: number
  flag: JobStabilityFlag
}

export interface CandidateResult {
  candidate_name: string
  email?: string | null
  is_eligible: boolean
  overall_score: number
  eligibility?: {
    meets_experience: boolean
    missing_must_haves: string[]
  }
  match_scores?: {
    skills?: ScoreDetail
    experience?: ScoreDetail
    education?: ScoreDetail
  }
  education_summary?: string[]
  raw_text?: string | null
  rank?: number
  final_rank?: number
  final_score?: number
  experience_relevance?: ExperienceRelevance | null
  job_stability?: JobStability | null
  manually_added?: boolean
  override_reason?: string
  added_by?: string | null
  [key: string]: unknown
}

export interface CandidateSummary {
  rank?: number
  final_rank?: number
  candidate_name: string
  is_eligible: boolean
  overall_score?: number
  final_score?: number
  skill_score?: number
  experience_score?: number
  meets_experience?: boolean
  missing_must_haves_count?: number
  top_missing_must_haves?: string[]
  experience_relevance_score?: number | null
  seniority_fit?: string | null
  domain_fit?: string | null
  job_stability_flag?: JobStabilityFlag | null
  average_tenure_years?: number | null
  short_stints_count?: number
  [key: string]: unknown
}

export interface BatchRankingResult {
  job_title: string | null
  ranking_rule: string
  summary: CandidateSummary[]
  results: CandidateResult[]
}

export interface ReviewPayload {
  type: string
  job_title: string | null
  shortlist_size: number
  shortlist: CandidateSummary[]
  other_candidates: CandidateSummary[]
  used_relative_fallback?: boolean
  message: string
}

export interface PipelineRunResponse {
  thread_id: string
  status: 'awaiting_review' | 'no_eligible_candidates'
  batch_ranking: BatchRankingResult | null
  review_payload: ReviewPayload | null
}

export interface ManualAddition {
  candidate_name: string
  override_reason: string
  added_by?: string | null
}

export interface RerankedResult {
  job_title: string | null
  ranking_rule: string
  shortlist_size: number
  summary: CandidateSummary[]
  results: CandidateResult[]
}

export interface PersistenceResult {
  run_id: number
  saved_rankings: number
}

export interface PipelineResumeResponse {
  thread_id: string
  status: 'persisted' | 'rejected'
  reranked: RerankedResult | null
  persistence_result: PersistenceResult | null
}

export type PipelineAction = 'approve' | 'edit' | 'reject'

export interface ProfileGapRequest {
  jd: Jd
  candidate: Candidate
  target_role?: string | null
}

export interface QualificationGaps {
  missing_required_skills: string[]
  missing_experience_signals: string[]
  matched_skills: string[]
}

export interface RecommendedActions {
  suggested_projects: string[]
  resume_improvements: string[]
  learning_focus: string[]
}

export interface ProfileGapEvidence {
  skills: string[]
  experience: string[]
}

export interface JobSearchResult {
  source: string
  id: string
  title: string | null
  company: string | null
  location: string | null
  description: string | null
  url: string | null
  posted_at: string | null
}

export interface JobSearchResponse {
  count: number
  results: JobSearchResult[]
  expanded_titles: string[]
  used_query: string
  recommended: boolean
}

export type JobEventType = 'viewed' | 'applied' | 'liked'

export interface JobEventRequest {
  candidate_id: string
  event_type: JobEventType
  job_source?: string | null
  job_external_id?: string | null
  job_title?: string | null
  company?: string | null
  location?: string | null
}

export interface ProfileGapResponse {
  target_role: string | null
  candidate_name: string
  current_fit: 'strong' | 'partial' | 'weak'
  role_readiness_score: number | null
  eligibility: {
    meets_experience: boolean
    missing_must_haves: string[]
    [key: string]: unknown
  }
  qualification_gaps: QualificationGaps
  recommended_actions: RecommendedActions
  evidence: ProfileGapEvidence
}
