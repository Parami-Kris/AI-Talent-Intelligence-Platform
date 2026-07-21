import type { CandidateSummary } from '../../../api/types'

const CSV_COLUMNS: { header: string; get: (row: CandidateSummary) => string | number }[] = [
  { header: 'Rank', get: (row) => row.final_rank ?? row.rank ?? '' },
  { header: 'Candidate', get: (row) => row.candidate_name },
  { header: 'Eligible', get: (row) => (row.is_eligible ? 'Yes' : 'No') },
  { header: 'Score', get: (row) => row.final_score ?? row.overall_score ?? '' },
  { header: 'Skill score', get: (row) => row.skill_score ?? '' },
  { header: 'Experience score', get: (row) => row.experience_score ?? '' },
  { header: 'LLM relevance score', get: (row) => row.experience_relevance_score ?? '' },
  { header: 'Domain fit', get: (row) => row.domain_fit ?? '' },
  { header: 'Missing must-haves', get: (row) => (row.top_missing_must_haves ?? []).join('; ') },
  { header: 'Job stability', get: (row) => row.job_stability_flag ?? '' },
  { header: 'Manually added', get: (row) => (row.manually_added ? 'Yes' : 'No') },
]

function csvEscape(value: string | number): string {
  const str = String(value)
  return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str
}

export function candidatesToCsv(rows: CandidateSummary[]): string {
  const header = CSV_COLUMNS.map((col) => csvEscape(col.header)).join(',')
  const lines = rows.map((row) => CSV_COLUMNS.map((col) => csvEscape(col.get(row))).join(','))
  return [header, ...lines].join('\n')
}

export function exportCandidatesToCsv(rows: CandidateSummary[], filename: string): void {
  const blob = new Blob([candidatesToCsv(rows)], { type: 'text/csv;charset=utf-8;' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}
