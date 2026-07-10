interface ActionBarProps {
  pendingCount: number
  isSubmitting: boolean
  onApprove: () => void
  onReject: () => void
}

export function ActionBar({ pendingCount, isSubmitting, onApprove, onReject }: ActionBarProps) {
  const handleReject = () => {
    if (window.confirm('Discard this screening run? This cannot be undone.')) {
      onReject()
    }
  }

  return (
    <div className="flex items-center justify-end gap-3 border-t border-gray-200 pt-4 dark:border-gray-800">
      <button
        type="button"
        onClick={handleReject}
        disabled={isSubmitting}
        className="rounded-md px-4 py-2 text-sm font-medium text-red-600 hover:bg-red-50 disabled:opacity-50 dark:hover:bg-red-950/40"
      >
        Reject
      </button>
      <button
        type="button"
        onClick={onApprove}
        disabled={isSubmitting}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isSubmitting ? 'Saving…' : pendingCount > 0 ? `Save & Persist (${pendingCount} manual add${pendingCount > 1 ? 's' : ''})` : 'Approve'}
      </button>
    </div>
  )
}
