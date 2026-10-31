"""Tests for the Chunk 7.22 Redis-backed rate-limit coordinator.

Unit tests use ``fakeredis[lua]`` as an in-process Redis double. All
tests run deterministically without a real Redis server.

Integration tests against a REAL Redis server are gated on the
``ARXIV_TEST_REDIS_URL`` environment variable. When unset, those tests
skip with an explanatory reason.

Determinism trick for gap-behavior tests: fakeredis's ``TIME`` command
uses the real system clock, so we cannot fake "3 seconds elapsed"
without actually waiting. Instead, we prime the Redis ``last_ms`` key
to a timestamp in the past before acquire; the coordinator then sees
the gap as already satisfied.
"""
from __future__ import annotations

import os
import threading
import time
from typing import List
from unittest.mock import MagicMock

import pytest


fakeredis = pytest.importorskip("fakeredis")
redis = pytest.importorskip("redis")  # noqa: F401

from nlp_semantic.ingestion.rate_limit import (  # noqa: E402
    COORDINATOR_URL_ENV_VAR,
    MIN_REQUEST_SPACING_SECONDS,
    ArxivRateLimiter,
    RateLimitAcquireTimeoutError,
    RateLimitCoordinator,
    RateLimitCoordinatorUnavailableError,
    RedisCoordinator,
    _DEFAULT_COORDINATOR,
    _reset_default_coordinator_for_testing,
    make_coordinator_from_env,
)


# ---- Fixtures ---------------------------------------------------------------


@pytest.fixture
def fake_redis_client():
    """A fresh fakeredis instance with Lua support, per test."""
    client = fakeredis.FakeRedis(decode_responses=True)
    yield client
    client.flushdb()


@pytest.fixture(autouse=True)
def _reset_default_coord():
    _reset_default_coordinator_for_testing()
    yield
    _reset_default_coordinator_for_testing()


# ---- Protocol conformance ---------------------------------------------------


class TestProtocolConformance:
    def test_redis_coordinator_satisfies_protocol(self, fake_redis_client):
        coord = RedisCoordinator(fake_redis_client)
        assert isinstance(coord, RateLimitCoordinator)

    def test_facade_accepts_redis_coordinator_via_protocol(
        self, fake_redis_client
    ):
        # The current Chunk 7.20 ArxivRateLimiter facade does NOT yet
        # accept a `coordinator=` kwarg (that is a separate backward-
        # compat extension point). This test asserts the shape instead:
        # a RedisCoordinator exposes the same three attributes the
        # facade reads.
        coord = RedisCoordinator(fake_redis_client)
        assert isinstance(coord.min_spacing_seconds, float)
        assert coord.min_spacing_seconds >= MIN_REQUEST_SPACING_SECONDS
        assert coord.last_acquire_time is None
        # acquire() returns a context manager
        with coord.acquire():
            pass
        assert coord.last_acquire_time is not None


# ---- Initialization and configuration validation ----------------------------


class TestInitialization:
    def test_default_initialization_ok(self, fake_redis_client):
        c = RedisCoordinator(fake_redis_client)
        assert c.min_spacing_seconds == 3.0

    def test_min_spacing_below_minimum_rejected(self, fake_redis_client):
        with pytest.raises(ValueError, match=r"must be >= .*3\.0"):
            RedisCoordinator(fake_redis_client, min_spacing_seconds=2.9)

    def test_lock_ttl_must_exceed_min_spacing(self, fake_redis_client):
        with pytest.raises(ValueError, match="lock_ttl_seconds must exceed"):
            RedisCoordinator(
                fake_redis_client,
                lock_ttl_seconds=3.0,  # == min_spacing
            )

    def test_max_attempts_must_be_positive(self, fake_redis_client):
        with pytest.raises(ValueError, match="max_attempts"):
            RedisCoordinator(fake_redis_client, max_attempts=0)

    def test_locked_backoff_must_be_positive(self, fake_redis_client):
        with pytest.raises(ValueError, match="locked_backoff"):
            RedisCoordinator(fake_redis_client, locked_backoff_seconds=0)

    def test_key_prefix_must_be_non_empty(self, fake_redis_client):
        with pytest.raises(ValueError, match="key_prefix"):
            RedisCoordinator(fake_redis_client, key_prefix="")

    def test_custom_key_prefix_used(self, fake_redis_client):
        c = RedisCoordinator(fake_redis_client, key_prefix="custom:ns:")
        with c.acquire():
            pass
        assert fake_redis_client.exists("custom:ns:last_ms") == 1


# ---- Atomic acquire + release -----------------------------------------------


class TestAcquireRelease:
    def test_acquire_sets_last_ms_and_releases_lock(self, fake_redis_client):
        c = RedisCoordinator(fake_redis_client)
        with c.acquire():
            # Lock held while inside the body
            assert fake_redis_client.exists("arxiv:rate:lock") == 1
        # Released on exit
        assert fake_redis_client.exists("arxiv:rate:lock") == 0
        assert fake_redis_client.exists("arxiv:rate:last_ms") == 1

    def test_last_ms_has_ttl(self, fake_redis_client):
        c = RedisCoordinator(fake_redis_client)
        with c.acquire():
            pass
        ttl = fake_redis_client.pttl("arxiv:rate:last_ms")
        # TTL = min_spacing_ms * 10 = 30_000 ms
        assert 25_000 < ttl <= 30_000

    def test_release_is_token_scoped(self, fake_redis_client):
        """A second coordinator cannot inadvertently release the first's lock."""
        c1 = RedisCoordinator(fake_redis_client)
        with c1.acquire():
            # Simulate c2 trying to release — write a different token
            # directly (we don't expose this normally; this is a
            # structural test).
            fake_redis_client.set("arxiv:rate:lock", "attacker_token", px=10_000)
            # c1's acquire context will try to release at exit using
            # ITS token, which no longer matches. Release script
            # returns 0; no exception. The attacker's token remains.
        assert fake_redis_client.get("arxiv:rate:lock") == "attacker_token"


# ---- Gap enforcement (deterministic via priming last_ms) -------------------


class TestGapEnforcement:
    def test_gap_already_satisfied_yields_no_sleep(self, fake_redis_client):
        # Prime last_ms with a timestamp 10 s in the past (per Redis TIME).
        now_s, now_us = fake_redis_client.time()
        now_ms = int(now_s) * 1000 + int(now_us) // 1000
        fake_redis_client.set("arxiv:rate:last_ms", str(now_ms - 10_000), px=60_000)
        sleeps: List[float] = []
        c = RedisCoordinator(
            fake_redis_client, sleeper=lambda d: sleeps.append(d)
        )
        with c.acquire():
            pass
        # Zero sleeps because deficit is -7000 ms (negative → success).
        assert sleeps == []

    def test_gap_not_satisfied_sleeps_and_retries(self, fake_redis_client):
        # Prime last_ms to NOW; the coordinator should sleep for ~3000 ms
        # on the first attempt. Our sleeper is a no-op that advances
        # Redis's clock mock... BUT fakeredis TIME is real; we cannot
        # fake it without lupa internals. We can, however, assert that
        # at least one deficit-sleep call occurs before max_attempts
        # exhaustion.
        now_s, now_us = fake_redis_client.time()
        now_ms = int(now_s) * 1000 + int(now_us) // 1000
        fake_redis_client.set("arxiv:rate:last_ms", str(now_ms), px=60_000)
        sleeps: List[float] = []
        c = RedisCoordinator(
            fake_redis_client,
            max_attempts=3,
            sleeper=lambda d: sleeps.append(d),
        )
        with pytest.raises(RateLimitAcquireTimeoutError):
            with c.acquire():
                pass
        # Each attempt should have produced a deficit sleep in the
        # 0..3000 ms range (converted to seconds).
        assert len(sleeps) >= 1
        for s in sleeps:
            assert 0 <= s <= 3.0


# ---- Concurrent acquisition (lock mutual exclusion within Redis) -----------


class TestConcurrency:
    def test_two_coordinators_cannot_both_hold_lock(self, fake_redis_client):
        """Two separate RedisCoordinator objects sharing one fakeredis
        instance must serialize via Redis's atomic SET NX.

        Both coordinators have their own per-instance threading.Lock,
        so neither blocks the other locally. The only serialization
        comes from Redis.
        """
        c1 = RedisCoordinator(fake_redis_client)
        c2 = RedisCoordinator(
            fake_redis_client, max_attempts=3, locked_backoff_seconds=0.01
        )

        # c1 enters acquire and holds its lock
        cm1 = c1.acquire()
        cm1.__enter__()
        try:
            # c2 should hit max_attempts (lock held by c1 throughout)
            with pytest.raises(RateLimitAcquireTimeoutError):
                with c2.acquire():
                    pass
        finally:
            cm1.__exit__(None, None, None)

        # Once c1 releases, c2 can acquire. But we also need the gap to
        # be satisfied — advance it by priming last_ms to 10 s ago.
        now_s, now_us = fake_redis_client.time()
        now_ms = int(now_s) * 1000 + int(now_us) // 1000
        fake_redis_client.set("arxiv:rate:last_ms", str(now_ms - 10_000), px=60_000)
        with c2.acquire():
            pass  # succeeds

    def test_in_process_local_lock_serializes_threads(self, fake_redis_client):
        """The per-coordinator `threading.Lock` must serialize threads
        from the SAME coordinator object. The Redis-level lock
        serializes DIFFERENT coordinator objects."""
        c = RedisCoordinator(fake_redis_client)
        # Prime last_ms with a very old timestamp so there's no deficit
        now_s, now_us = fake_redis_client.time()
        now_ms = int(now_s) * 1000 + int(now_us) // 1000
        fake_redis_client.set("arxiv:rate:last_ms", str(now_ms - 60_000), px=120_000)

        active = 0
        max_active_seen = 0
        active_lock = threading.Lock()

        def worker():
            nonlocal active, max_active_seen
            # Each thread uses a fresh "primed" state; otherwise the
            # second thread hits the gap check. Reset last_ms per
            # worker.
            with active_lock:
                fake_redis_client.set(
                    "arxiv:rate:last_ms",
                    str(now_ms - 60_000),
                    px=120_000,
                )
            with c.acquire():
                with active_lock:
                    active += 1
                    max_active_seen = max(max_active_seen, active)
                time.sleep(0.005)
                with active_lock:
                    active -= 1

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert max_active_seen == 1


# ---- Exception / failure semantics -----------------------------------------


class TestExceptionSafety:
    def test_lock_released_on_body_exception(self, fake_redis_client):
        c = RedisCoordinator(fake_redis_client)

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom):
            with c.acquire():
                assert fake_redis_client.exists("arxiv:rate:lock") == 1
                raise _Boom()

        assert fake_redis_client.exists("arxiv:rate:lock") == 0

    def test_coordinator_unavailable_on_connection_failure(self):
        """When the Redis client raises on `register_script`, construction
        raises RateLimitCoordinatorUnavailableError, not a bare
        exception."""
        fake_client = MagicMock()
        fake_client.register_script.side_effect = ConnectionError(
            "simulated"
        )
        with pytest.raises(RateLimitCoordinatorUnavailableError):
            RedisCoordinator(fake_client)

    def test_coordinator_unavailable_on_acquire_failure(self, fake_redis_client):
        c = RedisCoordinator(fake_redis_client)
        # Replace the acquire script with one that always raises
        failing_script = MagicMock(side_effect=ConnectionError("boom"))
        c._acquire_script = failing_script
        with pytest.raises(RateLimitCoordinatorUnavailableError):
            with c.acquire():
                pass

    def test_no_silent_fallback_to_in_process_on_redis_error(
        self, fake_redis_client
    ):
        """A Redis failure must raise, NOT silently return a slot that
        would allow the request to proceed."""
        c = RedisCoordinator(fake_redis_client)
        c._acquire_script = MagicMock(side_effect=RuntimeError("redis down"))
        with pytest.raises(RateLimitCoordinatorUnavailableError):
            with c.acquire():
                pytest.fail(
                    "acquire context body must not execute on Redis error"
                )


# ---- Factory and configuration ---------------------------------------------


class TestFactory:
    def test_empty_env_returns_default_coordinator(self):
        c = make_coordinator_from_env(env={})
        assert c is _DEFAULT_COORDINATOR

    def test_unset_env_var_returns_default_coordinator(self):
        c = make_coordinator_from_env(env={"OTHER_VAR": "value"})
        assert c is _DEFAULT_COORDINATOR

    def test_empty_value_returns_default_coordinator(self):
        c = make_coordinator_from_env(env={COORDINATOR_URL_ENV_VAR: ""})
        assert c is _DEFAULT_COORDINATOR

    def test_whitespace_only_returns_default_coordinator(self):
        c = make_coordinator_from_env(
            env={COORDINATOR_URL_ENV_VAR: "   "}
        )
        assert c is _DEFAULT_COORDINATOR

    def test_in_process_prefix_returns_default_coordinator(self):
        c = make_coordinator_from_env(
            env={COORDINATOR_URL_ENV_VAR: "in_process:"}
        )
        assert c is _DEFAULT_COORDINATOR

    def test_unknown_scheme_raises_value_error(self):
        with pytest.raises(ValueError, match="unrecognized scheme"):
            make_coordinator_from_env(
                env={COORDINATOR_URL_ENV_VAR: "ftp://host"}
            )

    def test_unknown_scheme_does_not_leak_url_in_error(self):
        secret_url = "ftp://user:password_SHOULDNOT_LEAK@host"
        try:
            make_coordinator_from_env(
                env={COORDINATOR_URL_ENV_VAR: secret_url}
            )
            pytest.fail("expected ValueError")
        except ValueError as e:
            msg = str(e)
            assert "password_SHOULDNOT_LEAK" not in msg
            assert "ftp://user" not in msg

    def test_unreachable_redis_fail_closed_no_url_leak(self):
        secret_url = (
            "redis://user:password_SHOULDNOT_LEAK@127.0.0.1:1/0"
        )
        with pytest.raises(RateLimitCoordinatorUnavailableError) as exc_info:
            make_coordinator_from_env(
                env={COORDINATOR_URL_ENV_VAR: secret_url}
            )
        msg = str(exc_info.value)
        assert "password_SHOULDNOT_LEAK" not in msg
        assert secret_url not in msg
        # Error should mention the env var name and point to config
        assert COORDINATOR_URL_ENV_VAR in msg

    def test_env_var_name_is_the_chunk_7_21_canonical(self):
        assert COORDINATOR_URL_ENV_VAR == "ARXIV_RATE_COORDINATOR_URL"


# ---- Co-existence with the process-local limiter ---------------------------


class TestInProcessCompatibility:
    def test_process_local_limiter_still_works(self):
        """Chunk 7.22 does not break the Chunk 7.20 facade."""
        lim = ArxivRateLimiter()
        assert lim.is_shared_default is True
        with lim.acquire():
            pass
        # Second acquire should see the shared default coordinator
        # record the time (we're not asserting pacing here).

    def test_injectable_clock_and_sleeper_still_work(self):
        """Chunk 7.22 preserves the Chunk 7.18 test-isolation API."""
        calls: List[float] = []
        lim = ArxivRateLimiter(
            clock=lambda: 1000.0, sleeper=lambda d: calls.append(d)
        )
        with lim.acquire():
            pass
        with lim.acquire():
            pass
        assert calls == [3.0]  # second acquire sleeps the full gap


# ---- Integration tests (skipped unless ARXIV_TEST_REDIS_URL is set) --------


_REAL_REDIS_URL = os.environ.get("ARXIV_TEST_REDIS_URL")

requires_real_redis = pytest.mark.skipif(
    not _REAL_REDIS_URL,
    reason=(
        "ARXIV_TEST_REDIS_URL not set; Redis integration tests "
        "require a running Redis test server. Not run in this chunk."
    ),
)


@requires_real_redis
class TestRedisIntegration:  # pragma: no cover - requires real Redis
    def test_real_redis_coordinator(self):  # pragma: no cover
        import redis as redis_module
        client = redis_module.Redis.from_url(
            _REAL_REDIS_URL, decode_responses=True, socket_timeout=5.0
        )
        client.ping()
        try:
            key_prefix = "arxiv:test:chunk722:"
            # Clean up any leftovers from a previous run
            for k in client.scan_iter(f"{key_prefix}*"):
                client.delete(k)
            coord = RedisCoordinator(client, key_prefix=key_prefix)
            with coord.acquire():
                pass
            assert client.exists(f"{key_prefix}last_ms") == 1
        finally:
            for k in client.scan_iter(f"{key_prefix}*"):
                client.delete(k)
