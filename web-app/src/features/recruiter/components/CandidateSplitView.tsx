import { useMemo, useState, type ReactNode } from 'react'
import type { CandidateResult, CandidateSummary } from '../../../api/types'
import { exportCandidatesToCsv } from '../lib/csvExport'
import { CandidateComparisonPanel } from './CandidateComparisonPanel'
import { CandidateDetailPanel } from './CandidateDetailPanel'
import { CandidateListRow } from './CandidateListRow'
import { CandidateResultsView } from './CandidateResultsView'
import type { CandidateTableColumn } from './CandidateTable'

export interface CandidateGroup {
  title: string
  rows: CandidateSummary[]
  extraColumns?: CandidateTableColumn[]
  rowActions?: (row: CandidateSummary) => ReactNode
  emptyMessage?: string
}

interface CandidateSplitViewProps {
  groups: CandidateGroup[]
  fullResults: CandidateResult[]
}

function csvFilename(title: string): string {
  return `${title.replace(/[^a-z0-9]+/gi, '-').toLowerCase().replace(/^-+|-+$/g, '')}.csv`
}

export function CandidateSplitView({ groups, fullResults }: CandidateSplitViewProps) {
  const [selected, setSelected] = useState<CandidateSummary | null>(null)
  const [compareSelected, setCompareSelected] = useState<Set<string>>(new Set())
  const [showComparison, setShowComparison] = useState(false)

  const allRows = useMemo(() => groups.flatMap((group) => group.rows), [groups])
  const compareRows = allRows.filter((row) => compareSelected.has(row.candidate_name))

  const toggleCompare = (row: CandidateSummary) => {
    setCompareSelected((prev) => {
      const next = new Set(prev)
      if (next.has(row.candidate_name)) {
        next.delete(row.candidate_name)
      } else {
        next.add(row.candidate_name)
      }
      return next
    })
  }

  const removeFromCompare = (candidateName: string) => {
    setCompareSelected((prev) => {
      const next = new Set(prev)
      next.delete(candidateName)
      if (next.size < 2) setShowComparison(false)
      return next
    })
  }

  const compareBar = compareSelected.size > 0 && (
    <div className="sticky bottom-4 z-10 flex items-center justify-between gap-3 rounded-lg border border-indigo-200 bg-white px-4 py-2 shadow-lg dark:border-indigo-800 dark:bg-gray-900">
      <span className="text-sm text-gray-700 dark:text-gray-300">{compareSelected.size} selected</span>
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => setCompareSelected(new Set())}
          className="text-xs font-medium text-gray-500 hover:underline"
        >
          Clear
        </button>
        <button
          type="button"
          disabled={compareSelected.size < 2}
          onClick={() => setShowComparison(true)}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          Compare
        </button>
      </div>
    </div>
  )

  const comparisonModal = showComparison && compareRows.length >= 2 && (
    <CandidateComparisonPanel
      rows={compareRows}
      fullResults={fullResults}
      onClose={() => setShowComparison(false)}
      onRemove={removeFromCompare}
    />
  )

  if (!selected) {
    return (
      <div className="space-y-8">
        {groups.map((group) => (
          <section key={group.title} className="space-y-2">
            <div className="flex items-center justify-between gap-3">
              <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                {group.title} ({group.rows.length})
              </h3>
              {group.rows.length > 0 && (
                <button
                  type="button"
                  onClick={() => exportCandidatesToCsv(group.rows, csvFilename(group.title))}
                  className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
                >
                  Export CSV
                </button>
              )}
            </div>
            <CandidateResultsView
              rows={group.rows}
              onRowClick={setSelected}
              extraColumns={group.extraColumns}
              rowActions={group.rowActions}
              emptyMessage={group.emptyMessage}
              compareSelected={compareSelected}
              onToggleCompare={toggleCompare}
            />
          </section>
        ))}
        {compareBar}
        {comparisonModal}
      </div>
    )
  }

  return (
    <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[320px_1fr]">
      <div className="space-y-4 lg:max-h-[calc(100vh-8rem)] lg:overflow-y-auto lg:pr-1">
        <button
          type="button"
          onClick={() => setSelected(null)}
          className="text-xs font-medium text-indigo-600 hover:underline dark:text-indigo-400"
        >
          ← Back to all candidates
        </button>
        {groups.map((group) => (
          <div key={group.title} className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
              {group.title}
            </p>
            {group.rows.length === 0 ? (
              <p className="px-3 py-1 text-xs text-gray-500 dark:text-gray-400">
                {group.emptyMessage ?? 'No candidates.'}
              </p>
            ) : (
              group.rows.map((row) => (
                <CandidateListRow
                  key={row.candidate_name}
                  row={row}
                  selected={row.candidate_name === selected.candidate_name}
                  onClick={() => setSelected(row)}
                  actions={group.rowActions?.(row)}
                  compareChecked={compareSelected.has(row.candidate_name)}
                  onToggleCompare={toggleCompare}
                />
              ))
            )}
          </div>
        ))}
        {compareBar}
      </div>

      <CandidateDetailPanel summaryRow={selected} fullResults={fullResults} onClose={() => setSelected(null)} />
      {comparisonModal}
    </div>
  )
}
