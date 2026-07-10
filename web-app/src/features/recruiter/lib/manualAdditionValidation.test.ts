import { describe, expect, it } from 'vitest'
import type { ManualAddition } from '../../../api/types'
import { validateManualAddition } from './manualAdditionValidation'

describe('validateManualAddition', () => {
  it('rejects an empty reason', () => {
    const result = validateManualAddition('Alice', '', [])
    expect(result.valid).toBe(false)
  })

  it('rejects a whitespace-only reason', () => {
    const result = validateManualAddition('Alice', '   ', [])
    expect(result.valid).toBe(false)
  })

  it('rejects a duplicate candidate already pending', () => {
    const pending: ManualAddition[] = [{ candidate_name: 'Alice', override_reason: 'Great interview' }]
    const result = validateManualAddition('Alice', 'Another reason', pending)
    expect(result.valid).toBe(false)
  })

  it('accepts a valid, non-duplicate addition', () => {
    const result = validateManualAddition('Bob', 'Strong technical interview', [])
    expect(result.valid).toBe(true)
    expect(result.error).toBeUndefined()
  })
})
