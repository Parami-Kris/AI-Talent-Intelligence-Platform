import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { ApiError, AUTH_TOKEN_KEY } from '../api/client'
import { getMe, login as loginRequest, register as registerRequest } from '../api/endpoints'
import type { User, UserRole } from '../api/types'

function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

interface AuthContextValue {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, role: UserRole, displayName?: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!localStorage.getItem(AUTH_TOKEN_KEY)) {
      setIsLoading(false)
      return
    }

    let cancelled = false

    async function verifySession() {
      // Only a 401 means the token itself is actually invalid/expired - that's
      // the one case worth clearing it and sending the user back to /login.
      // Anything else (network blip, a slow/momentarily-erroring backend) is
      // transient and shouldn't sign someone out of a session that's still
      // genuinely valid - one retry rides out most of those before giving up.
      for (let attempt = 0; attempt < 2; attempt++) {
        try {
          const me = await getMe()
          if (!cancelled) setUser(me)
          return
        } catch (err) {
          if (err instanceof ApiError && err.status === 401) {
            localStorage.removeItem(AUTH_TOKEN_KEY)
            return
          }
          if (attempt === 0) await sleep(1500)
        }
      }
      // Kept the token so the next reload (or this session recovering) can
      // still pick the session back up instead of forcing a fresh login.
    }

    verifySession().finally(() => {
      if (!cancelled) setIsLoading(false)
    })

    return () => {
      cancelled = true
    }
  }, [])

  async function login(email: string, password: string) {
    const result = await loginRequest({ email, password })
    localStorage.setItem(AUTH_TOKEN_KEY, result.access_token)
    setUser(result.user)
  }

  async function register(email: string, password: string, role: UserRole, displayName?: string) {
    const result = await registerRequest({ email, password, role, display_name: displayName || undefined })
    localStorage.setItem(AUTH_TOKEN_KEY, result.access_token)
    setUser(result.user)
  }

  function logout() {
    localStorage.removeItem(AUTH_TOKEN_KEY)
    setUser(null)
  }

  return <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used within an AuthProvider')
  return context
}
