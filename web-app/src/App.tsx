import { Navigate, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { JobSearchResultsPage } from './features/job-seeker/JobSearchResultsPage'
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
        <Route path="/recruiter" element={<RecruiterPage />} />
        <Route path="/job-seeker" element={<JobSeekerPage />} />
        <Route path="/job-seeker/search" element={<JobSearchResultsPage />} />
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </Layout>
  )
}

export default App
