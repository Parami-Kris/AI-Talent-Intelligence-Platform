import { useState, type ReactNode } from 'react'
import type { CandidateSummary } from '../../../api/types'
import { CandidateCard } from './CandidateCard'
import { CandidateTable, type CandidateTableColumn } from './CandidateTable'

interface CandidateResultsViewProps {
  rows: CandidateSummary[]
  extraColumns?: CandidateTableColumn[]
  onRowClick?: (row: CandidateSummary) => void
  rowActions?: (row: CandidateSummary) => ReactNode
  emptyMessage?: string
}

function toggleButtonClass(active: boolean) {
  return `rounded-md px-2 py-1 text-xs font-medium ${
    active
      ? 'bg-indigo-600 text-white'
      : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-400 dark:hover:bg-gray-700'
  }`
}

export function CandidateResultsView({
  rows,
  extraColumns,
  onRowClick,
  rowActions,
  emptyMessage = 'No candidates.',
}: CandidateResultsViewProps) {
  const [view, setView] = useState<'cards' | 'table'>('cards')

  if (rows.length === 0) {
    return <p className="text-sm text-gray-500 dark:text-gray-400">{emptyMessage}</p>
  }

  return (
    <div className="space-y-3">
      <div className="flex justify-end gap-1">
        <button type="button" onClick={() => setView('cards')} className={toggleButtonClass(view === 'cards')}>
          Cards
        </button>
        <button type="button" onClick={() => setView('table')} className={toggleButtonClass(view === 'table')}>
          Table
        </button>
      </div>

      {view === 'table' ? (
        <CandidateTable
          rows={rows}
          extraColumns={extraColumns}
          onRowClick={onRowClick}
          rowActions={rowActions}
          emptyMessage={emptyMessage}
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((row) => (
            <CandidateCard key={row.candidate_name} row={row} onClick={onRowClick} actions={rowActions?.(row)} />
          ))}
        </div>
      )}
    </div>
  )
}
