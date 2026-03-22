import api from '@/lib/axios'

export const notificationsAPI = {
  list:        () => api.get('/notifications/'),
  unreadCount: () => api.get('/notifications/unread-count/'),
  markRead:    () => api.post('/notifications/mark-read/'),
}
