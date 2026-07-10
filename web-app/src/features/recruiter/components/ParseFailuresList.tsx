interface ParseFailuresListProps {
  failures: { filename: string; reason: string }[]
}

export function ParseFailuresList({ failures }: ParseFailuresListProps) {
  if (failures.length === 0) return null

  return (
    <div className="rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300">
      <p className="font-medium">
        {failures.length} resume{failures.length > 1 ? 's' : ''} could not be parsed and will be skipped:
      </p>
      <ul className="mt-1 list-inside list-disc">
        {failures.map((failure) => (
          <li key={failure.filename}>
            {failure.filename}: {failure.reason}
          </li>
        ))}
      </ul>
    </div>
  )
}
