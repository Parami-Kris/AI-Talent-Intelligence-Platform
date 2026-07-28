import { useEffect, useState, type FormEvent } from 'react'
import { addCandidateComment, getCandidateComments } from '../../../api/endpoints'
import { ApiError, detailMessage } from '../../../api/client'
import type { CandidateComment } from '../../../api/types'
import { ErrorBanner } from '../../../components/ErrorBanner'
import { LoadingSpinner } from '../../../components/LoadingSpinner'

export function CandidateComments({ candidateId }: { candidateId: number }) {
  const [comments, setComments] = useState<CandidateComment[] | null>(null)
  const [commentText, setCommentText] = useState('')
  const [isCaution, setIsCaution] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    getCandidateComments(candidateId)
      .then((result) => {
        if (!cancelled) setComments(result.comments)
      })
      .catch(() => {
        if (!cancelled) setComments([])
      })
    return () => {
      cancelled = true
    }
  }, [candidateId])

  const handleSubmit = async (event: FormEvent) => {
    event.preventDefault()
    if (!commentText.trim()) return

    setError(null)
    setIsSubmitting(true)
    try {
      const created = await addCandidateComment(candidateId, commentText.trim(), isCaution)
      setComments((current) => [created, ...(current ?? [])])
      setCommentText('')
      setIsCaution(false)
    } catch (err) {
      setError(err instanceof ApiError ? detailMessage(err.detail) : 'Failed to save comment.')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="space-y-3 border-t border-gray-200 pt-4 dark:border-gray-800">
      <h4 className="text-sm font-semibold">Your comments on this candidate</h4>
      <p className="text-xs text-gray-500 dark:text-gray-400">
        Only visible to you. If this candidate shows up in a future job listing, these comments (and the "flag as
        caution" checkbox) are surfaced to the ranking assistant — but only when their email or phone number matches
        what's on file here. A different email/phone on a later resume won't be recognized as the same person.
      </p>

      {error && <ErrorBanner message={error} onDismiss={() => setError(null)} />}

      <form onSubmit={handleSubmit} className="space-y-2">
        <textarea
          rows={3}
          value={commentText}
          onChange={(event) => setCommentText(event.target.value)}
          placeholder="e.g. Interviewed well on paper but struggled with system design in the loop."
          className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm dark:border-gray-700 dark:bg-gray-800"
        />
        <label className="flex items-center gap-2 text-xs text-gray-600 dark:text-gray-400">
          <input
            type="checkbox"
            checked={isCaution}
            onChange={(event) => setIsCaution(event.target.checked)}
            className="h-4 w-4 accent-red-600"
          />
          Flag as caution — always surfaced if this candidate reappears, regardless of comment wording.
        </label>
        <button
          type="submit"
          disabled={isSubmitting || !commentText.trim()}
          className="rounded-md bg-indigo-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-indigo-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isSubmitting ? 'Saving…' : 'Add comment'}
        </button>
      </form>

      {comments === null ? (
        <LoadingSpinner label="Loading comments…" />
      ) : comments.length === 0 ? (
        <p className="text-xs text-gray-500 dark:text-gray-400">No comments yet.</p>
      ) : (
        <ul className="space-y-2">
          {comments.map((comment) => (
            <li
              key={comment.id}
              className="rounded-md border border-gray-200 px-3 py-2 text-xs dark:border-gray-800"
            >
              <div className="mb-1 flex items-center justify-between gap-2 text-gray-500 dark:text-gray-400">
                <span>{new Date(comment.created_at).toLocaleString()}</span>
                {comment.is_caution && (
                  <span className="rounded-full bg-red-100 px-2 py-0.5 font-medium text-red-800 dark:bg-red-900/40 dark:text-red-300">
                    Caution
                  </span>
                )}
              </div>
              <p className="text-gray-700 dark:text-gray-300">{comment.comment_text}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
