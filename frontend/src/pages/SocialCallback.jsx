import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { authAPI } from '@/api/auth'
import useAuthStore from '@/store/authStore'
import Spinner from '@/components/ui/Spinner'

/**
 * Landing page after Google OAuth redirect.
 * Exchanges the allauth Django session for JWT tokens, then navigates home.
 */
export default function SocialCallback() {
  const navigate = useNavigate()
  const setUser = useAuthStore(s => s.setUser)

  useEffect(() => {
    authAPI.socialToken()
      .then(({ data }) => {
        localStorage.setItem('access_token', data.access)
        localStorage.setItem('refresh_token', data.refresh)
        return authAPI.me()
      })
      .then(({ data: user }) => {
        setUser(user)
        useAuthStore.setState({ isAuthenticated: true, isLoading: false })
        navigate('/', { replace: true })
      })
      .catch(() => {
        navigate('/login', { replace: true })
      })
  }, [navigate, setUser])

  return (
    <div className="min-h-screen flex items-center justify-center">
      <Spinner />
    </div>
  )
}
