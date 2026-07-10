import type { ReactNode } from 'react'

export function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50 text-gray-900 dark:bg-gray-950 dark:text-gray-100">
      <header className="border-b border-gray-200 bg-white dark:border-gray-800 dark:bg-gray-900">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <h1 className="text-lg font-semibold">AI Talent Intelligence Platform</h1>
          <nav className="flex gap-4 text-sm">
            <span className="rounded-md bg-indigo-100 px-3 py-1.5 font-medium text-indigo-800 dark:bg-indigo-900/40 dark:text-indigo-300">
              Recruiter Dashboard
            </span>
            <span
              className="cursor-not-allowed rounded-md px-3 py-1.5 text-gray-400 dark:text-gray-600"
              title="Coming soon"
            >
              Job Seeker (coming soon)
            </span>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
    </div>
  )
}
