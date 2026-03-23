from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification, PushSubscription


class NotificationListView(APIView):
    """GET /api/v1/notifications/  → 20 most recent notifications for the current user."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = Notification.objects.filter(user=request.user)[:20]
        data = [
            {
                'id':         n.id,
                'type':       n.type,
                'message':    n.message,
                'is_read':    n.is_read,
                'created_at': n.created_at.isoformat(),
                'meta':       n.meta,
            }
            for n in qs
        ]
        return Response(data)


class UnreadCountView(APIView):
    """GET /api/v1/notifications/unread-count/  → {"count": N}"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        count = Notification.objects.filter(user=request.user, is_read=False).count()
        return Response({'count': count})


class MarkReadView(APIView):
    """POST /api/v1/notifications/mark-read/  → marks all unread as read."""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        marked = Notification.objects.filter(
            user=request.user, is_read=False
        ).update(is_read=True)
        return Response({'marked': marked})


class ClearNotificationsView(APIView):
    """DELETE /api/v1/notifications/clear/  → deletes all notifications for the user."""
    permission_classes = [IsAuthenticated]

    def delete(self, request):
        deleted, _ = Notification.objects.filter(user=request.user).delete()
        return Response({'deleted': deleted})


class DeleteNotificationView(APIView):
    """DELETE /api/v1/notifications/<id>/  → deletes a single notification."""
    permission_classes = [IsAuthenticated]

    def delete(self, request, pk):
        deleted, _ = Notification.objects.filter(user=request.user, pk=pk).delete()
        if not deleted:
            return Response(status=404)
        return Response(status=204)


class PushSubscriptionView(APIView):
    """
    POST   /api/v1/notifications/push/  → save a push subscription
    DELETE /api/v1/notifications/push/  → remove it
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        sub  = request.data.get('subscription', {})
        keys = sub.get('keys', {})
        endpoint = sub.get('endpoint', '')
        p256dh   = keys.get('p256dh', '')
        auth     = keys.get('auth', '')
        if not endpoint or not p256dh or not auth:
            return Response({'error': 'Invalid subscription data'}, status=400)

        PushSubscription.objects.update_or_create(
            endpoint=endpoint,
            defaults={'user': request.user, 'p256dh': p256dh, 'auth': auth},
        )
        return Response({'status': 'saved'})

    def delete(self, request):
        endpoint = request.data.get('endpoint', '')
        PushSubscription.objects.filter(user=request.user, endpoint=endpoint).delete()
        return Response({'status': 'removed'})
