import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { LoginPage } from './auth/LoginPage'
import { RegisterPage } from './auth/RegisterPage'
import { RequireAuth } from './auth/RequireAuth'
import { JobSearchResultsPage } from './features/job-seeker/JobSearchResultsPage'
import { MatchesPage } from './features/job-seeker/MatchesPage'
import { MyJobsPage } from './features/job-seeker/MyJobsPage'
import { ProfilePage } from './features/job-seeker/ProfilePage'
import { ShortlistDetailPage } from './features/recruiter/ShortlistDetailPage'
import { ShortlistsPage } from './features/recruiter/ShortlistsPage'
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
        <Route
          path="/recruiter/shortlists"
          element={
            <RequireAuth role="recruiter">
              <ShortlistsPage />
            </RequireAuth>
          }
        />
        <Route
          path="/recruiter/shortlists/:runId"
          element={
            <RequireAuth role="recruiter">
              <ShortlistDetailPage />
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
        <Route
          path="/job-seeker/matches"
          element={
            <RequireAuth role="job_seeker">
              <MatchesPage />
            </RequireAuth>
          }
        />
        <Route
          path="/job-seeker/profile"
          element={
            <RequireAuth role="job_seeker">
              <ProfilePage />
            </RequireAuth>
          }
        />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Layout>
  )
}

export default App
