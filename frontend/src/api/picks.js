import api from '@/lib/axios'
import posthog from '@/lib/posthog'
import useTournamentStore from '@/store/tournamentStore'

export const picksAPI = {
  list:    ()           => api.get('/picks/'),
  active:  ()           => api.get('/picks/active/'),
  history: (params)     => api.get('/picks/history/', { params }),
  stats:   (params)     => api.get('/picks/stats/', { params }),
  update:  (id, data)   => api.patch(`/picks/${id}/`, data),

  place: (data) => api.post('/picks/', data).then(res => {
    const t = useTournamentStore.getState().currentTournament
    posthog.capture('pick_placed', {
      match_id:       data.match,
      pick_type:      data.draw ? 'draw' : 'team',
      team_id:        data.draw ? null : data.selection,
      sport:          t?.sport ?? null,
      tournament_id:  t?.id ?? null,
      tournament_name: t?.name ?? null,
    })
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
