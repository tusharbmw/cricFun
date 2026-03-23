"""
Tests for the notifications app:
  - Notification API endpoints (list, unread-count, mark-read, clear, delete)
  - PushSubscription API (save, remove)
  - send_custom_notification task
  - send_pick_reminders task (24h and 1h windows, dedup via cache)
"""
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.test import APIClient

from django.core.cache import cache

from teams.models import Match, Team, Selection
from apps.notifications.models import Notification, PushSubscription


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()
    yield
    cache.clear()


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

NOTIF_LIST_URL       = '/api/v1/notifications/'
UNREAD_COUNT_URL     = '/api/v1/notifications/unread-count/'
MARK_READ_URL        = '/api/v1/notifications/mark-read/'
CLEAR_URL            = '/api/v1/notifications/clear/'
PUSH_URL             = '/api/v1/notifications/push/'


def _auth_client(user):
    client = APIClient()
    token = RefreshToken.for_user(user)
    client.credentials(HTTP_AUTHORIZATION=f'Bearer {token.access_token}')
    return client


def _make_notification(user, message='Test', ntype='rank_change', is_read=False):
    return Notification.objects.create(
        user=user, type=ntype, message=message, is_read=is_read
    )


def _make_push_sub(user, endpoint='https://push.example.com/sub1'):
    return PushSubscription.objects.create(
        user=user, endpoint=endpoint, p256dh='key', auth='authkey'
    )


# ---------------------------------------------------------------------------
# Notification list
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_notification_list_requires_auth(api_client):
    response = api_client.get(NOTIF_LIST_URL)
    assert response.status_code == 401


@pytest.mark.django_db
def test_notification_list_returns_own_notifications(user, user2):
    _make_notification(user,  'For user 1')
    _make_notification(user2, 'For user 2')

    client = _auth_client(user)
    response = client.get(NOTIF_LIST_URL)

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]['message'] == 'For user 1'


@pytest.mark.django_db
def test_notification_list_max_20(user):
    for i in range(25):
        _make_notification(user, f'msg {i}')

    client = _auth_client(user)
    response = client.get(NOTIF_LIST_URL)

    assert response.status_code == 200
    assert len(response.data) == 20


@pytest.mark.django_db
def test_notification_list_fields(user):
    _make_notification(user, 'Hello')
    client = _auth_client(user)
    data = client.get(NOTIF_LIST_URL).data[0]

    for field in ('id', 'type', 'message', 'is_read', 'created_at', 'meta'):
        assert field in data


# ---------------------------------------------------------------------------
# Unread count
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_unread_count_zero_when_none(user):
    client = _auth_client(user)
    response = client.get(UNREAD_COUNT_URL)
    assert response.status_code == 200
    assert response.data['count'] == 0


@pytest.mark.django_db
def test_unread_count_correct(user):
    _make_notification(user, 'unread 1', is_read=False)
    _make_notification(user, 'unread 2', is_read=False)
    _make_notification(user, 'read',     is_read=True)

    client = _auth_client(user)
    response = client.get(UNREAD_COUNT_URL)
    assert response.data['count'] == 2


@pytest.mark.django_db
def test_unread_count_only_own_user(user, user2):
    _make_notification(user2, 'other user unread', is_read=False)

    client = _auth_client(user)
    response = client.get(UNREAD_COUNT_URL)
    assert response.data['count'] == 0


# ---------------------------------------------------------------------------
# Mark read
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_mark_read_marks_all_unread(user):
    _make_notification(user, 'a', is_read=False)
    _make_notification(user, 'b', is_read=False)

    client = _auth_client(user)
    response = client.post(MARK_READ_URL)

    assert response.status_code == 200
    assert response.data['marked'] == 2
    assert Notification.objects.filter(user=user, is_read=False).count() == 0


@pytest.mark.django_db
def test_mark_read_does_not_affect_other_user(user, user2):
    _make_notification(user2, 'other', is_read=False)

    client = _auth_client(user)
    client.post(MARK_READ_URL)

    assert Notification.objects.filter(user=user2, is_read=False).count() == 1


# ---------------------------------------------------------------------------
# Clear all
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_clear_deletes_all_own_notifications(user):
    _make_notification(user, 'a')
    _make_notification(user, 'b')

    client = _auth_client(user)
    response = client.delete(CLEAR_URL)

    assert response.status_code == 200
    assert response.data['deleted'] == 2
    assert Notification.objects.filter(user=user).count() == 0


@pytest.mark.django_db
def test_clear_does_not_delete_other_user_notifications(user, user2):
    _make_notification(user2, 'keep')

    client = _auth_client(user)
    client.delete(CLEAR_URL)

    assert Notification.objects.filter(user=user2).count() == 1


# ---------------------------------------------------------------------------
# Delete single notification
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_delete_single_notification(user):
    n = _make_notification(user, 'bye')
    client = _auth_client(user)
    response = client.delete(f'/api/v1/notifications/{n.id}/')
    assert response.status_code == 204
    assert not Notification.objects.filter(pk=n.id).exists()


@pytest.mark.django_db
def test_delete_single_notification_not_found(user):
    client = _auth_client(user)
    response = client.delete('/api/v1/notifications/99999/')
    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_single_notification_other_user_forbidden(user, user2):
    n = _make_notification(user2, 'not mine')
    client = _auth_client(user)
    response = client.delete(f'/api/v1/notifications/{n.id}/')
    # Returns 404 — user1 cannot see user2's notifications
    assert response.status_code == 404
    assert Notification.objects.filter(pk=n.id).exists()


# ---------------------------------------------------------------------------
# Push subscription
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_push_subscribe_saves_subscription(user):
    client = _auth_client(user)
    payload = {
        'subscription': {
            'endpoint': 'https://push.example.com/abc',
            'keys': {'p256dh': 'pubkey', 'auth': 'authval'},
        }
    }
    response = client.post(PUSH_URL, payload, format='json')
    assert response.status_code == 200
    assert PushSubscription.objects.filter(user=user).count() == 1


@pytest.mark.django_db
def test_push_subscribe_invalid_data_returns_400(user):
    client = _auth_client(user)
    response = client.post(PUSH_URL, {'subscription': {}}, format='json')
    assert response.status_code == 400


@pytest.mark.django_db
def test_push_unsubscribe_removes_subscription(user):
    sub = _make_push_sub(user)
    client = _auth_client(user)
    response = client.delete(PUSH_URL, {'endpoint': sub.endpoint}, format='json')
    assert response.status_code == 200
    assert not PushSubscription.objects.filter(pk=sub.id).exists()


@pytest.mark.django_db
def test_push_subscribe_updates_existing_endpoint(user, user2):
    """Same endpoint re-subscribed should update user, not create duplicate."""
    endpoint = 'https://push.example.com/shared'
    _make_push_sub(user, endpoint=endpoint)

    client = _auth_client(user2)
    payload = {
        'subscription': {
            'endpoint': endpoint,
            'keys': {'p256dh': 'newkey', 'auth': 'newauth'},
        }
    }
    client.post(PUSH_URL, payload, format='json')

    assert PushSubscription.objects.filter(endpoint=endpoint).count() == 1


# ---------------------------------------------------------------------------
# send_custom_notification task
# ---------------------------------------------------------------------------

@pytest.mark.django_db
def test_send_custom_notification_creates_in_app(user, user2):
    from apps.notifications.tasks import send_custom_notification

    with patch('apps.notifications.utils.send_push_notification', return_value=False):
        result = send_custom_notification(
            'Hello', 'Test message', '/', [user.id, user2.id]
        )

    assert Notification.objects.filter(type='custom').count() == 2
    assert result['in_app'] == 2


@pytest.mark.django_db
def test_send_custom_notification_skips_inactive_user(user, user2):
    from apps.notifications.tasks import send_custom_notification

    user2.is_active = False
    user2.save()

    with patch('apps.notifications.utils.send_push_notification', return_value=False):
        result = send_custom_notification('Hi', 'msg', '/', [user.id, user2.id])

    assert result['in_app'] == 1
    assert Notification.objects.filter(user=user2).count() == 0


@pytest.mark.django_db
def test_send_custom_notification_sends_push_to_subscribers(user, user2):
    from apps.notifications.tasks import send_custom_notification

    _make_push_sub(user)  # user has push; user2 does not

    with patch('apps.notifications.utils.send_push_notification', return_value=True) as mock_push:
        result = send_custom_notification('Hi', 'msg', '/', [user.id, user2.id])

    assert mock_push.call_count == 1
    assert result['push'] == 1


# ---------------------------------------------------------------------------
# send_pick_reminders task
# ---------------------------------------------------------------------------

@pytest.fixture
def team1(db):
    return Team.objects.create(name='Team Alpha')


@pytest.fixture
def team2(db):
    return Team.objects.create(name='Team Beta')


def _match_in(hours, team1, team2):
    """Create a TBD match starting in `hours` from now."""
    return Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) + timedelta(hours=hours),
        result='TBD', match_points=1,
    )


@pytest.mark.django_db
def test_pick_reminder_24h_sends_push(user, team1, team2):
    from apps.notifications.tasks import send_pick_reminders

    _match_in(24, team1, team2)
    _make_push_sub(user)

    with patch('apps.notifications.utils.send_push_notification', return_value=True) as mock_push:
        result = send_pick_reminders()

    assert mock_push.call_count == 1
    assert result['sent'] == 1


@pytest.mark.django_db
def test_pick_reminder_1h_sends_push(user, team1, team2):
    from apps.notifications.tasks import send_pick_reminders

    _match_in(1, team1, team2)
    _make_push_sub(user)

    with patch('apps.notifications.utils.send_push_notification', return_value=True) as mock_push:
        result = send_pick_reminders()

    assert mock_push.call_count == 1
    assert result['sent'] == 1


@pytest.mark.django_db
def test_pick_reminder_skips_user_who_already_picked(user, team1, team2):
    from apps.notifications.tasks import send_pick_reminders

    match = _match_in(24, team1, team2)
    Selection.objects.create(user=user, match=match, selection=team1)
    _make_push_sub(user)

    with patch('apps.notifications.utils.send_push_notification', return_value=True) as mock_push:
        result = send_pick_reminders()

    assert mock_push.call_count == 0
    assert result['sent'] == 0


@pytest.mark.django_db
def test_pick_reminder_skips_user_without_push_sub(user, team1, team2):
    from apps.notifications.tasks import send_pick_reminders

    _match_in(24, team1, team2)
    # No PushSubscription for user

    with patch('apps.notifications.utils.send_push_notification', return_value=True) as mock_push:
        result = send_pick_reminders()

    assert mock_push.call_count == 0
    assert result['sent'] == 0


@pytest.mark.django_db
def test_pick_reminder_dedup_via_cache(user, team1, team2):
    """Running the task twice should not send duplicate reminders."""
    from apps.notifications.tasks import send_pick_reminders

    _match_in(24, team1, team2)
    _make_push_sub(user)

    with patch('apps.notifications.utils.send_push_notification', return_value=True) as mock_push:
        send_pick_reminders()
        send_pick_reminders()  # second run — cache hit, should not resend

    assert mock_push.call_count == 1


@pytest.mark.django_db
def test_pick_reminder_ignores_past_matches(user, team1, team2):
    from apps.notifications.tasks import send_pick_reminders

    # Match started 1 hour ago — already locked
    Match.objects.create(
        team1=team1, team2=team2,
        datetime=datetime.now(timezone.utc) - timedelta(hours=1),
        result='TBD', match_points=1,
    )
    _make_push_sub(user)

    with patch('apps.notifications.utils.send_push_notification', return_value=True) as mock_push:
        result = send_pick_reminders()

    assert mock_push.call_count == 0
    assert result['sent'] == 0
