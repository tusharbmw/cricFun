from django.db import models
from django.contrib.auth.models import User


class Tournament(models.Model):
    class Sport(models.TextChoices):
        CRICKET = 'cricket', 'Cricket'
        SOCCER = 'soccer', 'Soccer'

    name = models.CharField(max_length=100)
    sport = models.CharField(max_length=20, choices=Sport.choices, default=Sport.CRICKET)
    season = models.CharField(max_length=50, blank=True, default='')
    external_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=False)
    state = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.season})' if self.season else self.name


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
        DRAW = 'draw', 'Draw'
        IN_PROGRESS = 'IP', 'In Progress'
        TBD = 'TBD', 'TBD'
        TOSS = 'TOSS', 'Toss'
        DELAYED = 'DLD', 'Delayed'

    class Duration(models.TextChoices):
        REGULAR = 'REGULAR', 'Regular'
        EXTRA_TIME = 'EXTRA_TIME', 'Extra Time'
        PENALTY_SHOOTOUT = 'PENALTY_SHOOTOUT', 'Penalty Shootout'

    team1 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='home_matches')
    team2 = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, related_name='away_matches')
    tournament = models.ForeignKey(Tournament, on_delete=models.PROTECT, related_name='matches')
    description = models.TextField(blank=True, null=True)
    venue = models.CharField(max_length=40, blank=True, null=True)
    result = models.CharField(max_length=10, choices=Result.choices, default=Result.TBD, db_index=True)
    datetime = models.DateTimeField(db_index=True)
    match_id = models.CharField(max_length=50, blank=True, null=True, unique=True)
    match_points = models.IntegerField(default=1)
    playoff = models.BooleanField(default=False)
    scores = models.JSONField(default=list, blank=True)
    status_text = models.CharField(max_length=200, blank=True, default='')
    home_score = models.IntegerField(null=True, blank=True)
    away_score = models.IntegerField(null=True, blank=True)
    duration = models.CharField(
        max_length=20, choices=Duration.choices, null=True, blank=True
    )
    odds = models.JSONField(null=True, blank=True)
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
        return self.result in (
            self.Result.TEAM1_WON,
            self.Result.TEAM2_WON,
            self.Result.DRAW,
            self.Result.NO_RESULT,
        )


class Selection(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    match = models.ForeignKey(Match, on_delete=models.CASCADE)
    selection = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    draw = models.BooleanField(default=False)
    hidden = models.BooleanField(default=False)
    no_negative = models.BooleanField(default=False)
    fake = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = [['user', 'match']]

    def __str__(self):
        pick = 'Draw' if self.draw else str(self.selection)
        return f'{self.user.username} → {pick} ({self.match})'
