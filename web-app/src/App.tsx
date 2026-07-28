import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LoginPage } from './auth/LoginPage'
import { RegisterPage } from './auth/RegisterPage'
import { RequireAuth } from './auth/RequireAuth'
import { JobSearchResultsPage } from './features/job-seeker/JobSearchResultsPage'
import { MyJobsPage } from './features/job-seeker/MyJobsPage'
import { JobSeekerPage } from './routes/JobSeekerPage'
import { RecruiterPage } from './routes/RecruiterPage'

function NotFoundPage() {
  return <p className="text-sm text-gray-600 dark:text-gray-400">Page not found.</p>
}

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Navigate to="/recruiter" replace />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route
          path="/recruiter"
          element={
            <RequireAuth role="recruiter">
              <RecruiterPage />
            </RequireAuth>
          }
        />
        <Route path="/job-seeker" element={<JobSeekerPage />} />
        <Route path="/job-seeker/search" element={<JobSearchResultsPage />} />
        <Route
          path="/job-seeker/my-jobs"
          element={
            <RequireAuth role="job_seeker">
              <MyJobsPage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Layout>
  )
}

export default App
