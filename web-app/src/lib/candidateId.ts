const STORAGE_KEY = 'candidateId'

// Anonymous, local-only identity for the job seeker's search/view/apply/like
// history - not tied to an account, used while logged out. Once a job_seeker
// account exists, pass its id as accountUserId so history is keyed to
// `user-{id}` instead - stable across devices/browsers, unlike the localStorage
// UUID. Pre-login anonymous history under the old id is not migrated/merged
// into the account; this is a deliberate v1 limitation, not an oversight.
export function getCandidateId(accountUserId?: number): string {
  if (accountUserId != null) return `user-${accountUserId}`

  const existing = localStorage.getItem(STORAGE_KEY)
  if (existing) return existing

  const id = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, id)
  return id
}
