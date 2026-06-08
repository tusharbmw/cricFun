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
# Cricket scoring — unit tests
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_winner_earns_points_equal_to_losers(db, user, user2, tournament, team1, team2):
    """User who picked the winning team earns 1 point per loser."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2)

    scores = calculate_scores()
    assert scores[user.username]['won'] == 1
    assert scores[user.username]['lost'] == 0
    assert scores[user2.username]['won'] == 0
    assert scores[user2.username]['lost'] == 1


@pytest.mark.django_db
def test_match_points_multiplier(db, user, user2, tournament, team1, team2):
    """match_points=2 doubles the score."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=2,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2)

    scores = calculate_scores()
    assert scores[user.username]['won'] == 2
    assert scores[user2.username]['lost'] == 2


@pytest.mark.django_db
def test_no_negative_powerup_blocks_loss(db, user, user2, tournament, team1, team2):
    """User with no_negative loses nothing even when wrong."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2, no_negative=True)

    scores = calculate_scores()
    assert scores[user2.username]['lost'] == 0
    assert scores[user2.username]['total'] == 0


@pytest.mark.django_db
def test_skipped_match_counts_as_skip(db, user, user2, tournament, team1, team2):
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user2, match=match, selection=team1)

    scores = calculate_scores()
    assert scores[user.username]['skipped'] == 1
    assert scores[user2.username]['skipped'] == 0


@pytest.mark.django_db
def test_total_is_won_minus_lost(db, user, user2, tournament, team1, team2):
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2)

    scores = calculate_scores()
    u = scores[user.username]
    assert u['total'] == u['won'] - u['lost']


# ---------------------------------------------------------------------------
# Soccer scoring — win (variable BP)
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_soccer_win_bp_scales_with_goal_diff(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """3-1 win → goal_diff=2 → BP = match_points × 2."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
        home_score=3, away_score=1,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    Selection.objects.create(user=soccer_user2, match=match, selection=team2)

    scores = calculate_scores()
    # BP = 1 × min(2, 3) = 2
    assert scores[soccer_user.username]['won'] == 2
    assert scores[soccer_user2.username]['lost'] == 2


@pytest.mark.django_db
def test_soccer_win_bp_capped_at_3(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """5-0 win → goal_diff=5 → BP capped at match_points × 3."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
        home_score=5, away_score=0,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    Selection.objects.create(user=soccer_user2, match=match, selection=team2)

    scores = calculate_scores()
    assert scores[soccer_user.username]['won'] == 3
    assert scores[soccer_user2.username]['lost'] == 3


@pytest.mark.django_db
def test_soccer_win_minimum_bp_1(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """Shootout scenario (goal_diff=0) → BP floored at match_points × 1."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=5,
        home_score=1, away_score=1,
        duration='PENALTY_SHOOTOUT',
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    Selection.objects.create(user=soccer_user2, match=match, selection=team2)

    scores = calculate_scores()
    assert scores[soccer_user.username]['won'] == 5   # 1 loser × 5 pts × max(1,0)=1
    assert scores[soccer_user2.username]['lost'] == 5


@pytest.mark.django_db
def test_soccer_win_net_zero(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """Without no_negative: total points transferred = zero sum."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
        home_score=2, away_score=0,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    Selection.objects.create(user=soccer_user2, match=match, selection=team2)

    scores = calculate_scores()
    net = scores[soccer_user.username]['total'] + scores[soccer_user2.username]['total']
    assert net == 0


@pytest.mark.django_db
def test_soccer_win_net_zero_breaks_with_no_negative(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """no_negative shields a loser → net sum > 0 (winner gains, loser loses nothing)."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
        home_score=2, away_score=0,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    Selection.objects.create(user=soccer_user2, match=match, selection=team2, no_negative=True)

    scores = calculate_scores()
    net = scores[soccer_user.username]['total'] + scores[soccer_user2.username]['total']
    assert net > 0  # zero-sum breaks when no_negative is used


# ---------------------------------------------------------------------------
# Soccer scoring — draw result
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_soccer_draw_correct_picker_wins(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """1-1 draw → BP = 1 × (1+1+1) = 3. Draw picker wins, team pickers lose."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='draw', match_points=1,
        home_score=1, away_score=1,
    )
    Selection.objects.create(user=soccer_user, match=match, draw=True)   # correct
    Selection.objects.create(user=soccer_user2, match=match, selection=team1)  # wrong

    scores = calculate_scores()
    # BP = 1 × (1+1+1) = 3
    assert scores[soccer_user.username]['won'] == 3   # 1 wrong picker × 3
    assert scores[soccer_user2.username]['lost'] == 3  # 1 correct picker × 3


@pytest.mark.django_db
def test_soccer_draw_net_zero(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """Draw result — net sum is zero without no_negative."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='draw', match_points=1,
        home_score=0, away_score=0,
    )
    Selection.objects.create(user=soccer_user, match=match, draw=True)
    Selection.objects.create(user=soccer_user2, match=match, selection=team1)

    scores = calculate_scores()
    net = scores[soccer_user.username]['total'] + scores[soccer_user2.username]['total']
    assert net == 0


@pytest.mark.django_db
def test_soccer_match_skipped_if_no_score_data(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """Soccer match with result but no home/away score is skipped in scoring."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
        home_score=None, away_score=None,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    Selection.objects.create(user=soccer_user2, match=match, selection=team2)

    scores = calculate_scores()
    assert scores[soccer_user.username]['won'] == 0
    assert scores[soccer_user2.username]['lost'] == 0


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
    usernames = [e['username'] for e in response.data['entries']]
    assert user.username in usernames


@pytest.mark.django_db
def test_leaderboard_sorted_by_total_desc(db, auth_client, user, user2, tournament, team1, team2):
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
    )
    Selection.objects.create(user=user, match=match, selection=team1)
    Selection.objects.create(user=user2, match=match, selection=team2)

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


@pytest.mark.django_db
def test_leaderboard_scoped_to_tournament(
    auth_client, user, user2, soccer_user, tournament, soccer_tournament, team1, team2
):
    """?tournament= param returns only players in that tournament and tournament_name."""
    response = auth_client.get(LEADERBOARD_URL, {'tournament': soccer_tournament.id})
    assert response.status_code == 200
    assert response.data['tournament_name'] == soccer_tournament.name
    usernames = [e['username'] for e in response.data['entries']]
    assert soccer_user.username in usernames
    # cricket-only users must not appear
    assert user.username not in usernames
    assert user2.username not in usernames


@pytest.mark.django_db
def test_my_rank_scoped_to_tournament(
    soccer_auth_client, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """?tournament= param computes rank from that tournament's matches only."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
        home_score=2, away_score=0,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    Selection.objects.create(user=soccer_user2, match=match, selection=team2)

    response = soccer_auth_client.get(MY_RANK_URL, {'tournament': soccer_tournament.id})
    assert response.status_code == 200
    assert response.data['username'] == soccer_user.username
    assert response.data['total'] > 0


@pytest.mark.django_db
def test_my_rank_cross_tournament_isolation(
    auth_client, soccer_auth_client, user, soccer_user,
    tournament, soccer_tournament, team1, team2
):
    """A win in cricket must not inflate the soccer tournament rank, and vice versa."""
    cricket_match = Match.objects.create(
        team1=team1, team2=team2, tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=1,
        home_score=None, away_score=None,
    )
    Selection.objects.create(user=user, match=cricket_match, selection=team1)

    # soccer user checks their own rank scoped to soccer — should be 0 (no soccer picks)
    response = soccer_auth_client.get(MY_RANK_URL, {'tournament': soccer_tournament.id})
    assert response.status_code == 200
    assert response.data['total'] == 0


# ---------------------------------------------------------------------------
# is_high_stakes boundary — auto-assignment and skip counting
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_r32_non_picker_gets_skip_not_penalty(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """R32: non-picker counts as a skip, NOT penalised with points loss."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        description='Round of 32',
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=2,
        home_score=2, away_score=1, playoff=True,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    # soccer_user2 does NOT pick

    scores = calculate_scores(tournament=soccer_tournament)
    assert scores[soccer_user2.username]['skipped'] == 1
    assert scores[soccer_user2.username]['lost'] == 0


@pytest.mark.django_db
def test_qf_non_picker_penalised_not_skipped(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """QF: non-picker is auto-assigned losing side and loses points (is_high_stakes=True)."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        description='Quarter-final',
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team1', match_points=5,
        home_score=2, away_score=1, playoff=True,
    )
    Selection.objects.create(user=soccer_user, match=match, selection=team1)
    # soccer_user2 does NOT pick — should be auto-assigned team2 (loser)

    scores = calculate_scores(tournament=soccer_tournament)
    assert scores[soccer_user2.username]['skipped'] == 0
    assert scores[soccer_user2.username]['lost'] > 0


@pytest.mark.django_db
def test_r16_non_picker_gets_skip_not_penalty(
    db, soccer_user, soccer_user2, soccer_tournament, team1, team2
):
    """R16: same as R32 — powerups open, no auto-assignment penalty."""
    match = Match.objects.create(
        team1=team1, team2=team2, tournament=soccer_tournament,
        description='Round of 16',
        datetime=datetime.now(timezone.utc) - timedelta(days=1),
        result='team2', match_points=3,
        home_score=0, away_score=1, playoff=True,
    )
    Selection.objects.create(user=soccer_user2, match=match, selection=team2)
    # soccer_user does NOT pick

    scores = calculate_scores(tournament=soccer_tournament)
    assert scores[soccer_user.username]['skipped'] == 1
    assert scores[soccer_user.username]['lost'] == 0
