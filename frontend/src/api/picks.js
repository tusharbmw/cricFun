import api from '@/lib/axios'
import posthog from '@/lib/posthog'

export const picksAPI = {
  list:    ()           => api.get('/picks/'),
  active:  ()           => api.get('/picks/active/'),
  history: (params)     => api.get('/picks/history/', { params }),
  stats:   ()           => api.get('/picks/stats/'),
  update:  (id, data)   => api.patch(`/picks/${id}/`, data),

  place: (data) => api.post('/picks/', data).then(res => {
    posthog.capture('pick_placed', { match_id: data.match, team_id: data.selection })
    return res
  }),

  remove: (id) => api.delete(`/picks/${id}/`).then(res => {
    posthog.capture('pick_removed', { pick_id: id })
    return res
  }),

  applyPowerup: (id, type) => api.post(`/picks/${id}/powerup/`, { powerup_type: type }).then(res => {
    posthog.capture('powerup_applied', { pick_id: id, powerup_type: type })
    return res
  }),
}
