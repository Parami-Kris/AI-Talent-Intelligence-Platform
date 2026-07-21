const STORAGE_KEY = 'candidateId'

// Anonymous, local-only identity for the job seeker's search/view/apply/like
// history - not tied to an account. If email login is added later, that can
// simply start populating this same value instead; nothing downstream cares
// where the id came from.
export function getCandidateId(): string {
  const existing = localStorage.getItem(STORAGE_KEY)
  if (existing) return existing

  const id = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEY, id)
  return id
}
