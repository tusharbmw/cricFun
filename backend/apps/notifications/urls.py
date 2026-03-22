from django.urls import path

from .views import MarkReadView, NotificationListView, UnreadCountView

urlpatterns = [
    path('',              NotificationListView.as_view(), name='notification-list'),
    path('unread-count/', UnreadCountView.as_view(),      name='notification-unread-count'),
    path('mark-read/',    MarkReadView.as_view(),          name='notification-mark-read'),
]
