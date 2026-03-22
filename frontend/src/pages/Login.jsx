import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import useAuthStore from '@/store/authStore'

export default function Login() {
  const navigate = useNavigate()
  const login = useAuthStore(s => s.login)

  const [form, setForm] = useState({ username: '', password: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login({ username: form.username, password: form.password })
      navigate('/')
    } catch (err) {
      setError(err.response?.data?.detail ?? 'Invalid username or password')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-[#f8f9fa] flex flex-col items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-4">
        <div className="flex flex-col items-center gap-3 mb-6">
          <div className="w-16 h-16 rounded-full bg-gray-900 flex items-center justify-center"
            style={{ boxShadow: '0 0 0 3px #fbbf24' }}>
            <img src="/logo.PNG" alt="CricFun" className="w-11 h-11 object-contain rounded-full" />
          </div>
          <div className="text-center">
            <h1 className="text-2xl font-medium text-indigo-500">CricFun</h1>
            <p className="text-sm text-gray-500 mt-0.5">Sign in to place your picks</p>
          </div>
        </div>

        <div className="bg-white border border-gray-100 rounded-xl shadow-sm">
          <div className="p-5">
            <form onSubmit={handleSubmit} className="space-y-4">
              {error && (
                <div className="alert alert-error alert-soft py-2 px-3 text-sm">{error}</div>
              )}

              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">Username</span>
                </label>
                <input
                  type="text"
                  autoComplete="username"
                  value={form.username}
                  onChange={e => setForm(f => ({ ...f, username: e.target.value }))}
                  required
                  className="input input-bordered w-full"
                />
              </div>

              <div className="form-control">
                <label className="label py-1">
                  <span className="label-text font-medium">Password</span>
                </label>
                <input
                  type="password"
                  autoComplete="current-password"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                  className="input input-bordered w-full"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="btn btn-primary w-full"
              >
                {loading ? <span className="loading loading-spinner loading-sm" /> : 'Sign in'}
              </button>
            </form>
          </div>
        </div>

        <GoogleLoginButton />

        <p className="text-center text-xs text-gray-400 pt-2">
          TM, all rights reserved. By using this app you agree that Tushar is the Best!
        </p>
      </div>
    </div>
  )
}

function GoogleLoginButton() {
  // Django allauth handles the Google OAuth flow via /accounts/google/login/
  // Redirect to Django's allauth endpoint which sets session + JWT
  function handleGoogle() {
    window.location.href = '/accounts/google/login/'
  }

  return (
    <button
      onClick={handleGoogle}
      className="btn btn-outline w-full gap-3"
    >
      <GoogleIcon />
      Continue with Google
    </button>
  )
}

function GoogleIcon() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" xmlns="http://www.w3.org/2000/svg">
      <path d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 01-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615z" fill="#4285F4"/>
      <path d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 009 18z" fill="#34A853"/>
      <path d="M3.964 10.71A5.41 5.41 0 013.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 000 9c0 1.452.348 2.827.957 4.042l3.007-2.332z" fill="#FBBC05"/>
      <path d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 00.957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58z" fill="#EA4335"/>
    </svg>
  )
}
