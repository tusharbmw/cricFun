"""
Shared pytest fixtures.
"""
import pytest
from datetime import datetime, timezone, timedelta
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from teams.models import Team, Match, Selection


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return User.objects.create_user(username='testuser', password='testpass123')


@pytest.fixture
def user2(db):
    return User.objects.create_user(username='testuser2', password='testpass123')


@pytest.fixture
def auth_client(api_client, user):
    refresh = RefreshToken.for_user(user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    return api_client


@pytest.fixture
def team1(db):
    return Team.objects.create(name='Team Alpha')


@pytest.fixture
def team2(db):
    return Team.objects.create(name='Team Beta')


@pytest.fixture
def upcoming_match(db, team1, team2):
    """A future TBD match."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        datetime=datetime.now(timezone.utc) + timedelta(hours=24),
        result='TBD',
        match_points=1,
        venue='Test Stadium',
    )


@pytest.fixture
def past_match(db, team1, team2):
    """A match that started in the past — picks should be locked."""
    return Match.objects.create(
        team1=team1,
        team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(hours=2),
        result='TBD',
        match_points=1,
        venue='Test Stadium',
    )


@pytest.fixture
def completed_match_team1_won(db, team1, team2):
    return Match.objects.create(
        team1=team1,
        team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1',
        match_points=1,
        venue='Test Stadium',
    )


@pytest.fixture
def selection(db, user, upcoming_match, team1):
    return Selection.objects.create(user=user, match=upcoming_match, selection=team1)
