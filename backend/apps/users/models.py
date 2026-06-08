from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='userprofile')

    def __str__(self):
        return self.user.username


class TournamentEnrollment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='tournament_enrollments')
    tournament = models.ForeignKey(
        'teams.Tournament', on_delete=models.CASCADE, related_name='enrollments'
    )

    class Meta:
        unique_together = [['user', 'tournament']]
        ordering = ['tournament__name', 'user__username']

    def __str__(self):
        return f'{self.user.username} → {self.tournament}'


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)
