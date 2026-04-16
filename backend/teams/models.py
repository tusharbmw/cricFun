from django.db import models
from django.contrib.auth.models import User


class Team(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True, null=True)
    logo = models.ImageField(blank=True, null=True)
    location = models.CharField(max_length=40, blank=True, null=True)
    logo_url = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Match(models.Model):
    class Result(models.TextChoices):
        NO_RESULT = 'NR', 'No Result'
        TEAM1_WON = 'team1', 'Team 1 Won'
        TEAM2_WON = 'team2', 'Team 2 Won'
        IN_PROGRESS = 'IP', 'In Progress'
        TBD = 'TBD', 'TBD'
        TOSS = 'TOSS', 'Toss'
        DELAYED = 'DLD', 'Delayed'

    team1 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='home_matches')
    team2 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='away_matches')
    description = models.TextField(blank=True, null=True)
    venue = models.CharField(max_length=40, blank=True, null=True)
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.TBD, db_index=True)
    datetime = models.DateTimeField(db_index=True)
    tournament = models.CharField(max_length=50, default='IPL', blank=True, null=True)
    match_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    match_points = models.IntegerField(default=1)
    playoff = models.BooleanField(default=False)
    scores = models.JSONField(default=list, blank=True)
    status_text = models.CharField(max_length=200, blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['datetime']

    def __str__(self):
        team1 = self.team1.name if self.team1 else '?'
        team2 = self.team2.name if self.team2 else '?'
        return f'{team1} vs {team2} ({self.description})'

    @property
    def is_live(self):
        return self.result == self.Result.IN_PROGRESS

    @property
    def is_completed(self):
        return self.result in (self.Result.TEAM1_WON, self.Result.TEAM2_WON, self.Result.NO_RESULT)


class Selection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    selection = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True)
    hidden = models.BooleanField(default=False)
    no_negative = models.BooleanField(default=False)
    fake = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'match']]

    def __str__(self):
        return f'{self.user.username} → {self.selection} ({self.match})'
