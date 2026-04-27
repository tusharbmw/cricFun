"""
Web Push helper. Sends a push notification to a single PushSubscription.
Silently skips if pywebpush is not installed or VAPID keys are not configured.
"""
import json
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def send_push_notification(subscription, title, body, url='/', tag=None):
    """
    Send a push notification to one subscription.
    Deletes the subscription if it returns 404/410 (expired/unsubscribed).
    Returns True on success, False otherwise.
    """
    try:
        from pywebpush import WebPushException, webpush
    except ImportError:
        logger.warning('pywebpush not installed — push skipped')
        return False

    private_key = getattr(settings, 'VAPID_PRIVATE_KEY', '')
    admin_email = getattr(settings, 'VAPID_ADMIN_EMAIL', '')
    if not private_key or not admin_email:
        logger.warning('VAPID_PRIVATE_KEY / VAPID_ADMIN_EMAIL not set — push skipped')
        return False

    try:
        webpush(
            subscription_info={
                'endpoint': subscription.endpoint,
                'keys': {'p256dh': subscription.p256dh, 'auth': subscription.auth},
            },
            data=json.dumps({'title': title, 'body': body, 'url': url, 'tag': tag}),
            vapid_private_key=private_key,
            vapid_claims={'sub': f'mailto:{admin_email}'},
            ttl=3600,
        )
        return True
    except WebPushException as ex:
        if ex.response is not None and ex.response.status_code in (404, 410):
            subscription.delete()
            logger.info('Removed expired push subscription for %s', subscription.user_id)
        else:
            logger.warning('Push failed for user %s: %s', subscription.user_id, ex)
        return False
    except Exception as ex:
        logger.warning('Push error for user %s: %s', subscription.user_id, ex)
        return False
