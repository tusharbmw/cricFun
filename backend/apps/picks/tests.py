"""
Tests for the picks (Selection) API.
"""
import pytest
from datetime import datetime, timezone, timedelta
from rest_framework_simplejwt.tokens import RefreshToken

from teams.models import Match, Selection, Tournament
from apps.users.models import TournamentEnrollment


PICKS_URL = '/api/v1/picks/'
ACTIVE_URL = '/api/v1/picks/active/'
STATS_URL = '/api/v1/picks/stats/'


# ---------------------------------------------------------------------------
# Authentication guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_list_requires_auth(api_client):
    response = api_client.get(PICKS_URL)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Place pick
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_place_pick(auth_client, upcoming_match, team1):
    response = auth_client.post(PICKS_URL, {
        'match': upcoming_match.id,
        'selection': team1.id,
    })
    assert response.status_code == 201
    assert Selection.objects.count() == 1


@pytest.mark.django_db
def test_cannot_pick_twice_on_same_match(auth_client, upcoming_match, team1, team2):
    auth_client.post(PICKS_URL, {'match': upcoming_match.id, 'selection': team1.id})
    response = auth_client.post(PICKS_URL, {'match': upcoming_match.id, 'selection': team2.id})
    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_pick_on_started_match(auth_client, past_match, team1):
    response = auth_client.post(PICKS_URL, {
        'match': past_match.id,
        'selection': team1.id,
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_cannot_pick_on_live_match(db, auth_client, team1, team2, tournament):
    live_match = Match.objects.create(
        team1=team1, team2=team2,
        tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(minutes=30),
        result='IP',
    )
    response = auth_client.post(PICKS_URL, {'match': live_match.id, 'selection': team1.id})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Update pick
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_update_pick_selection(auth_client, selection, team2):
    url = f'{PICKS_URL}{selection.id}/'
    response = auth_client.patch(url, {'selection': team2.id})
    assert response.status_code == 200
    selection.refresh_from_db()
    assert selection.selection == team2


@pytest.mark.django_db
def test_cannot_update_another_users_pick(db, api_client, user2, selection, team2):
    refresh = RefreshToken.for_user(user2)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    url = f'{PICKS_URL}{selection.id}/'
    response = api_client.patch(url, {'selection': team2.id})
    assert response.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Remove pick
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_remove_pick(auth_client, selection):
    url = f'{PICKS_URL}{selection.id}/'
    response = auth_client.delete(url)
    assert response.status_code == 204
    assert Selection.objects.count() == 0


@pytest.mark.django_db
def test_cannot_remove_pick_with_powerup(auth_client, selection):
    selection.hidden = True
    selection.save()
    url = f'{PICKS_URL}{selection.id}/'
    response = auth_client.delete(url)
    assert response.status_code == 400
    assert Selection.objects.count() == 1


# ---------------------------------------------------------------------------
# Active picks
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_active_picks_includes_tbd(auth_client, selection):
    response = auth_client.get(ACTIVE_URL)
    assert response.status_code == 200
    ids = [b['id'] for b in response.data]
    assert selection.id in ids


@pytest.mark.django_db
def test_active_picks_excludes_completed(db, auth_client, user, completed_match_team1_won, team1):
    Selection.objects.create(user=user, match=completed_match_team1_won, selection=team1)
    response = auth_client.get(ACTIVE_URL)
    assert response.status_code == 200
    assert len(response.data) == 0


# ---------------------------------------------------------------------------
# Stats endpoint
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_stats_returns_powerup_counts(auth_client):
    response = auth_client.get(STATS_URL)
    assert response.status_code == 200
    data = response.data
    assert 'hidden_count' in data
    assert 'fake_count' in data
    assert 'no_negative_count' in data
    assert 'missing_picks' in data


# ---------------------------------------------------------------------------
# Powerup toggle
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_apply_powerup(auth_client, selection):
    url = f'{PICKS_URL}{selection.id}/powerup/'
    response = auth_client.post(url, {'powerup_type': 'hidden'})
    assert response.status_code == 200
    selection.refresh_from_db()
    assert selection.hidden is True


@pytest.mark.django_db
def test_toggle_powerup_off(auth_client, selection):
    selection.hidden = True
    selection.save()
    url = f'{PICKS_URL}{selection.id}/powerup/'
    response = auth_client.post(url, {'powerup_type': 'hidden'})
    assert response.status_code == 200
    selection.refresh_from_db()
    assert selection.hidden is False


@pytest.mark.django_db
def test_cannot_apply_second_powerup(auth_client, selection):
    selection.hidden = True
    selection.save()
    url = f'{PICKS_URL}{selection.id}/powerup/'
    response = auth_client.post(url, {'powerup_type': 'fake'})
    assert response.status_code == 400


@pytest.mark.django_db
def test_powerup_locked_after_match_starts(db, auth_client, user, team1, team2, tournament):
    past = Match.objects.create(
        team1=team1, team2=team2,
        tournament=tournament,
        datetime=datetime.now(timezone.utc) - timedelta(hours=1),
        result='TBD',
    )
    sel = Selection.objects.create(user=user, match=past, selection=team1)
    url = f'{PICKS_URL}{sel.id}/powerup/'
    response = auth_client.post(url, {'powerup_type': 'hidden'})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Soccer — draw pick validation
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_soccer_draw_pick_accepted_in_group_stage(
    api_client, soccer_user, soccer_tournament, soccer_group_match
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    response = api_client.post(PICKS_URL, {
        'match': soccer_group_match.id,
        'draw': True,
    })
    assert response.status_code == 201
    sel = Selection.objects.get()
    assert sel.draw is True
    assert sel.selection is None


@pytest.mark.django_db
def test_cricket_draw_pick_rejected(auth_client, upcoming_match):
    response = auth_client.post(PICKS_URL, {
        'match': upcoming_match.id,
        'draw': True,
    })
    assert response.status_code == 400


@pytest.mark.django_db
def test_soccer_draw_pick_rejected_in_knockout(
    api_client, soccer_user, soccer_tournament, soccer_qf_match
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    response = api_client.post(PICKS_URL, {
        'match': soccer_qf_match.id,
        'draw': True,
    })
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Soccer — hidden auto-applied at QF+
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_soccer_qf_pick_is_auto_hidden(
    api_client, soccer_user, soccer_tournament, soccer_qf_match, team1
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    response = api_client.post(PICKS_URL, {
        'match': soccer_qf_match.id,
        'selection': team1.id,
    })
    assert response.status_code == 201
    sel = Selection.objects.get()
    assert sel.hidden is True


# ---------------------------------------------------------------------------
# Soccer — powerups blocked at QF+
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_powerup_blocked_at_soccer_qf(
    api_client, soccer_user, soccer_tournament, soccer_qf_match, team1
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.post(PICKS_URL, {'match': soccer_qf_match.id, 'selection': team1.id})
    sel = Selection.objects.get()
    url = f'{PICKS_URL}{sel.id}/powerup/'
    response = api_client.post(url, {'powerup_type': 'no_negative'})
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Soccer — fake powerup requires decoy choice
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_soccer_fake_powerup_requires_decoy(
    api_client, soccer_user, soccer_tournament, soccer_group_match, team1
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.post(PICKS_URL, {'match': soccer_group_match.id, 'selection': team1.id})
    sel = Selection.objects.get()
    url = f'{PICKS_URL}{sel.id}/powerup/'
    # No fake_selection_id or fake_draw provided
    response = api_client.post(url, {'powerup_type': 'fake'})
    assert response.status_code == 400


@pytest.mark.django_db
def test_soccer_fake_powerup_with_team_decoy(
    api_client, soccer_user, soccer_tournament, soccer_group_match, team1, team2
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.post(PICKS_URL, {'match': soccer_group_match.id, 'selection': team1.id})
    sel = Selection.objects.get()
    url = f'{PICKS_URL}{sel.id}/powerup/'
    response = api_client.post(url, {
        'powerup_type': 'fake',
        'fake_selection_id': team2.id,
    })
    assert response.status_code == 200
    sel.refresh_from_db()
    assert sel.fake is True
    assert sel.fake_selection == team2
    assert sel.fake_draw is False


@pytest.mark.django_db
def test_soccer_fake_powerup_with_draw_decoy(
    api_client, soccer_user, soccer_tournament, soccer_group_match, team1
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.post(PICKS_URL, {'match': soccer_group_match.id, 'selection': team1.id})
    sel = Selection.objects.get()
    url = f'{PICKS_URL}{sel.id}/powerup/'
    response = api_client.post(url, {
        'powerup_type': 'fake',
        'fake_draw': True,
    })
    assert response.status_code == 200
    sel.refresh_from_db()
    assert sel.fake is True
    assert sel.fake_draw is True
    assert sel.fake_selection is None


@pytest.mark.django_db
def test_soccer_fake_powerup_toggle_off_clears_decoy(
    api_client, soccer_user, soccer_tournament, soccer_group_match, team1, team2
):
    refresh = RefreshToken.for_user(soccer_user)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    api_client.post(PICKS_URL, {'match': soccer_group_match.id, 'selection': team1.id})
    sel = Selection.objects.get()
    url = f'{PICKS_URL}{sel.id}/powerup/'
    api_client.post(url, {'powerup_type': 'fake', 'fake_selection_id': team2.id})
    # Toggle off
    api_client.post(url, {'powerup_type': 'fake'})
    sel.refresh_from_db()
    assert sel.fake is False
    assert sel.fake_selection is None
    assert sel.fake_draw is False


# ---------------------------------------------------------------------------
# Enrollment guard
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_cannot_pick_without_tournament_enrollment(
    api_client, soccer_tournament, soccer_group_match, team1
):
    """User not enrolled in the tournament cannot place a pick."""
    unenrolled = Match._default_manager.model  # just to get a user
    from django.contrib.auth.models import User
    u = User.objects.create_user(username='outsider', password='testpass123')
    refresh = RefreshToken.for_user(u)
    api_client.credentials(HTTP_AUTHORIZATION=f'Bearer {refresh.access_token}')
    response = api_client.post(PICKS_URL, {
        'match': soccer_group_match.id,
        'selection': team1.id,
    })
    assert response.status_code in (400, 403)
