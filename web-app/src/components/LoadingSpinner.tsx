export function LoadingSpinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-indigo-600 dark:border-gray-600 dark:border-t-indigo-400" />
      {label && <span>{label}</span>}
    </div>
  )
}
