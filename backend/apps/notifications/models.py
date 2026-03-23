from django.contrib.auth.models import User
from django.db import models


class PushSubscription(models.Model):
    """Stores a browser Web Push subscription for a user."""
    user     = models.ForeignKey(User, on_delete=models.CASCADE, related_name='push_subscriptions')
    endpoint = models.CharField(max_length=512, unique=True)
    p256dh   = models.TextField()
    auth     = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.user.username} — {self.endpoint[:60]}'


class Notification(models.Model):
    TYPE_CHOICES = [
        ('rank_change',  'Rank Change'),
        ('pick_result',  'Pick Result'),
    ]

    user       = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    type       = models.CharField(max_length=30, choices=TYPE_CHOICES)
    message    = models.CharField(max_length=255)
    is_read    = models.BooleanField(default=False, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Extra context e.g. {"new_leader": "alice", "prev_leader": "bob", "match_id": 12}
    meta       = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [models.Index(fields=['user', 'is_read'])]

    def __str__(self):
        return f'{self.user.username} | {self.type} | read={self.is_read}'
