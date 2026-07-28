import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { AUTH_TOKEN_KEY } from '../api/client'
import { getMe, login as loginRequest, register as registerRequest } from '../api/endpoints'
import type { User, UserRole } from '../api/types'

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
    getMe()
      .then(setUser)
      .catch(() => localStorage.removeItem(AUTH_TOKEN_KEY))
      .finally(() => setIsLoading(false))
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
