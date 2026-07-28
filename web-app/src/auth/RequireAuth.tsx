import type { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import type { UserRole } from '../api/types'
import { useAuth } from './AuthContext'

export function RequireAuth({ role, children }: { role: UserRole; children: ReactNode }) {
  const { user, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) return null
  if (!user) return <Navigate to="/login" replace state={{ from: location }} />
  // Redirect to the user's own home, not "/" - "/" redirects to /recruiter,
  // which would bounce a logged-in job seeker straight back into this same
  // check and loop.
  if (user.role !== role) return <Navigate to={user.role === 'recruiter' ? '/recruiter' : '/job-seeker'} replace />

  return <>{children}</>
}
