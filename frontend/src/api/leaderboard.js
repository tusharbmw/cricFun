import api from '@/lib/axios'

export const leaderboardAPI = {
  global:  (tournament) => api.get('/leaderboard/', { params: tournament ? { tournament } : {} }),
  me:      (tournament) => api.get('/leaderboard/me/', { params: tournament ? { tournament } : {} }),
  history: (tournament) => api.get('/leaderboard/history/', { params: tournament ? { tournament } : {} }),
}
