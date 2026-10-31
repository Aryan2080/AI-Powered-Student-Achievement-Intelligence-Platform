"""Process-local arXiv rate limiter (Chunk 7.18 Rev 1 + Chunk 7.20 remediation).

Enforces the arXiv API Terms of Use access limits WITHIN A SINGLE Python
process:

  * At most one active request at a time (single-connection semantics).
  * At least 3.0 seconds between successive requests.

**Chunk 7.20 change — shared coordinator by default.** All default-
constructed :class:`ArxivRateLimiter` instances in the same process
share one module-level ``_DEFAULT_COORDINATOR``. Multiple limiter
objects therefore cannot independently bypass the aggregate gap. This
closes the Chunk 7.19 §B3 finding. Explicitly passing
``min_spacing_seconds``, ``clock``, or ``sleeper`` yields a per-instance
coordinator intended for TEST ISOLATION only; production code must
default-construct.

**Known limitation — process-local only.** This limiter cannot see or
coordinate with other OS processes, other machines, or other users'
sessions. The arXiv API Terms of Use' rate limits apply COLLECTIVELY
across every machine under the user's control; a cross-process /
cross-machine guarantee requires external coordination (a shared file
lock, a Redis mutex, a DB-backed semaphore, …) that is NOT part of this
module. The Chunk 7.19 audit explicitly classifies the global
requirement as NOT SATISFIED by this module; see
``reports/chunk_7_19_arxiv_governance_implementation_audit.md`` §5.3.

**Operator discipline required** until a cross-process coordinator is
designed and approved in a future chunk: run exactly ONE collector
process at a time, on exactly ONE machine. See
``hybrid_dataset/metadata/arxiv_governance_decisions.md``.

This module performs no network I/O. It is a timing-and-locking gate
that any future collector MUST pass through before each API request.
"""
from __future__ import annotations

import os
import secrets
import threading
import time
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from typing import Any, Callable, Final, Iterator, Protocol, runtime_checkable


#: arXiv ToU minimum request spacing (seconds).
MIN_REQUEST_SPACING_SECONDS: Final[float] = 3.0


# ---- Protocol + errors (Chunk 7.21 / 7.22) ----------------------------------


@runtime_checkable
class RateLimitCoordinator(Protocol):
    """Any object that gates arXiv requests must satisfy this shape.

    Implementations may be process-local (:class:`_ArxivCoordinator`
    plus :data:`_DEFAULT_COORDINATOR`), Redis-backed
    (:class:`RedisCoordinator`), or others. The facade
    :class:`ArxivRateLimiter` calls only ``.acquire()`` and reads
    ``.min_spacing_seconds`` / ``.last_acquire_time``.
    """

    min_spacing_seconds: float

    @property
    def last_acquire_time(self) -> float | None: ...

    def acquire(self) -> AbstractContextManager[None]: ...


class RateLimitCoordinatorUnavailableError(RuntimeError):
    """The configured coordinator cannot complete an acquisition.

    Raised by :class:`RedisCoordinator` on Redis connection failure,
    timeout, Lua-script failure, or any other backend error.
    Also raised by :func:`make_coordinator_from_env` when the
    configured URL is a Redis URL but ``redis`` is not importable or
    the server is unreachable.

    **Fail-closed semantics.** When this exception is raised, no
    request slot has been acquired; the caller MUST NOT proceed with
    its arXiv request. The caller MUST NOT fall back to the process-
    local limiter unless the configuration explicitly permits that.
    """


class RateLimitAcquireTimeoutError(RuntimeError):
    """Could not acquire a slot within the configured attempt budget."""


@dataclass
class _ArxivCoordinator:
    """Internal coordination state. One per process (shared) OR one per
    isolated test case.

    Holds the single-connection lock, the last-acquire timestamp, and
    the clock / sleeper callables used for inter-request pacing. All
    acquisitions on a given coordinator serialize against each other.
    """

    min_spacing_seconds: float
    clock: Callable[[], float]
    sleeper: Callable[[float], None]
    _lock: threading.Lock = field(default_factory=threading.Lock)
    _last_acquire_time: float | None = None

    @property
    def last_acquire_time(self) -> float | None:
        return self._last_acquire_time

    @contextmanager
    def acquire(self) -> Iterator[None]:
        """Block until the single-connection lock is held AND the gap
        from the previous acquisition is >= ``min_spacing_seconds``.

        The ``_last_acquire_time`` is updated BEFORE yielding, so an
        exception raised inside the body still leaves the coordinator
        in a state where the next acquisition respects the gap. The
        lock is always released via ``finally``.
        """
        self._lock.acquire()
        try:
            now = self.clock()
            if self._last_acquire_time is not None:
                elapsed = now - self._last_acquire_time
                deficit = self.min_spacing_seconds - elapsed
                if deficit > 0:
                    self.sleeper(deficit)
                    now = self.clock()
            self._last_acquire_time = now
            yield
        finally:
            self._lock.release()


#: Module-level default coordinator. Every default-constructed
#: :class:`ArxivRateLimiter` in this process shares this instance.
#: Multiple limiter objects therefore cannot independently bypass the
#: aggregate rate limit within one process.
_DEFAULT_COORDINATOR: _ArxivCoordinator = _ArxivCoordinator(
    min_spacing_seconds=MIN_REQUEST_SPACING_SECONDS,
    clock=time.monotonic,
    sleeper=time.sleep,
)


def _reset_default_coordinator_for_testing() -> None:
    """Reset the module-level default coordinator's acquisition history.

    TEST-ONLY. Used by test fixtures to isolate between-test state so
    that `test_default_spacing` and similar tests see a clean
    ``last_acquire_time is None``. Not part of the production API.
    """
    with _DEFAULT_COORDINATOR._lock:
        _DEFAULT_COORDINATOR._last_acquire_time = None


class ArxivRateLimiter:
    """Thread-safe, process-local arXiv rate limiter facade.

    **Default construction** (``ArxivRateLimiter()``) returns a facade
    over the module-level :data:`_DEFAULT_COORDINATOR`. All default-
    constructed instances in the same process share the single-
    connection lock and the 3-second gap. This closes the Chunk 7.19
    §B3 "two naive instances could halve the rate" finding.

    **Explicit construction with ``min_spacing_seconds``, ``clock``, or
    ``sleeper``** yields a per-instance coordinator. This is TEST
    ISOLATION ONLY — production code must default-construct.

    **Coordinator injection** (``ArxivRateLimiter(coordinator=…)``)
    forwards the facade to a caller-supplied object satisfying the
    :class:`RateLimitCoordinator` Protocol — closing Chunk 7.19 §B /
    Chunk 7.26A K10. Typical use: pair with
    :func:`make_coordinator_from_env` to let a future collector pick
    the backend (in-process default vs :class:`RedisCoordinator`)
    without touching the facade signature on its call sites.

    Rules for the ``coordinator=`` path:

    * The injected object must satisfy :class:`RateLimitCoordinator`;
      otherwise :class:`TypeError` is raised **before** any attempt
      to use it (fail-closed).
    * Its ``min_spacing_seconds`` must be ``>=
      MIN_REQUEST_SPACING_SECONDS`` (3.0); otherwise ``ValueError``.
    * ``coordinator=`` cannot be combined with
      ``min_spacing_seconds=``, ``clock=``, or ``sleeper=``; a caller
      wanting a custom clock must build the coordinator themselves
      and pass it in. Combining them raises ``ValueError``.
    * Validation failure NEVER falls back to the default
      coordinator; the construction raises and the caller never
      receives a limiter object.

    Thread-safe within one Python process. NOT process- or machine-
    safe — see module docstring and Chunk 7.19 audit §5.3.
    """

    def __init__(
        self,
        min_spacing_seconds: float | None = None,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        coordinator: RateLimitCoordinator | None = None,
    ) -> None:
        # Chunk 7.27A — coordinator-injection path.
        if coordinator is not None:
            if (
                min_spacing_seconds is not None
                or clock is not None
                or sleeper is not None
            ):
                raise ValueError(
                    "coordinator= cannot be combined with "
                    "min_spacing_seconds=, clock=, or sleeper=; build the "
                    "coordinator with those settings yourself and pass it "
                    "in as the single `coordinator=` argument."
                )
            if not isinstance(coordinator, RateLimitCoordinator):
                raise TypeError(
                    "coordinator must satisfy the RateLimitCoordinator "
                    "Protocol (min_spacing_seconds, last_acquire_time, "
                    "acquire()); got "
                    f"{type(coordinator).__name__!r}"
                )
            if coordinator.min_spacing_seconds < MIN_REQUEST_SPACING_SECONDS:
                raise ValueError(
                    "coordinator.min_spacing_seconds must be >= the arXiv "
                    f"ToU minimum of {MIN_REQUEST_SPACING_SECONDS} "
                    f"seconds; got {coordinator.min_spacing_seconds}"
                )
            self._coordinator = coordinator
            self._is_default = coordinator is _DEFAULT_COORDINATOR
            return

        isolated_test_path = (
            min_spacing_seconds is not None
            or clock is not None
            or sleeper is not None
        )
        if isolated_test_path:
            spacing = (
                min_spacing_seconds
                if min_spacing_seconds is not None
                else MIN_REQUEST_SPACING_SECONDS
            )
            if spacing < MIN_REQUEST_SPACING_SECONDS:
                raise ValueError(
                    "min_spacing_seconds must be >= the arXiv ToU minimum "
                    f"of {MIN_REQUEST_SPACING_SECONDS} seconds; got "
                    f"{spacing}"
                )
            self._coordinator = _ArxivCoordinator(
                min_spacing_seconds=float(spacing),
                clock=clock if clock is not None else time.monotonic,
                sleeper=sleeper if sleeper is not None else time.sleep,
            )
            self._is_default = False
        else:
            self._coordinator = _DEFAULT_COORDINATOR
            self._is_default = True

    @property
    def min_spacing_seconds(self) -> float:
        return self._coordinator.min_spacing_seconds

    @property
    def last_acquire_time(self) -> float | None:
        return self._coordinator.last_acquire_time

    @property
    def is_shared_default(self) -> bool:
        """True if this facade is backed by the module-level default
        coordinator (shared with every other default-constructed
        limiter in this process)."""
        return self._is_default

    @contextmanager
    def acquire(self) -> Iterator[None]:
        """Block until the shared single-connection lock is held AND the
        gap from the previous acquisition on the backing coordinator is
        at least :attr:`min_spacing_seconds` seconds.

        Delegates to the backing :class:`_ArxivCoordinator`. If this
        facade is default-constructed, the backing coordinator is the
        process-wide :data:`_DEFAULT_COORDINATOR` — every other default
        limiter in the process sees the same state.
        """
        with self._coordinator.acquire():
            yield


# ---- Chunk 7.22 — Redis-backed cross-machine coordinator -------------------


# Lua script for atomic acquisition.
#
# KEYS[1] = lock key (held while the request is in flight)
# KEYS[2] = last-acquire-time key (milliseconds since epoch, Redis time)
# ARGV[1] = min_spacing_ms (integer)
# ARGV[2] = lock_ttl_ms (integer; stale-lock safeguard)
# ARGV[3] = client token (opaque; used to safely release the lock)
# Returns a two-element array:
#   {1, 0}        — success; lock is held, timestamp updated. Caller
#                    runs its request and then invokes the release
#                    script with the same token to free the lock.
#   {0, deficit}  — gap not yet satisfied; the lock was NOT retained.
#                    Caller sleeps for `deficit` ms (converted to
#                    seconds client-side) and retries.
#   {-1, 0}       — lock already held by another client. Caller
#                    sleeps a short backoff and retries.
#
# The script uses Redis's TIME command so participating clients do not
# need synchronized local clocks for the gap computation.
_ACQUIRE_LUA = """
local now = redis.call('TIME')
local now_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
local min_spacing_ms = tonumber(ARGV[1])
local lock_ttl_ms = tonumber(ARGV[2])
local token = ARGV[3]

local acquired = redis.call('SET', KEYS[1], token, 'NX', 'PX', lock_ttl_ms)
if not acquired then
    return {-1, 0}
end

local last = redis.call('GET', KEYS[2])
if last then
    local elapsed_ms = now_ms - tonumber(last)
    if elapsed_ms < min_spacing_ms then
        local deficit_ms = min_spacing_ms - elapsed_ms
        redis.call('DEL', KEYS[1])
        return {0, deficit_ms}
    end
end

redis.call('SET', KEYS[2], tostring(now_ms), 'PX', (min_spacing_ms * 10))
return {1, 0}
"""

# Lua script for safe release: only release the lock if we still hold it.
# Prevents one client from deleting another client's lock after a
# stale-TTL expiry + re-acquisition race.
_RELEASE_LUA = """
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
else
    return 0
end
"""


class RedisCoordinator:
    """Redis-backed, cross-process + cross-machine rate-limit coordinator.

    **Chunk 7.22 implementation of the Chunk 7.21 Option C design.**

    Guarantees (when backed by a correctly-deployed Redis instance that
    all participating clients can reach):

      * **Single-connection semantics across clients.** The Lua script
        performs an atomic ``SET NX PX`` on the lock key; concurrent
        clients cannot both acquire.
      * **≥ 3-second gap across clients.** The Lua script uses Redis
        ``TIME`` as the authoritative clock, avoiding reliance on
        client-local clock synchronization.
      * **Fail-closed on backend failure.** Connection errors, timeout,
        Lua-script errors, or any Redis exception raise
        :class:`RateLimitCoordinatorUnavailableError`; the acquisition
        does NOT silently fall back to local-only coordination.
      * **Bounded retry.** The retry loop is capped by ``max_attempts``;
        exhaustion raises :class:`RateLimitAcquireTimeoutError`.

    **Not guaranteed:**

      * Protection against Redis itself failing in a split-brain or
        asymmetric network partition. For stronger multi-master
        guarantees the project would need the Redlock algorithm across
        multiple independent Redis masters; this is out of scope.
      * Perfect fairness between competing clients. The locked-backoff
        is uniform and not jittered; a client with lower local jitter
        may acquire more often.

    **Clock + sleeper injection.** ``clock`` and ``sleeper`` are used
    for local-side timing (deficit sleep, locked-backoff sleep). The
    AUTHORITATIVE clock for the gap computation is Redis ``TIME``
    inside the Lua script. The ``last_acquire_time`` attribute is a
    client-local, monotonic-clock view intended for introspection and
    logging; it is NOT the authoritative shared state.

    The coordinator holds a local :class:`threading.Lock` so concurrent
    threads within one process do not thrash Redis with SETNX from
    multiple threads. This is a per-process optimization; it does not
    weaken the cross-process / cross-machine guarantees.
    """

    DEFAULT_KEY_PREFIX: Final[str] = "arxiv:rate:"
    DEFAULT_LOCK_TTL_SECONDS: Final[float] = 10.0
    DEFAULT_MAX_ATTEMPTS: Final[int] = 40
    DEFAULT_LOCKED_BACKOFF_SECONDS: Final[float] = 0.25

    def __init__(
        self,
        redis_client: Any,
        *,
        min_spacing_seconds: float = MIN_REQUEST_SPACING_SECONDS,
        key_prefix: str = DEFAULT_KEY_PREFIX,
        lock_ttl_seconds: float = DEFAULT_LOCK_TTL_SECONDS,
        max_attempts: int = DEFAULT_MAX_ATTEMPTS,
        locked_backoff_seconds: float = DEFAULT_LOCKED_BACKOFF_SECONDS,
        clock: Callable[[], float] = time.monotonic,
        sleeper: Callable[[float], None] = time.sleep,
    ) -> None:
        if min_spacing_seconds < MIN_REQUEST_SPACING_SECONDS:
            raise ValueError(
                "min_spacing_seconds must be >= the arXiv ToU minimum "
                f"of {MIN_REQUEST_SPACING_SECONDS} seconds; got "
                f"{min_spacing_seconds}"
            )
        if lock_ttl_seconds <= min_spacing_seconds:
            raise ValueError(
                "lock_ttl_seconds must exceed min_spacing_seconds so a "
                "slow request body does not race its own stale-lock "
                f"TTL; got lock_ttl={lock_ttl_seconds}, "
                f"min_spacing={min_spacing_seconds}"
            )
        if max_attempts < 1:
            raise ValueError("max_attempts must be >= 1")
        if locked_backoff_seconds <= 0:
            raise ValueError("locked_backoff_seconds must be > 0")
        if not key_prefix:
            raise ValueError("key_prefix must be a non-empty string")

        self._redis = redis_client
        self.min_spacing_seconds: float = float(min_spacing_seconds)
        self._lock_key = f"{key_prefix}lock"
        self._last_key = f"{key_prefix}last_ms"
        self._lock_ttl_ms = int(lock_ttl_seconds * 1000)
        self._min_spacing_ms = int(self.min_spacing_seconds * 1000)
        self._max_attempts = int(max_attempts)
        self._locked_backoff = float(locked_backoff_seconds)
        self._clock = clock
        self._sleeper = sleeper
        self._local_lock = threading.Lock()
        self._last_acquire_time: float | None = None

        try:
            self._acquire_script = redis_client.register_script(
                _ACQUIRE_LUA
            )
            self._release_script = redis_client.register_script(
                _RELEASE_LUA
            )
        except Exception as e:  # pragma: no cover - defensive
            raise RateLimitCoordinatorUnavailableError(
                "failed to register Lua scripts on the Redis client "
                f"({type(e).__name__})"
            ) from e

    @property
    def last_acquire_time(self) -> float | None:
        """Client-local view of the most recent successful acquisition
        (monotonic-clock seconds). Introspection only; the
        authoritative shared state lives in Redis."""
        return self._last_acquire_time

    @contextmanager
    def acquire(self) -> Iterator[None]:
        """Acquire the shared rate-limit slot.

        Blocks until BOTH the shared lock is held AND the shared
        timestamp indicates at least :attr:`min_spacing_seconds` have
        elapsed since the previous successful acquisition.

        Raises:
            RateLimitCoordinatorUnavailableError: Redis call failed.
            RateLimitAcquireTimeoutError: ``max_attempts`` exhausted.

        **Fail-closed:** on any Redis error, this method raises and
        the caller does NOT get a slot. It does NOT fall back to the
        process-local coordinator.
        """
        with self._local_lock:
            token = secrets.token_hex(16)
            attempts = 0
            acquired = False
            try:
                while True:
                    attempts += 1
                    if attempts > self._max_attempts:
                        raise RateLimitAcquireTimeoutError(
                            "could not acquire rate-limit slot after "
                            f"{self._max_attempts} attempts"
                        )
                    try:
                        result = self._acquire_script(
                            keys=[self._lock_key, self._last_key],
                            args=[
                                str(self._min_spacing_ms),
                                str(self._lock_ttl_ms),
                                token,
                            ],
                        )
                    except Exception as e:
                        raise RateLimitCoordinatorUnavailableError(
                            "Redis acquire failed "
                            f"({type(e).__name__})"
                        ) from e
                    status = int(result[0])
                    deficit_ms = int(result[1])
                    if status == 1:
                        self._last_acquire_time = self._clock()
                        acquired = True
                        break
                    if status == 0:
                        self._sleeper(deficit_ms / 1000.0)
                        continue
                    # status == -1: lock held by someone else
                    self._sleeper(self._locked_backoff)
                try:
                    yield
                finally:
                    if acquired:
                        try:
                            self._release_script(
                                keys=[self._lock_key], args=[token]
                            )
                        except Exception:
                            # Lock will expire via TTL. Do not raise
                            # during cleanup; caller may already be
                            # mid-cleanup of its own.
                            pass
            except RateLimitCoordinatorUnavailableError:
                raise
            except RateLimitAcquireTimeoutError:
                raise


# ---- Chunk 7.22 — environment-based coordinator factory --------------------


_IN_PROCESS_URL_PREFIXES: Final[tuple[str, ...]] = ("in_process:",)
_REDIS_URL_PREFIXES: Final[tuple[str, ...]] = ("redis://", "rediss://")

#: Canonical environment variable name per Chunk 7.21 §7.3.
COORDINATOR_URL_ENV_VAR: Final[str] = "ARXIV_RATE_COORDINATOR_URL"


def make_coordinator_from_env(
    env: dict | None = None,
    env_var: str = COORDINATOR_URL_ENV_VAR,
) -> RateLimitCoordinator:
    """Return the configured coordinator per :data:`COORDINATOR_URL_ENV_VAR`.

    Rules:

    - Unset or empty value → process-local :data:`_DEFAULT_COORDINATOR`.
    - Starts with ``in_process:`` → process-local
      :data:`_DEFAULT_COORDINATOR` (explicit opt-in).
    - Starts with ``redis://`` or ``rediss://`` → :class:`RedisCoordinator`.
    - Anything else → ``ValueError`` (the invalid value is **not**
      included in the error message; it may contain credentials).

    When a Redis URL is explicitly configured:

    - ``redis`` must be importable (added as a project dependency in
      Chunk 7.22). If import fails, this function raises
      :class:`RateLimitCoordinatorUnavailableError`.
    - A ``PING`` is sent during construction. On any error, this
      function raises :class:`RateLimitCoordinatorUnavailableError`
      and the error message **does not** include the URL
      (fail-closed; no credential leakage).
    - This function NEVER silently falls back to the process-local
      coordinator when a Redis URL was explicitly configured.
    """
    environ = env if env is not None else os.environ
    url = (environ.get(env_var) or "").strip()
    if not url or url.startswith(_IN_PROCESS_URL_PREFIXES):
        return _DEFAULT_COORDINATOR
    if url.startswith(_REDIS_URL_PREFIXES):
        try:
            import redis as _redis_module  # type: ignore[import-not-found]
        except ImportError as e:
            raise RateLimitCoordinatorUnavailableError(
                "redis Python client is not installed; add 'redis' "
                "to requirements.txt and install it before setting "
                f"{env_var} to a redis:// URL"
            ) from e
        try:
            client = _redis_module.Redis.from_url(
                url, decode_responses=True, socket_timeout=5.0
            )
            client.ping()
        except Exception as e:
            raise RateLimitCoordinatorUnavailableError(
                f"Redis connection or PING failed ({type(e).__name__}); "
                f"check {env_var} (URL deliberately not echoed)"
            ) from e
        return RedisCoordinator(client)
    raise ValueError(
        f"{env_var} has an unrecognized scheme; expected 'redis://', "
        "'rediss://', 'in_process:', or empty. The configured value is "
        "deliberately not echoed here to avoid printing credentials."
    )
