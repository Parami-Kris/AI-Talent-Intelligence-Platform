import type { CandidateResult, CandidateSummary } from '../../../api/types'

export function joinCandidateDetail(
  summaryRow: CandidateSummary,
  fullResults: CandidateResult[],
): CandidateResult | undefined {
  return fullResults.find((result) => result.candidate_name === summaryRow.candidate_name)
}
