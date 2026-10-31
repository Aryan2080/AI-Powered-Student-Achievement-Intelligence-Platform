"""Tests for the Chunk 7.18 arXiv rate limiter + Chunk 7.20 remediation.

Deterministic — uses injected clock and sleeper, never actually sleeps.

Chunk 7.20 remediation: the module-level default coordinator is shared
across all default-constructed `ArxivRateLimiter()` instances in the
process. The autouse fixture `_reset_default_coord` resets its state
between tests so each test starts from a clean baseline.
"""
from __future__ import annotations

import threading
import time
from typing import List

import pytest

from nlp_semantic.ingestion.rate_limit import (
    MIN_REQUEST_SPACING_SECONDS,
    ArxivRateLimiter,
    _ArxivCoordinator,
    _DEFAULT_COORDINATOR,
    _reset_default_coordinator_for_testing,
)


@pytest.fixture(autouse=True)
def _reset_default_coord():
    """Reset the module-level default coordinator before each test so
    tests that touch `ArxivRateLimiter()` (default construction) start
    from `last_acquire_time is None`."""
    _reset_default_coordinator_for_testing()
    yield
    _reset_default_coordinator_for_testing()


class FakeClock:
    """Deterministic monotonic clock for tests."""

    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, dt: float) -> None:
        self.now += dt


class FakeSleeper:
    """Captures sleep durations without actually sleeping."""

    def __init__(self, clock: FakeClock) -> None:
        self._clock = clock
        self.calls: List[float] = []

    def __call__(self, dt: float) -> None:
        self.calls.append(dt)
        self._clock.advance(dt)


class TestRateLimiterConstruction:
    def test_default_spacing(self):
        lim = ArxivRateLimiter()
        assert lim.min_spacing_seconds == MIN_REQUEST_SPACING_SECONDS
        assert lim.last_acquire_time is None

    def test_explicit_spacing_at_minimum_accepted(self):
        lim = ArxivRateLimiter(min_spacing_seconds=3.0)
        assert lim.min_spacing_seconds == 3.0

    def test_explicit_spacing_above_minimum_accepted(self):
        lim = ArxivRateLimiter(min_spacing_seconds=5.0)
        assert lim.min_spacing_seconds == 5.0

    def test_spacing_below_minimum_rejected(self):
        with pytest.raises(ValueError, match=r"must be >= .*3\.0"):
            ArxivRateLimiter(min_spacing_seconds=2.9)

    def test_min_request_spacing_is_three_seconds(self):
        """The ToU minimum must be exactly 3.0 s per the human review."""
        assert MIN_REQUEST_SPACING_SECONDS == 3.0


class TestRateLimiterPacing:
    def test_first_acquire_does_not_sleep(self):
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)
        with lim.acquire():
            pass
        assert sleeper.calls == []
        assert lim.last_acquire_time == 1000.0

    def test_second_acquire_within_gap_sleeps_remainder(self):
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)
        with lim.acquire():
            pass  # first at t=1000.0
        clock.advance(1.0)  # second attempt 1 s later
        with lim.acquire():
            pass
        # Must have slept for 3 - 1 = 2.0 s.
        assert sleeper.calls == [2.0]
        assert lim.last_acquire_time == 1003.0

    def test_second_acquire_after_gap_does_not_sleep(self):
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)
        with lim.acquire():
            pass  # first at t=1000.0
        clock.advance(10.0)  # second attempt 10 s later
        with lim.acquire():
            pass
        assert sleeper.calls == []
        assert lim.last_acquire_time == 1010.0

    def test_second_acquire_exactly_at_gap_does_not_sleep(self):
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)
        with lim.acquire():
            pass
        clock.advance(3.0)
        with lim.acquire():
            pass
        assert sleeper.calls == []

    def test_three_rapid_acquires_each_waits_three_seconds(self):
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)
        for _ in range(3):
            with lim.acquire():
                pass
        # First has nothing to wait for; second and third each wait 3.0.
        assert sleeper.calls == [3.0, 3.0]
        assert lim.last_acquire_time == 1006.0


class TestRateLimiterConcurrency:
    def test_single_connection_lock_serializes_threads(self):
        """Two threads cannot both be inside acquire() simultaneously.

        Uses a shared counter that must never exceed 1 while the
        acquire context is held.
        """
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(
            min_spacing_seconds=3.0,
            clock=clock,
            sleeper=sleeper,
        )
        active = 0
        max_active_seen = 0
        active_lock = threading.Lock()

        def worker():
            nonlocal active, max_active_seen
            with lim.acquire():
                with active_lock:
                    active += 1
                    max_active_seen = max(max_active_seen, active)
                # Simulate request body with a brief yield so the other
                # thread has a chance to try to enter.
                time.sleep(0.01)
                with active_lock:
                    active -= 1

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert max_active_seen == 1, (
            "ArxivRateLimiter.acquire must serialize threads; observed "
            f"up to {max_active_seen} concurrent holders"
        )

    def test_last_acquire_time_updated_under_thread_contention(self):
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)

        def worker():
            with lim.acquire():
                pass

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        # Four of five calls had to wait the 3 s gap.
        assert len(sleeper.calls) == 4
        assert all(c == 3.0 for c in sleeper.calls)
        assert lim.last_acquire_time == 1012.0


class TestRateLimiterOperatorDisciplineDocumented:
    def test_module_documents_process_local_limitation(self):
        """The module docstring must document that the limiter is
        process-local; cross-process coordination is operator
        discipline, not code enforcement."""
        import nlp_semantic.ingestion.rate_limit as mod
        doc = mod.__doc__ or ""
        assert "process-local" in doc.lower() or "process local" in doc.lower()
        assert "operator" in doc.lower()

    def test_module_documents_global_not_satisfied(self):
        """The module docstring must explicitly state that the Chunk
        7.19 audit classifies the global requirement as NOT SATISFIED
        by this module (per Chunk 7.20 remediation reporting)."""
        import nlp_semantic.ingestion.rate_limit as mod
        doc = (mod.__doc__ or "").lower()
        assert "not satisfied" in doc or "not satisfied by this" in doc


# ---- Chunk 7.20 — shared default coordinator -------------------------------


class TestSharedDefaultCoordinator:
    """Chunk 7.20 remediation: multiple default-constructed
    ArxivRateLimiter instances in one process share the same
    coordinator and cannot bypass the aggregate rate limit."""

    def test_default_construction_uses_shared_coordinator(self):
        a = ArxivRateLimiter()
        b = ArxivRateLimiter()
        assert a.is_shared_default is True
        assert b.is_shared_default is True
        assert a._coordinator is b._coordinator
        assert a._coordinator is _DEFAULT_COORDINATOR

    def test_explicit_args_bypass_default_coordinator(self):
        """Explicit clock/sleeper/min_spacing_seconds → per-instance
        coordinator (test-isolation path), not the module default."""
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)
        assert lim.is_shared_default is False
        assert lim._coordinator is not _DEFAULT_COORDINATOR

    def test_two_default_instances_share_last_acquire_time(self):
        """When a default instance acquires, the next default instance
        sees the updated `last_acquire_time`."""
        # Replace the default coordinator with a fake-clock one for
        # determinism, then restore. (This is only safe because the
        # autouse fixture resets the real one before/after.)
        import nlp_semantic.ingestion.rate_limit as mod
        original = mod._DEFAULT_COORDINATOR
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        fake_default = _ArxivCoordinator(
            min_spacing_seconds=3.0, clock=clock, sleeper=sleeper,
        )
        mod._DEFAULT_COORDINATOR = fake_default
        try:
            a = ArxivRateLimiter()
            b = ArxivRateLimiter()
            with a.acquire():
                pass
            t_after_a = a.last_acquire_time
            assert t_after_a == 1000.0
            # b sees the same last_acquire_time because it shares the
            # coordinator.
            assert b.last_acquire_time == t_after_a
            # b acquires 1 second later → must wait 2.0 s.
            clock.advance(1.0)
            with b.acquire():
                pass
            assert sleeper.calls == [2.0]
            assert a.last_acquire_time == 1003.0
            assert b.last_acquire_time == 1003.0
        finally:
            mod._DEFAULT_COORDINATOR = original

    def test_single_connection_lock_serializes_across_default_instances(self):
        """Different default-constructed limiter objects must still
        serialize concurrent requests via the one shared lock."""
        active = 0
        max_active_seen = 0
        active_lock = threading.Lock()

        # Use the real default coordinator (which uses real clock /
        # sleeper). To keep the test fast, use an isolated coordinator
        # swapped in — the serialization behavior is identical because
        # it comes from the lock, not the pacing.
        import nlp_semantic.ingestion.rate_limit as mod
        original = mod._DEFAULT_COORDINATOR
        instant_clock = FakeClock()
        # Sleeper that advances the fake clock enough so no gap wait
        # dominates the timing of the test:
        sleeper = FakeSleeper(instant_clock)
        mod._DEFAULT_COORDINATOR = _ArxivCoordinator(
            min_spacing_seconds=3.0,
            clock=instant_clock,
            sleeper=sleeper,
        )
        try:
            def worker():
                nonlocal active, max_active_seen
                lim = ArxivRateLimiter()  # default — shared
                with lim.acquire():
                    with active_lock:
                        active += 1
                        max_active_seen = max(max_active_seen, active)
                    time.sleep(0.005)
                    with active_lock:
                        active -= 1

            threads = [threading.Thread(target=worker) for _ in range(5)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            assert max_active_seen == 1, (
                "Different default-constructed ArxivRateLimiter objects "
                "must serialize via the shared coordinator lock; observed "
                f"{max_active_seen} concurrent holders"
            )
        finally:
            mod._DEFAULT_COORDINATOR = original


# ---- Chunk 7.20 — exception safety -----------------------------------------


class TestRateLimiterExceptionSafety:
    """The limiter must release the lock on exception, keep
    `last_acquire_time` updated, and remain usable for subsequent
    acquisitions."""

    def test_exception_in_body_releases_lock(self):
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom):
            with lim.acquire():
                raise _Boom()

        # Lock must be released: a subsequent acquire does not deadlock.
        # Advance past the 3 s gap so no sleep is required either.
        clock.advance(10.0)
        with lim.acquire():
            pass  # must complete without hanging

    def test_last_acquire_time_updated_on_exception(self):
        """Even if the request body raises, the acquisition already
        happened (one request was made under the lock). The gap must
        apply to the NEXT acquisition."""
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom):
            with lim.acquire():
                raise _Boom()

        # The acquire that raised still counted. Subsequent acquire
        # 1 s later must wait 2 s to satisfy the gap.
        clock.advance(1.0)
        with lim.acquire():
            pass
        assert sleeper.calls == [2.0]

    def test_lock_free_after_concurrent_exception(self):
        """A thread that raises inside acquire() does not deadlock
        other threads waiting to acquire."""
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)

        completed = []

        class _Boom(Exception):
            pass

        def failing_worker():
            try:
                with lim.acquire():
                    raise _Boom()
            except _Boom:
                completed.append("failed")

        def normal_worker():
            with lim.acquire():
                completed.append("ok")

        t_fail = threading.Thread(target=failing_worker)
        t_fail.start()
        t_fail.join(timeout=2.0)
        assert not t_fail.is_alive()

        t_ok = threading.Thread(target=normal_worker)
        t_ok.start()
        t_ok.join(timeout=2.0)
        assert not t_ok.is_alive()

        assert "failed" in completed
        assert "ok" in completed

    def test_many_acquisitions_state_consistency(self):
        """After many acquire/release cycles (including some that raise),
        the limiter's internal state remains consistent."""
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)

        class _Boom(Exception):
            pass

        for i in range(20):
            try:
                with lim.acquire():
                    if i % 3 == 0:
                        raise _Boom()
            except _Boom:
                pass
            # Advance well past the gap for the next iteration.
            clock.advance(10.0)

        # 20 acquisitions, each spaced > 3 s apart → no sleeps required.
        assert sleeper.calls == []
        # `last_acquire_time` reflects the final acquisition.
        assert lim.last_acquire_time is not None
        assert lim.last_acquire_time == 1000.0 + 19 * 10.0

    def test_min_spacing_seconds_below_minimum_rejected_on_explicit_construction(self):
        """Chunk 7.20 preserves the Chunk 7.18 lower-bound check."""
        with pytest.raises(ValueError, match=r"must be >= .*3\.0"):
            ArxivRateLimiter(min_spacing_seconds=2.9)


# ---- Chunk 7.20 — global requirement classification -----------------------


class TestGlobalRequirementClassification:
    """Chunk 7.20 must not claim the global cross-machine requirement
    is satisfied. The module docstring explicitly says it is not; the
    governance decisions document likewise."""

    def test_governance_doc_states_global_blocked(self):
        """`arxiv_governance_decisions.md` must document that global
        rate-limit coordination remains blocked / unresolved."""
        from pathlib import Path
        repo_root = Path(__file__).resolve().parents[2]
        doc = (repo_root / "hybrid_dataset" / "metadata"
               / "arxiv_governance_decisions.md").read_text(encoding="utf-8")
        lower = doc.lower()
        # Either phrasing acceptable.
        assert (
            "global enforcement" in lower
            or "process-local" in lower
            or "cross-process" in lower
            or "cross-machine" in lower
        )
        assert "operator discipline" in lower


# ---- Chunk 7.27A — coordinator-injection path -----------------------------


class _FakeCoordinator:
    """Minimal RateLimitCoordinator-conforming test double.

    Satisfies the Protocol structurally: has ``min_spacing_seconds``,
    ``last_acquire_time``, and ``acquire()`` (context manager).
    Records acquisition count for assertions.
    """

    def __init__(self, min_spacing_seconds: float = 3.0) -> None:
        self.min_spacing_seconds = float(min_spacing_seconds)
        self._last_acquire_time: float | None = None
        self.acquire_count = 0

    @property
    def last_acquire_time(self) -> float | None:
        return self._last_acquire_time

    def acquire(self):
        import contextlib

        @contextlib.contextmanager
        def _gen():
            self.acquire_count += 1
            self._last_acquire_time = 1234.5
            yield
        return _gen()


class _NotACoordinator:
    """Object with the WRONG shape — missing acquire(). Must be rejected."""

    min_spacing_seconds: float = 3.0

    @property
    def last_acquire_time(self):
        return None
    # no acquire() method


class TestCoordinatorInjection:
    """Chunk 7.27A — the coordinator-injection path on
    ArxivRateLimiter closes Chunk 7.26A K10."""

    # --- default behavior preserved -----------------------------------

    def test_default_construction_still_shared_default(self):
        """No `coordinator=` → facade still wraps _DEFAULT_COORDINATOR."""
        lim = ArxivRateLimiter()
        assert lim.is_shared_default is True
        assert lim._coordinator is _DEFAULT_COORDINATOR

    def test_isolated_test_path_still_works_without_coordinator(self):
        """Existing `clock=`/`sleeper=` test-isolation path untouched."""
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        lim = ArxivRateLimiter(clock=clock, sleeper=sleeper)
        assert lim.is_shared_default is False
        assert lim._coordinator is not _DEFAULT_COORDINATOR

    # --- injection succeeds -------------------------------------------

    def test_injected_coordinator_is_retained(self):
        fake = _FakeCoordinator()
        lim = ArxivRateLimiter(coordinator=fake)
        assert lim._coordinator is fake
        assert lim.is_shared_default is False

    def test_injected_coordinator_acquire_is_invoked(self):
        fake = _FakeCoordinator()
        lim = ArxivRateLimiter(coordinator=fake)
        assert fake.acquire_count == 0
        with lim.acquire():
            pass
        assert fake.acquire_count == 1
        # And the facade's last_acquire_time reflects the fake's state.
        assert lim.last_acquire_time == 1234.5

    def test_default_coordinator_is_not_touched_when_injected(self):
        """Injecting MUST NOT accidentally mutate _DEFAULT_COORDINATOR."""
        default_last_before = _DEFAULT_COORDINATOR.last_acquire_time
        fake = _FakeCoordinator()
        lim = ArxivRateLimiter(coordinator=fake)
        with lim.acquire():
            pass
        assert _DEFAULT_COORDINATOR.last_acquire_time == default_last_before

    def test_injecting_default_coordinator_is_recognized_as_shared(self):
        """Explicitly injecting _DEFAULT_COORDINATOR → is_shared_default True.
        Edge case; it's valid and `is_shared_default` reflects reality."""
        lim = ArxivRateLimiter(coordinator=_DEFAULT_COORDINATOR)
        assert lim._coordinator is _DEFAULT_COORDINATOR
        assert lim.is_shared_default is True

    def test_min_spacing_reflects_injected_coordinator(self):
        fake = _FakeCoordinator(min_spacing_seconds=5.0)
        lim = ArxivRateLimiter(coordinator=fake)
        assert lim.min_spacing_seconds == 5.0

    def test_injected_arxiv_coordinator_works(self):
        """Injecting a fresh _ArxivCoordinator (not the default) works
        the same as if constructed via the test-isolation path."""
        clock = FakeClock()
        sleeper = FakeSleeper(clock)
        coord = _ArxivCoordinator(
            min_spacing_seconds=3.0, clock=clock, sleeper=sleeper,
        )
        lim = ArxivRateLimiter(coordinator=coord)
        with lim.acquire():
            pass
        assert coord.last_acquire_time == 1000.0

    # --- validation: wrong shape --------------------------------------

    def test_object_without_acquire_rejected(self):
        with pytest.raises(TypeError, match="RateLimitCoordinator"):
            ArxivRateLimiter(coordinator=_NotACoordinator())

    def test_plain_object_rejected(self):
        with pytest.raises(TypeError, match="RateLimitCoordinator"):
            ArxivRateLimiter(coordinator=object())

    def test_rejection_does_not_fall_back_to_default(self):
        """A rejected coordinator MUST NOT silently become the default.
        The construction must raise and no limiter object is returned."""
        with pytest.raises(TypeError):
            lim = ArxivRateLimiter(coordinator=object())
            # Should never reach here; but if it did, assert it's NOT a
            # usable default-backed facade:
            assert lim is None  # pragma: no cover

    def test_zero_min_spacing_rejected(self):
        fake = _FakeCoordinator(min_spacing_seconds=0.5)
        with pytest.raises(ValueError, match=r"must be >= .*3\.0"):
            ArxivRateLimiter(coordinator=fake)

    def test_below_minimum_spacing_rejected(self):
        fake = _FakeCoordinator(min_spacing_seconds=2.9)
        with pytest.raises(ValueError, match=r"must be >= .*3\.0"):
            ArxivRateLimiter(coordinator=fake)

    # --- validation: combining with isolated-path kwargs is rejected --

    def test_coordinator_with_clock_rejected(self):
        fake = _FakeCoordinator()
        with pytest.raises(ValueError, match="cannot be combined"):
            ArxivRateLimiter(coordinator=fake, clock=lambda: 0.0)

    def test_coordinator_with_sleeper_rejected(self):
        fake = _FakeCoordinator()
        with pytest.raises(ValueError, match="cannot be combined"):
            ArxivRateLimiter(coordinator=fake, sleeper=lambda d: None)

    def test_coordinator_with_min_spacing_rejected(self):
        fake = _FakeCoordinator()
        with pytest.raises(ValueError, match="cannot be combined"):
            ArxivRateLimiter(5.0, coordinator=fake)

    # --- error propagation -------------------------------------------

    def test_injected_coordinator_exceptions_propagate(self):
        """If the injected coordinator's acquire() raises, the facade
        does not swallow it."""
        import contextlib

        class _ExplodingCoordinator:
            min_spacing_seconds: float = 3.0
            last_acquire_time: float | None = None
            def acquire(self):
                @contextlib.contextmanager
                def gen():
                    raise RuntimeError("backend down")
                    yield  # pragma: no cover
                return gen()

        lim = ArxivRateLimiter(coordinator=_ExplodingCoordinator())
        with pytest.raises(RuntimeError, match="backend down"):
            with lim.acquire():
                pass

    def test_body_exception_propagates_through_facade(self):
        fake = _FakeCoordinator()
        lim = ArxivRateLimiter(coordinator=fake)

        class _Boom(Exception):
            pass

        with pytest.raises(_Boom):
            with lim.acquire():
                raise _Boom()
        # The injected coordinator still saw the acquisition.
        assert fake.acquire_count == 1
