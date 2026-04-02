import api from '@/lib/axios'

export const matchesAPI = {
  list:      (params) => api.get('/matches/', { params }),
  get:       (id)     => api.get(`/matches/${id}/`),
  live:      ()       => api.get('/matches/live/'),
  upcoming:  (params) => api.get('/matches/upcoming/', { params }),
  completed: (params) => api.get('/matches/completed/', { params }),
  selections:(id)     => api.get(`/matches/${id}/selections/`),
  teamForm:  (id)     => api.get(`/matches/${id}/team_form/`),
  teams:     ()       => api.get('/teams/'),
}
