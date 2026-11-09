import asyncio
from datetime import timedelta
from unittest.mock import patch

from django.test import SimpleTestCase, TransactionTestCase, override_settings
from django.utils import timezone
from redis.exceptions import ConnectionError as RedisConnectionError
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.exceptions import InvalidToken
from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import AccountSession
from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
from apps.notifications.event_stream import AnnouncementEvents, authorize_connection
from apps.notifications.tests_personal_services import PersonalNotificationFixtures


class StreamAuthorizationTests(PersonalNotificationFixtures, TransactionTestCase):
    def token(self, actor):
        token = AccessToken.for_user(actor)
        token["auth_epoch"] = actor.auth_epoch
        return str(token).encode()

    def test_owner_admin_only_and_business_isolation(self):
        for actor in (self.owner, self.admin):
            self.assertEqual(authorize_connection(self.token(actor), self.business.pk), (actor.pk, self.business.pk))
        for actor in (self.staff, self.marketer, self.outsider):
            with self.assertRaises(PermissionDenied):
                authorize_connection(self.token(actor), self.business.pk)
        with self.assertRaises(PermissionDenied):
            authorize_connection(self.token(self.owner), self.foreign.pk)

    def test_membership_and_user_revocation_are_rechecked(self):
        token = self.token(self.admin)
        authorize_connection(token, self.business.pk)
        BusinessMember.objects.filter(business=self.business, user=self.admin).update(is_active=False)
        with self.assertRaises(PermissionDenied):
            authorize_connection(token, self.business.pk)
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with self.assertRaises(AuthenticationFailed):
            authorize_connection(self.token(self.owner), self.business.pk)

    def test_expiry_and_auth_epoch_are_rechecked(self):
        token = AccessToken.for_user(self.owner)
        token.set_exp(from_time=timezone.now() - timedelta(days=1), lifetime=timedelta(seconds=1))
        with self.assertRaises(InvalidToken):
            authorize_connection(str(token).encode(), self.business.pk)
        raw = self.token(self.owner)
        self.owner.auth_epoch += 1
        self.owner.save(update_fields=["auth_epoch"])
        with self.assertRaises(AuthenticationFailed):
            authorize_connection(raw, self.business.pk)

    def test_current_manage_override_is_enforced(self):
        role = BusinessRole.objects.create(business=self.business, name="Denied management")
        RolePermission.objects.create(business_role=role, resource="notifications", action="manage",
                                      is_allowed=False, scope="none")
        raw = self.token(self.admin)
        authorize_connection(raw, self.business.pk)
        BusinessMember.objects.filter(business=self.business, user=self.admin).update(business_role=role)
        with self.assertRaises(PermissionDenied):
            authorize_connection(raw, self.business.pk)

    def test_device_session_revocation_is_enforced(self):
        session = AccountSession.objects.create(user=self.owner, auth_epoch=self.owner.auth_epoch,
            refresh_jti="stream-device", last_seen_at=timezone.now(), expires_at=timezone.now() + timedelta(hours=1))
        token = AccessToken.for_user(self.owner)
        token["auth_epoch"] = self.owner.auth_epoch
        token["sid"] = str(session.pk)
        raw = str(token).encode()
        authorize_connection(raw, self.business.pk)
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])
        with self.assertRaises(AuthenticationFailed):
            authorize_connection(raw, self.business.pk)


class FakeSubscription:
    def __init__(self):
        self.queue = asyncio.Queue()
        self.closed = False
        self.channel = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        self.closed = True

    async def subscribe(self, channel):
        self.channel = channel
        await self.queue.put({"type": "subscribe"})

    async def get_message(self, **kwargs):
        try:
            item = await asyncio.wait_for(self.queue.get(), kwargs.get("timeout", 1))
        except TimeoutError:
            return None
        if isinstance(item, Exception):
            raise item
        return item


class FakeRedis:
    def __init__(self):
        self.subscription = FakeSubscription()
        self.closed = False

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_args):
        self.closed = True

    def pubsub(self):
        return self.subscription


@override_settings(NOTIFICATION_EVENTS_ENABLED=True, NOTIFICATION_EVENTS_NAMESPACE="stream-test")
class StreamTransportTests(SimpleTestCase):
    def scope(self, **changes):
        return {"type": "http", "method": "GET", "path": "/api/notifications/events/",
                "query_string": b"business=4", "headers": [(b"authorization", b"Bearer synthetic")], **changes}

    async def start(self, app, scope=None):
        incoming, outgoing = asyncio.Queue(), asyncio.Queue()
        task = asyncio.create_task(app(scope or self.scope(), incoming.get, outgoing.put))
        return task, incoming, outgoing

    async def message(self, outgoing):
        return await asyncio.wait_for(outgoing.get(), 2)

    async def ready(self, outgoing):
        self.assertEqual((await self.message(outgoing))["status"], 200)
        self.assertIn(b"event: ready", (await self.message(outgoing))["body"])

    async def test_invalid_requests_rejected_without_broker_access(self):
        cases = [(self.scope(headers=[]), 401), (self.scope(query_string=b"business=4&token=secret"), 400),
                 (self.scope(query_string=b"business=4&business=5"), 400),
                 (self.scope(path="/api/clients/"), 404), (self.scope(method="POST"), 405)]
        with patch("apps.notifications.event_stream.Redis.from_url") as broker:
            for scope, status in cases:
                task, _incoming, outgoing = await self.start(AnnouncementEvents(), scope)
                await task
                self.assertEqual((await self.message(outgoing))["status"], status)
            broker.assert_not_called()

    async def test_disabled_and_denied_streams_do_not_subscribe(self):
        with self.settings(NOTIFICATION_EVENTS_ENABLED=False):
            task, _incoming, outgoing = await self.start(AnnouncementEvents())
            await task
            self.assertEqual((await self.message(outgoing))["status"], 503)
        for error, status in ((AuthenticationFailed(), 401), (PermissionDenied(), 403)):
            with patch("apps.notifications.event_stream.authorize_connection", side_effect=error), \
                 patch("apps.notifications.event_stream.Redis.from_url") as broker:
                task, _incoming, outgoing = await self.start(AnnouncementEvents())
                await task
                self.assertEqual((await self.message(outgoing))["status"], status)
                broker.assert_not_called()

    async def test_ready_after_subscription_changes_have_no_payload_and_disconnect_cleans_up(self):
        redis = FakeRedis()
        app = AnnouncementEvents()
        with patch("apps.notifications.event_stream.authorize_connection", return_value=(2, 4)) as auth, \
             patch("apps.notifications.event_stream.Redis.from_url", return_value=redis):
            task, incoming, outgoing = await self.start(app)
            await self.ready(outgoing)
            self.assertEqual(redis.subscription.channel, "stream-test:announcements:4")
            await redis.subscription.queue.put({"type": "message", "data": b"private employee data"})
            self.assertEqual((await self.message(outgoing))["body"], b"event: changed\ndata: {}\n\n")
            self.assertGreaterEqual(auth.call_count, 2)
            await incoming.put({"type": "http.disconnect"})
            await asyncio.wait_for(task, 2)
        self.assertTrue(redis.subscription.closed)
        self.assertTrue(redis.closed)
        self.assertFalse(app.connections)

    async def test_permission_revocation_closes_before_forwarding_signal(self):
        redis = FakeRedis()
        with patch("apps.notifications.event_stream.authorize_connection", side_effect=[(2, 4), PermissionDenied()]), \
             patch("apps.notifications.event_stream.Redis.from_url", return_value=redis):
            task, _incoming, outgoing = await self.start(AnnouncementEvents())
            await self.ready(outgoing)
            await redis.subscription.queue.put({"type": "message"})
            self.assertIn(b"event: forbidden", (await self.message(outgoing))["body"])
            await asyncio.wait_for(task, 2)
        self.assertTrue(redis.closed)

    async def test_heartbeat_rechecks_expiry_even_without_changes(self):
        redis = FakeRedis()
        with patch("apps.notifications.event_stream.authorize_connection", side_effect=[(2, 4), InvalidToken()]), \
             patch("apps.notifications.event_stream.Redis.from_url", return_value=redis):
            task, _incoming, outgoing = await self.start(AnnouncementEvents(heartbeat=0.01))
            await self.ready(outgoing)
            self.assertIn(b"event: reauthenticate", (await self.message(outgoing))["body"])
            await asyncio.wait_for(task, 2)

    async def test_broker_failure_then_reconnect_always_resyncs(self):
        app = AnnouncementEvents()
        with patch("apps.notifications.event_stream.authorize_connection", return_value=(2, 4)):
            with patch("apps.notifications.event_stream.Redis.from_url", side_effect=RedisConnectionError()):
                task, _incoming, outgoing = await self.start(app)
                await asyncio.wait_for(task, 2)
                self.assertEqual((await self.message(outgoing))["status"], 503)
                self.assertFalse(app.connections)
            for _attempt in range(2):
                redis = FakeRedis()
                with patch("apps.notifications.event_stream.Redis.from_url", return_value=redis):
                    task, incoming, outgoing = await self.start(app)
                    await self.ready(outgoing)
                    await incoming.put({"type": "http.disconnect"})
                    await asyncio.wait_for(task, 2)
                self.assertFalse(app.connections)

    async def test_midstream_redis_failure_releases_connection(self):
        app, redis = AnnouncementEvents(), FakeRedis()
        with patch("apps.notifications.event_stream.authorize_connection", return_value=(2, 4)), \
             patch("apps.notifications.event_stream.Redis.from_url", return_value=redis):
            task, _incoming, outgoing = await self.start(app)
            await self.ready(outgoing)
            await redis.subscription.queue.put(RedisConnectionError())
            await asyncio.wait_for(task, 2)
        self.assertFalse(app.connections)
        self.assertTrue(redis.closed)

    async def test_actor_connection_cap_rejects_excess_without_subscribing(self):
        app = AnnouncementEvents(actor_limit=1)
        app.connections[2] = 1
        with patch("apps.notifications.event_stream.authorize_connection", return_value=(2, 4)), \
             patch("apps.notifications.event_stream.Redis.from_url") as broker:
            task, _incoming, outgoing = await self.start(app)
            await task
            self.assertEqual((await self.message(outgoing))["status"], 429)
            broker.assert_not_called()
