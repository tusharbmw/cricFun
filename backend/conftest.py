"""
Shared pytest fixtures.
"""
import pytest
from datetime import datetime, timezone, timedelta
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from teams.models import Team, Match, Selection, Tournament
from apps.users.models import TournamentEnrollment


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def tournament(db):
    return Tournament.objects.create(
        name='Test League',
        sport=Tournament.Sport.CRICKET,
        season='2024',
        is_active=True,
    )


@pytest.fixture
def soccer_tournament(db):
    return Tournament.objects.create(
        name='World Cup 2026',
        sport=Tournament.Sport.SOCCER,
        season='2026',
        is_active=True,
    )


@pytest.fixture
def user(db, tournament):
    u = User.objects.create_user(username='testuser', password='testpass123')
    TournamentEnrollment.objects.create(user=u, tournament=tournament)
    return u


@pytest.fixture
def user2(db, tournament):
    u = User.objects.create_user(username='testuser2', password='testpass123')
    TournamentEnrollment.objects.create(user=u, tournament=tournament)
    return u


@pytest.fixture
def soccer_user(db, soccer_tournament):
    u = User.objects.create_user(username='soccer_user', password='testpass123')
    TournamentEnrollment.objects.create(user=u, tournament=soccer_tournament)
    return u


@pytest.fixture
def soccer_user2(db, soccer_tournament):
    u = User.objects.create_user(username='soccer_user2', password='testpass123')
    TournamentEnrollment.objects.create(user=u, tournament=soccer_tournament)
    return u


@pytest.fixture
def auth_client(api_client, user):
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def soccer_auth_client(api_client, soccer_user):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def team1(db):
    return Team.objects.create(name='Team Alpha')


@pytest.fixture
def team2(db):
    return Team.objects.create(name='Team Beta')


@pytest.fixture
def upcoming_match(db, team1, team2, tournament):
    """A future TBD cricket match."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        tournament=tournament,
        datetime=datetime.now(timezone.utc) + timedelta(hours=24),
        result='TBD',
        match_points=1,
        venue='Test Stadium',
    )


@pytest.fixture
def past_match(db, team1, team2, tournament):
    """A match that started in the past — picks should be locked."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(hours=2),
        result='TBD',
        match_points=1,
        venue='Test Stadium',
    )


@pytest.fixture
def completed_match_team1_won(db, team1, team2, tournament):
    return Match.objects.create(
        team1=team1,
        team2=team2,
        tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1',
        match_points=1,
        venue='Test Stadium',
    )


@pytest.fixture
def soccer_group_match(db, team1, team2, soccer_tournament):
    """A future TBD soccer group-stage match (draws allowed)."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        tournament=soccer_tournament,
        description='Group A',
        datetime=datetime.now(timezone.utc) + timedelta(hours=24),
        result='TBD',
        match_points=1,
        playoff=False,
        venue='Test Stadium',
    )


@pytest.fixture
def soccer_qf_match(db, team1, team2, soccer_tournament):
    """A future TBD soccer quarter-final (playoff, hidden auto-applied, no powerups)."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        tournament=soccer_tournament,
        description='Quarter-final',
        datetime=datetime.now(timezone.utc) + timedelta(hours=24),
        result='TBD',
        match_points=5,
        playoff=True,
        venue='Test Stadium',
    )


@pytest.fixture
def completed_soccer_group_match(db, team1, team2, soccer_tournament):
    """Completed soccer group-stage match — team1 won 3-1."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        tournament=soccer_tournament,
        description='Group A',
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1',
        match_points=1,
        playoff=False,
        home_score=3,
        away_score=1,
        venue='Test Stadium',
    )


@pytest.fixture
def completed_soccer_draw_match(db, team1, team2, soccer_tournament):
    """Completed soccer group-stage match — 1-1 draw."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        tournament=soccer_tournament,
        description='Group B',
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='draw',
        match_points=1,
        playoff=False,
        home_score=1,
        away_score=1,
        venue='Test Stadium',
    )


@pytest.fixture
def selection(db, user, upcoming_match, team1):
    return Selection.objects.create(user=user, match=upcoming_match, selection=team1)
