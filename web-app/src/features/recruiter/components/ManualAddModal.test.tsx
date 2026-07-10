import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ManualAddModal } from './ManualAddModal'

const candidate = { candidate_name: 'Alice', is_eligible: false }

describe('ManualAddModal', () => {
  it('keeps the submit button disabled until a reason is entered', async () => {
    const onConfirm = vi.fn()
    render(<ManualAddModal candidate={candidate} pending={[]} onConfirm={onConfirm} onCancel={vi.fn()} />)

    const submitButton = screen.getByRole('button', { name: /add to pending list/i })
    expect(submitButton).toBeDisabled()

    await userEvent.type(screen.getByLabelText(/reason/i), 'Exceptional in interview')
    expect(submitButton).toBeEnabled()
  })

  it('calls onConfirm with the trimmed reason on submit', async () => {
    const onConfirm = vi.fn()
    render(<ManualAddModal candidate={candidate} pending={[]} onConfirm={onConfirm} onCancel={vi.fn()} />)

    await userEvent.type(screen.getByLabelText(/reason/i), '  Great interview  ')
    await userEvent.click(screen.getByRole('button', { name: /add to pending list/i }))

    expect(onConfirm).toHaveBeenCalledWith({
      candidate_name: 'Alice',
      override_reason: 'Great interview',
      added_by: undefined,
    })
  })
})
