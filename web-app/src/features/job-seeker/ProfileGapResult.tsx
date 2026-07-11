import type { ProfileGapResponse } from '../../api/types'
import { ScoreRing } from '../../components/ScoreRing'
import { SkillChips } from '../../components/SkillChips'

interface ProfileGapResultProps {
  result: ProfileGapResponse
  onStartOver: () => void
}

const fitStyles: Record<ProfileGapResponse['current_fit'], string> = {
  strong: 'border-green-300 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950/40 dark:text-green-300',
  partial:
    'border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-300',
  weak: 'border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-300',
}

function Section({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div className="space-y-2">
      <h4 className="text-sm font-semibold">{title}</h4>
      <ul className="list-inside list-disc space-y-1 text-sm text-gray-700 dark:text-gray-300">
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  )
}

export function ProfileGapResult({ result, onStartOver }: ProfileGapResultProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-xl font-semibold">{result.candidate_name}</h2>
          <p className="text-sm text-gray-600 dark:text-gray-400">{result.target_role ?? 'Target role'}</p>
          <span
            className={`mt-2 inline-flex items-center rounded-full border px-3 py-1 text-xs font-medium capitalize ${fitStyles[result.current_fit]}`}
          >
            {result.current_fit} fit
          </span>
        </div>
        <ScoreRing score={result.role_readiness_score} size={72} />
      </div>

      {result.qualification_gaps.missing_required_skills.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Missing must-have skills
          </h3>
          <SkillChips items={result.qualification_gaps.missing_required_skills} tone="missing" limit={20} />
        </div>
      )}

      {result.qualification_gaps.matched_skills.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
            Skills you already match
          </h3>
          <SkillChips items={result.qualification_gaps.matched_skills} tone="matched" limit={20} />
        </div>
      )}

      <div className="grid gap-6 sm:grid-cols-2">
        <Section title="Suggested projects" items={result.recommended_actions.suggested_projects} />
        <Section title="Resume improvements" items={result.recommended_actions.resume_improvements} />
      </div>

      <Section title="Missing experience signals" items={result.qualification_gaps.missing_experience_signals} />

      <button
        type="button"
        onClick={onStartOver}
        className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
      >
        Check another role
      </button>
    </div>
  )
}
