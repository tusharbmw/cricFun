import api from '@/lib/axios'
import posthog from '@/lib/posthog'

export const authAPI = {
  login:    (data) => api.post('/auth/login/', data),
  refresh:  (data) => api.post('/auth/refresh/', data),
  logout:   (data) => api.post('/auth/logout/', data),
  me:       ()     => api.get('/auth/me/'),
  socialToken: () => api.get('/auth/social/token/'),
  updateMe: (data) => api.put('/auth/me/', data),

  register: (data) => api.post('/auth/register/', data).then(res => {
    posthog.capture('user_registered', { username: data.username })
    return res
  }),
}
