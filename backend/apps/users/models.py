from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')
    approved = models.BooleanField(
        default=False,
        help_text='User participates in leaderboard and scoring only when approved.',
    )

    def __str__(self):
        return f'{self.user.username} ({"approved" if self.approved else "pending"})'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
