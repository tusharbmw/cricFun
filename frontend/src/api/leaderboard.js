import api from '@/lib/axios'

export const leaderboardAPI = {
  global:  () => api.get('/leaderboard/'),
  me:      () => api.get('/leaderboard/me/'),
  history: () => api.get('/leaderboard/history/'),
}
