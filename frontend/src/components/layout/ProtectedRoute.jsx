import { Navigate } from 'react-router-dom'
import useAuthStore from '@/store/authStore'

export default function ProtectedRoute({ children }) {
  const { isAuthenticated, isLoading } = useAuthStore()
  if (isLoading) return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="animate-spin rounded-full h-10 w-10 border-4 border-blue-600 border-t-transparent" />
    </div>
  )
  return isAuthenticated ? children : <Navigate to="/login" replace />
}
