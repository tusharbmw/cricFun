import api from '@/lib/axios'

export const notificationsAPI = {
  list:        () => api.get('/notifications/'),
  unreadCount: () => api.get('/notifications/unread-count/'),
  markRead:    () => api.post('/notifications/mark-read/'),
  clear:       ()   => api.delete('/notifications/clear/'),
  deleteOne:   (id) => api.delete(`/notifications/${id}/`),
  savePush:    (subscription) => api.post('/notifications/push/', { subscription }),
  deletePush:  (data)         => api.delete('/notifications/push/', { data }),
}
