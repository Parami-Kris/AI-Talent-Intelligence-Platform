export function CautionBadge({ reason }: { reason: string | null | undefined }) {
  return (
    <span
      title={reason ?? 'A recruiter flagged a concern about this candidate in an earlier screening.'}
      className="inline-flex items-center rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-800 dark:bg-red-900/40 dark:text-red-300"
    >
      ⚠ Recruiter caution
    </span>
  )
}
