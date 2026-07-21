import type { ReactNode } from 'react'
import type { CandidateSummary } from '../../../api/types'
import { EligibilityBadge } from './EligibilityBadge'

export interface CandidateTableColumn {
  header: string
  render: (row: CandidateSummary) => ReactNode
}

interface CandidateTableProps {
  rows: CandidateSummary[]
  extraColumns?: CandidateTableColumn[]
  onRowClick?: (row: CandidateSummary) => void
  rowActions?: (row: CandidateSummary) => ReactNode
  emptyMessage?: string
  compareSelected?: Set<string>
  onToggleCompare?: (row: CandidateSummary) => void
}

export function CandidateTable({
  rows,
  extraColumns = [],
  onRowClick,
  rowActions,
  emptyMessage = 'No candidates.',
  compareSelected,
  onToggleCompare,
}: CandidateTableProps) {
  if (rows.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">{emptyMessage}</p>
  }

  return (
    <div className="overflow-x-auto rounded-md border border-gray-200 dark:border-gray-800">
      <table className="min-w-full divide-y divide-gray-200 text-sm dark:divide-gray-800">
        <thead className="bg-gray-50 dark:bg-gray-900">
          <tr>
            {onToggleCompare && <th className="px-3 py-2" />}
            <th className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-400">Candidate</th>
            <th className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-400">Eligibility</th>
            <th className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-400">Score</th>
            {extraColumns.map((col) => (
              <th key={col.header} className="px-3 py-2 text-left font-medium text-gray-600 dark:text-gray-400">
                {col.header}
              </th>
            ))}
            {rowActions && <th className="px-3 py-2" />}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 dark:divide-gray-800">
          {rows.map((row) => (
            <tr
              key={row.candidate_name}
              className={onRowClick ? 'cursor-pointer hover:bg-gray-50 dark:hover:bg-gray-900' : ''}
              onClick={() => onRowClick?.(row)}
            >
              {onToggleCompare && (
                <td className="px-3 py-2" onClick={(event) => event.stopPropagation()}>
                  <input
                    type="checkbox"
                    checked={!!compareSelected?.has(row.candidate_name)}
                    onChange={() => onToggleCompare(row)}
                    title="Select for comparison"
                    className="h-4 w-4 accent-indigo-600"
                  />
                </td>
              )}
              <td className="px-3 py-2 font-medium">{row.candidate_name}</td>
              <td className="px-3 py-2">
                <EligibilityBadge isEligible={row.is_eligible} />
              </td>
              <td className="px-3 py-2">{row.final_score ?? row.overall_score ?? '—'}</td>
              {extraColumns.map((col) => (
                <td key={col.header} className="px-3 py-2">
                  {col.render(row)}
                </td>
              ))}
              {rowActions && (
                <td className="px-3 py-2 text-right" onClick={(event) => event.stopPropagation()}>
                  {rowActions(row)}
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
