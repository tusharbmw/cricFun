import api from '@/lib/axios'

export const picksAPI = {
  list:         ()           => api.get('/picks/'),
  place:        (data)       => api.post('/picks/', data),
  update:       (id, data)   => api.patch(`/picks/${id}/`, data),
  remove:       (id)         => api.delete(`/picks/${id}/`),
  active:       ()           => api.get('/picks/active/'),
  history:      (params)     => api.get('/picks/history/', { params }),
  stats:        ()           => api.get('/picks/stats/'),
  applyPowerup: (id, type)   => api.post(`/picks/${id}/powerup/`, { powerup_type: type }),
}
