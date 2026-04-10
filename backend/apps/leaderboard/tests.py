"""
Tests for leaderboard scoring logic and API.
"""
import pytest
from datetime import datetime, timezone, timedelta

from teams.models import Match, Selection
from apps.leaderboard.views import calculate_scores


LEADERBOARD_URL = '/api/v1/leaderboard/'
MY_RANK_URL = '/api/v1/leaderboard/me/'


# ---------------------------------------------------------------------------
# Unit tests for calculate_scores()
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_winner_earns_points_equal_to_losers(db, user, user2, team1, team2):
    """User who picked the winning team earns 1 point per loser."""
    match = Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)   # winner
    Selection.objects.create(user=user2, match=match, selection=team2)  # loser

    scores = calculate_scores()
    assert scores[user.username]['won'] == 1
    assert scores[user.username]['lost'] == 0
    assert scores[user2.username]['won'] == 0
    assert scores[user2.username]['lost'] == 1


@pytest.mark.django_db
def test_match_points_multiplier(db, user, user2, team1, team2):
    """match_points=2 doubles the score."""
    match = Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=2,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2)

    scores = calculate_scores()
    assert scores[user.username]['won'] == 2   # 1 loser × 2 pts
    assert scores[user2.username]['lost'] == 2


@pytest.mark.django_db
def test_no_negative_powerup_blocks_loss(db, user, user2, team1, team2):
    """User with no_negative powerup loses nothing even when wrong."""
    match = Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2, no_negative=True)

    scores = calculate_scores()
    assert scores[user2.username]['lost'] == 0
    assert scores[user2.username]['total'] == 0


@pytest.mark.django_db
def test_skipped_match_counts_as_skip(db, user, user2, team1, team2):
    """User who doesn't pick on a completed match gets a skip."""
    match = Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    # Only user2 picks
    Selection.objects.create(user=user2, match=match, selection=team1)

    scores = calculate_scores()
    assert scores[user.username]['skipped'] == 1
    assert scores[user2.username]['skipped'] == 0


@pytest.mark.django_db
def test_total_is_won_minus_lost(db, user, user2, team1, team2):
    match = Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2)

    scores = calculate_scores()
    assert scores[user.username]['total'] == scores[user.username]['won'] - scores[user.username]['lost']


# ---------------------------------------------------------------------------
# API tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_leaderboard_requires_auth(api_client):
    response = api_client.get(LEADERBOARD_URL)
    assert response.status_code == 401


@pytest.mark.django_db
def test_leaderboard_returns_ranked_list(auth_client, user):
    response = auth_client.get(LEADERBOARD_URL)
    assert response.status_code == 200
    assert 'entries' in response.data
    assert isinstance(response.data['entries'], list)
    # Must include authenticated user
    usernames = [e['username'] for e in response.data['entries']]
    assert user.username in usernames


@pytest.mark.django_db
def test_leaderboard_sorted_by_total_desc(db, auth_client, user, user2, team1, team2):
    match = Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)   # wins
    Selection.objects.create(user=user2, match=match, selection=team2)  # loses

    response = auth_client.get(LEADERBOARD_URL)
    assert response.status_code == 200
    totals = [e['total'] for e in response.data['entries']]
    assert totals == sorted(totals, reverse=True)


@pytest.mark.django_db
def test_my_rank_returns_current_user(auth_client, user):
    response = auth_client.get(MY_RANK_URL)
    assert response.status_code == 200
    assert response.data['username'] == user.username
    assert 'rank' in response.data
    assert 'total' in response.data
