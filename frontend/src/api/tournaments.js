import api from '@/lib/axios'

export const tournamentsAPI = {
  list: () => api.get('/tournaments/'),
}
