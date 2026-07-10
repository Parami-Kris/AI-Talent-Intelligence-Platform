import { describe, expect, it } from 'vitest'
import type { CandidateResult, CandidateSummary } from '../../../api/types'
import { joinCandidateDetail } from './joinCandidateDetail'

const fullResults: CandidateResult[] = [
  { candidate_name: 'Alice', is_eligible: true, overall_score: 90 },
  { candidate_name: 'Bob', is_eligible: false, overall_score: 60 },
]

describe('joinCandidateDetail', () => {
  it('finds the matching full record by candidate_name', () => {
    const summary: CandidateSummary = { candidate_name: 'Alice', is_eligible: true }
    expect(joinCandidateDetail(summary, fullResults)).toEqual(fullResults[0])
  })

  it('returns undefined when no matching record exists', () => {
    const summary: CandidateSummary = { candidate_name: 'Carol', is_eligible: true }
    expect(joinCandidateDetail(summary, fullResults)).toBeUndefined()
  })
})
