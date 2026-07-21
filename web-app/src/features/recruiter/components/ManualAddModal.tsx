import { useState } from 'react'
import type { CandidateSummary, ManualAddition } from '../../../api/types'
import { useEscapeKey } from '../../../lib/useEscapeKey'
import { validateManualAddition } from '../lib/manualAdditionValidation'

interface ManualAddModalProps {
  candidate: CandidateSummary
  pending: ManualAddition[]
  onConfirm: (addition: ManualAddition) => void
  onCancel: () => void
}

export function ManualAddModal({ candidate, pending, onConfirm, onCancel }: ManualAddModalProps) {
  const [overrideReason, setOverrideReason] = useState('')
  const [addedBy, setAddedBy] = useState('')
  const [error, setError] = useState<string | undefined>()

  useEscapeKey(onCancel)

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const result = validateManualAddition(candidate.candidate_name, overrideReason, pending)
    if (!result.valid) {
      setError(result.error)
      return
    }
    onConfirm({
      candidate_name: candidate.candidate_name,
      override_reason: overrideReason.trim(),
      added_by: addedBy.trim() || undefined,
    })
  }

  return (
    <div
      className="fixed inset-0 z-30 flex items-center justify-center bg-black/30"
      onClick={onCancel}
      role="presentation"
    >
      <form
        onSubmit={handleSubmit}
        onClick={(event) => event.stopPropagation()}
        className="w-full max-w-md space-y-4 rounded-md bg-white p-6 shadow-xl dark:bg-gray-900"
        role="dialog"
        aria-modal="true"
        aria-labelledby="manual-add-modal-title"
      >
        <h3 id="manual-add-modal-title" className="text-lg font-semibold">
          Add {candidate.candidate_name} to shortlist
        </h3>
        <p className="text-sm text-gray-600 dark:text-gray-400">
          This candidate wasn't LLM-shortlisted. Provide a reason (e.g. strong interview performance) so
          the override is evidence-backed.
        </p>

        <label className="block text-sm font-medium">
          Reason <span className="text-red-600">*</span>
          <textarea
            required
            value={overrideReason}
            onChange={(event) => setOverrideReason(event.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
            rows={3}
          />
        </label>

        <label className="block text-sm font-medium">
          Added by (optional)
          <input
            type="text"
            value={addedBy}
            onChange={(event) => setAddedBy(event.target.value)}
            className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
          />
        </label>

        {error && <p className="text-sm text-red-600">{error}</p>}

        <div className="flex justify-end gap-3">
          <button
            type="button"
            onClick={onCancel}
            className="rounded-md px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 dark:text-gray-400 dark:hover:bg-gray-800"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!overrideReason.trim()}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Add to pending list
          </button>
        </div>
      </form>
    </div>
  )
}
