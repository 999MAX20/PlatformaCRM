"""Dedicated ASGI SSE endpoint. Never run this stream in a WSGI worker."""
import asyncio
import contextlib
import logging
import time
from collections import Counter
from urllib.parse import parse_qs

from asgiref.sync import sync_to_async
from django.conf import settings
from django.db import close_old_connections
from redis.asyncio import Redis
from redis.exceptions import RedisError
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied
from rest_framework_simplejwt.exceptions import InvalidToken

from apps.accounts.authentication import SessionEpochJWTAuthentication
from apps.notifications.announcements import assert_announcement_manager
from apps.notifications.personal_selectors import personal_business
from apps.notifications.realtime import announcement_channel

logger = logging.getLogger(__name__)
EVENT_PATH = "/api/notifications/events/"


def authorize_connection(token, business_id):
    close_old_connections()
    try:
        auth = SessionEpochJWTAuthentication()
        actor = auth.get_user(auth.get_validated_token(token))
        business = personal_business(actor=actor, business_id=business_id)
        assert_announcement_manager(actor=actor, business=business)
        return actor.pk, business.pk
    finally:
        close_old_connections()


async def _disconnect(receive):
    while (await receive())["type"] != "http.disconnect":
        pass


async def _response(send, status):
    await send({"type": "http.response.start", "status": status, "headers": [
        (b"content-type", b"application/json"), (b"cache-control", b"no-store"),
    ]})
    await send({"type": "http.response.body", "body": b'{"detail":"Event stream unavailable."}'})


async def _event(send, name):
    await send({"type": "http.response.body", "body": f"event: {name}\ndata: {{}}\n\n".encode(),
                "more_body": True})


class AnnouncementEvents:
    # One stream per mounted management view, bounded per actor and process.
    def __init__(self, *, heartbeat=15, lifetime=300, limit=256, actor_limit=3):
        self.heartbeat = heartbeat
        self.lifetime = lifetime
        self.limit = limit
        self.actor_limit = actor_limit
        self.connections = Counter()

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        if scope["type"] != "http":
            return
        if scope.get("path") != EVENT_PATH:
            return await _response(send, 404)
        if scope.get("method") != "GET":
            return await _response(send, 405)
        if not settings.NOTIFICATION_EVENTS_ENABLED:
            return await _response(send, 503)
        try:
            params = parse_qs(scope.get("query_string", b"").decode("ascii"), keep_blank_values=True)
            values = params.get("business", [])
            if set(params) != {"business"} or len(values) != 1 or not values[0].isascii() or not values[0].isdigit():
                raise ValueError()
            business_id = int(values[0])
            if business_id <= 0:
                raise ValueError()
        except (ValueError, UnicodeError):
            return await _response(send, 400)
        headers = [value for key, value in scope.get("headers", []) if key.lower() == b"authorization"]
        if len(headers) != 1 or not headers[0].startswith(b"Bearer ") or len(headers[0]) > 8192:
            return await _response(send, 401)
        token = headers[0][7:]
        authorize = sync_to_async(authorize_connection, thread_sensitive=True)
        try:
            actor_id, _ = await authorize(token, business_id)
        except (AuthenticationFailed, InvalidToken):
            return await _response(send, 401)
        except PermissionDenied:
            return await _response(send, 403)
        if sum(self.connections.values()) >= self.limit or self.connections[actor_id] >= self.actor_limit:
            return await _response(send, 429)
        self.connections[actor_id] += 1
        disconnected = asyncio.create_task(_disconnect(receive))
        started = False
        read_task = None
        try:
            async with Redis.from_url(settings.NOTIFICATION_EVENTS_REDIS_URL,
                                      socket_connect_timeout=2, socket_timeout=self.heartbeat + 5) as redis:
                async with redis.pubsub() as subscription:
                    # Wait for subscription ACK *before* telling the browser to
                    # resync. Changes before the ACK are covered by that resync.
                    async with asyncio.timeout(3):
                        await subscription.subscribe(announcement_channel(business_id))
                        while True:
                            message = await subscription.get_message(timeout=1)
                            if message and message["type"] == "subscribe":
                                break
                    if disconnected.done():
                        return
                    await send({"type": "http.response.start", "status": 200, "headers": [
                        (b"content-type", b"text/event-stream"),
                        (b"cache-control", b"no-store"), (b"x-accel-buffering", b"no"),
                        (b"x-content-type-options", b"nosniff"),
                    ]})
                    started = True
                    await _event(send, "ready")
                    deadline = time.monotonic() + self.lifetime
                    while time.monotonic() < deadline:
                        read_task = asyncio.create_task(subscription.get_message(
                            ignore_subscribe_messages=True, timeout=self.heartbeat))
                        done, _ = await asyncio.wait([read_task, disconnected], return_when=asyncio.FIRST_COMPLETED)
                        if disconnected in done:
                            read_task.cancel()
                            with contextlib.suppress(asyncio.CancelledError, RedisError, OSError):
                                await read_task
                            read_task = None
                            return
                        completed = read_task
                        read_task = None
                        message = completed.result()
                        # Recheck signature/expiry, device revocation, active
                        # membership, owner/admin and current MANAGE on every
                        # signal and heartbeat. Never retain an authorized User.
                        try:
                            await authorize(token, business_id)
                        except (AuthenticationFailed, InvalidToken):
                            await _event(send, "reauthenticate")
                            break
                        except PermissionDenied:
                            await _event(send, "forbidden")
                            break
                        if message and message["type"] == "message":
                            await _event(send, "changed")
                        else:
                            await send({"type": "http.response.body", "body": b": keepalive\n\n", "more_body": True})
        except (RedisError, TimeoutError, OSError):
            logger.warning("announcement_stream_unavailable")
            if not started and not disconnected.done():
                await _response(send, 503)
                return
        finally:
            for task in (read_task, disconnected):
                if task is not None:
                    task.cancel()
                    with contextlib.suppress(asyncio.CancelledError, RedisError, OSError):
                        await task
            self.connections[actor_id] -= 1
            if self.connections[actor_id] == 0:
                del self.connections[actor_id]
        if started:
            with contextlib.suppress(OSError):
                await send({"type": "http.response.body", "body": b""})
