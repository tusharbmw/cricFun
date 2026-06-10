import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import posthog from '@/lib/posthog'
import useAuthStore from '@/store/authStore'
import useTournamentStore from '@/store/tournamentStore'
import Layout from '@/components/layout/Layout'
import ProtectedRoute from '@/components/layout/ProtectedRoute'
import Login from '@/pages/Login'
import Dashboard from '@/pages/Dashboard'
import Schedule from '@/pages/Schedule'
import Results from '@/pages/Results'
import Leaderboard from '@/pages/Leaderboard'
import MatchDetail from '@/pages/MatchDetail'
import Profile from '@/pages/Profile'
import Rules from '@/pages/Rules'
import Portfolio from '@/pages/Portfolio'
import SocialCallback from '@/pages/SocialCallback'
import TournamentChooser from '@/pages/TournamentChooser'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      staleTime: 30000,
    },
  },
})

function PageViewTracker() {
  const location = useLocation()
  useEffect(() => {
    posthog.capture('$pageview', { $current_url: window.location.href })
  }, [location.pathname])
  return null
}

function AppRoutes() {
  const authInit       = useAuthStore(s => s.init)
  const isAuthenticated = useAuthStore(s => s.isAuthenticated)
  const tournamentInit  = useTournamentStore(s => s.init)

  useEffect(() => { authInit() }, [authInit])

  // Fetch tournaments once the user is confirmed authenticated
  useEffect(() => {
    if (isAuthenticated) tournamentInit()
  }, [isAuthenticated, tournamentInit])

  return (
    <Routes>
      <Route path="*" element={<PageViewTracker />} />
      <Route path="/login" element={<Login />} />
      <Route path="/auth/callback/" element={<SocialCallback />} />
      <Route path="/tushar" element={<Portfolio />} />
      <Route path="/rules" element={<Layout />}>
        <Route index element={<Rules />} />
      </Route>
      <Route
        path="/choose"
        element={
          <ProtectedRoute>
            <TournamentChooser />
          </ProtectedRoute>
        }
      />
      <Route
        path="/"
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="schedule" element={<Schedule />} />
        <Route path="results" element={<Results />} />
        <Route path="standings" element={<Leaderboard />} />
        <Route path="matches/:id" element={<MatchDetail />} />
        <Route path="profile" element={<Profile />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppRoutes />
      </BrowserRouter>
    </QueryClientProvider>
  )
}
