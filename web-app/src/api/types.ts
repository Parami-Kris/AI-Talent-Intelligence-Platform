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
  rank?: number
  final_rank?: number
  final_score?: number
  experience_relevance?: ExperienceRelevance | null
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
