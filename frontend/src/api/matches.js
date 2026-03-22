import api from '@/lib/axios'

export const matchesAPI = {
  list:      (params) => api.get('/matches/', { params }),
  get:       (id)     => api.get(`/matches/${id}/`),
  live:      ()       => api.get('/matches/live/'),
  upcoming:  ()       => api.get('/matches/upcoming/'),
  completed: (params) => api.get('/matches/completed/', { params }),
  selections:(id)     => api.get(`/matches/${id}/selections/`),
  teams:     ()       => api.get('/teams/'),
}
