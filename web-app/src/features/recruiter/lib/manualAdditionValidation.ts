import type { ManualAddition } from '../../../api/types'

export interface ValidationResult {
  valid: boolean
  error?: string
}

export function validateManualAddition(
  candidateName: string,
  overrideReason: string,
  pending: ManualAddition[],
): ValidationResult {
  if (!overrideReason.trim()) {
    return { valid: false, error: 'A reason is required to add this candidate.' }
  }
  if (pending.some((addition) => addition.candidate_name === candidateName)) {
    return { valid: false, error: `${candidateName} is already in the pending list.` }
  }
  return { valid: true }
}
