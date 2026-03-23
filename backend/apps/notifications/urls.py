from django.urls import path

from .views import ClearNotificationsView, DeleteNotificationView, MarkReadView, NotificationListView, PushSubscriptionView, UnreadCountView

urlpatterns = [
    path('',              NotificationListView.as_view(),   name='notification-list'),
    path('unread-count/', UnreadCountView.as_view(),        name='notification-unread-count'),
    path('mark-read/',    MarkReadView.as_view(),           name='notification-mark-read'),
    path('clear/',        ClearNotificationsView.as_view(), name='notification-clear'),
    path('<int:pk>/',     DeleteNotificationView.as_view(), name='notification-delete'),
    path('push/',         PushSubscriptionView.as_view(),   name='notification-push'),
]
