import api from '@/lib/axios'

export const authAPI = {
  login:    (data) => api.post('/auth/login/', data),
  refresh:  (data) => api.post('/auth/refresh/', data),
  logout:   (data) => api.post('/auth/logout/', data),
  register: (data) => api.post('/auth/register/', data),
  me:       ()     => api.get('/auth/me/'),
  updateMe: (data) => api.put('/auth/me/', data),
}
