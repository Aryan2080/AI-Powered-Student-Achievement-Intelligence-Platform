# Chunk 7.27A — ArxivRateLimiter Coordinator Injection

**Report type:** narrowly scoped implementation + regression verification.
**Generated:** 2026-10-24 (session date).
**Final status:** `COMPLETED — K10 CLOSED. ArxivRateLimiter NOW ACCEPTS AN OPTIONAL coordinator= KWARG WITH PROTOCOL-BASED VALIDATION. 18 NEW TESTS, 592 PRIOR TESTS, ALL PASS. SOURCE REMAINS "unreviewed". NO ARCHITECTURE INTRODUCED.`

> Chunk 7.27A closes the Chunk 7.26A K10 limitation ("`ArxivRateLimiter` facade doesn't yet expose a `coordinator=` kwarg") by adding one keyword argument + explicit Protocol-based validation to the existing facade. No new class, no new file, no `FacadeCoordinator`, no `caller_context` / `audit_tag`, no production collector, no Redis provisioning. Entirely backward-compatible for existing callers (there are none in `src/` outside the module's own tests).

---

## 1. Objective

Add an optional `coordinator: RateLimitCoordinator | None = None` keyword argument to `ArxivRateLimiter.__init__`, matching the public `RateLimitCoordinator` Protocol defined in the same module. When supplied, the facade delegates to the injected coordinator. Fail-closed on invalid input — never silently fall back to the default coordinator.

---

## 2. Initial Git status

| Field | Value |
|---|---|
| Branch | `feature/nlp-semantic` |
| HEAD before + after | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` (unchanged — no commit) |
| Working tree before | `M hybrid_dataset/metadata/sources.yaml` + `M pyproject.toml` + `M requirements.txt`; 7 untracked policy / test / doc / report files; `PROJECT_HANDOFF.md` untracked |
| Working tree after | identical shape — Chunk 7.27A modified `src/nlp_semantic/ingestion/rate_limit.py` + `tests/ingestion/test_rate_limit.py` (both were already untracked from prior chunks) and added one new report file |
| Protected hash `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` — verified start + end |
| Protected hash `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — verified start + end |

Teammate directories (`src/ml`, `src/recommender`, `src/backend`) do not exist; not touched.

---

## 3. Architecture inspected (actual, not fabricated)

Pre-change, `src/nlp_semantic/ingestion/rate_limit.py` exposed:

| Symbol | Kind | Role |
|---|---|---|
| `MIN_REQUEST_SPACING_SECONDS` (= 3.0) | module constant | Minimum arXiv ToU request spacing. |
| `RateLimitCoordinator` | `typing.Protocol`, `@runtime_checkable` | The three-attribute interface: `min_spacing_seconds`, `last_acquire_time`, `acquire()`. |
| `_ArxivCoordinator` | `@dataclass` (private) | Default in-process coordinator; thread-safe. |
| `_DEFAULT_COORDINATOR` | module singleton of `_ArxivCoordinator` | Shared across every default-constructed `ArxivRateLimiter` in the process. |
| `_reset_default_coordinator_for_testing()` | test-only helper | Resets the shared singleton between tests. |
| `ArxivRateLimiter` | public facade | Pre-Chunk-7.27A signature: `__init__(min_spacing_seconds=None, *, clock=None, sleeper=None)`. |
| `RedisCoordinator` | public class | Cross-machine coordinator from Chunk 7.22. |
| `COORDINATOR_URL_ENV_VAR`, `make_coordinator_from_env()` | public config surface | Env-driven coordinator selection. |
| `RateLimitCoordinatorUnavailableError`, `RateLimitAcquireTimeoutError` | public exceptions | Fail-closed error types. |

Verified: there is NO `src/coordinator/`, NO `FacadeCoordinator`, NO `caller_context`, NO `audit_tag` anywhere. `grep -rln "FacadeCoordinator|caller_context|audit_tag" src/` → no matches. The Chunk 7.27 prompt that mentioned those was mis-routed; this chunk (7.27A) addresses the real K10.

**Zero callers in `src/` outside the module itself** — the facade is a policy surface awaiting a future collector chunk (Chunk 7.22 §10 L8; Chunk 7.25 §4 K4). Backward compatibility is therefore automatic.

---

## 4. Existing coordinator interface used by the injection path

Verbatim from the module (unchanged by Chunk 7.27A):

```python
@runtime_checkable
class RateLimitCoordinator(Protocol):
    """Any object that gates arXiv requests must satisfy this shape…"""
    min_spacing_seconds: float
    @property
    def last_acquire_time(self) -> float | None: ...
    def acquire(self) -> AbstractContextManager[None]: ...
```

Chunk 7.27A injection validates against this Protocol via `isinstance(coordinator, RateLimitCoordinator)` (safe because the Protocol is `@runtime_checkable`), plus one additional constraint: `coordinator.min_spacing_seconds >= MIN_REQUEST_SPACING_SECONDS (3.0)`. The 3-second floor matches the arXiv ToU and the existing `_ArxivCoordinator.__init__` / `RedisCoordinator.__init__` lower-bound checks.

---

## 5. Files changed

| Path | Action | Lines affected | Purpose |
|---|---|---|---|
| [`src/nlp_semantic/ingestion/rate_limit.py`](../src/nlp_semantic/ingestion/rate_limit.py) | **MODIFIED** | Class docstring extended (~15 new lines of documentation); `__init__` signature extended with `coordinator=` kwarg; +22 lines of validation + binding (new injection branch at the top of `__init__`). | K10 fix. |
| [`tests/ingestion/test_rate_limit.py`](../tests/ingestion/test_rate_limit.py) | **MODIFIED** | +1 helper class (`_FakeCoordinator`, 20 lines); +1 helper class (`_NotACoordinator`, 10 lines); +1 new test class (`TestCoordinatorInjection`, 18 tests, ~160 lines). | Regression coverage for K10 fix. |
| [`reports/chunk_7_27A_arxiv_coordinator_injection.md`](chunk_7_27A_arxiv_coordinator_injection.md) | **CREATED** (this file) | Required deliverable. |

**Explicitly NOT changed:**
- No new source file created. No `src/coordinator/`. No `FacadeCoordinator`. No new helper module.
- `src/nlp_semantic/ingestion/arxiv_governance.py` — unchanged.
- Other test modules (`test_arxiv_governance.py`, `test_redis_rate_limit.py`, `test_registry.py`, `test_manifest.py`, etc.) — unchanged.
- `hybrid_dataset/metadata/sources.yaml` — Chunk 7.20 wording preserved byte-identical. No `review_status` change.
- `hybrid_dataset/metadata/arxiv_governance_decisions.md` — unchanged.
- `pyproject.toml`, `requirements.txt` — unchanged in Chunk 7.27A (prior-chunk state preserved).
- SIH source entry — byte-identical.
- `src/ml`, `src/recommender`, `src/backend` — do not exist; not created.
- No test weakened or removed.

---

## 6. API change (verbatim)

### 6.1 Pre-Chunk-7.27A signature

```python
class ArxivRateLimiter:
    def __init__(
        self,
        min_spacing_seconds: float | None = None,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None: ...
```

### 6.2 Post-Chunk-7.27A signature

```python
class ArxivRateLimiter:
    def __init__(
        self,
        min_spacing_seconds: float | None = None,
        *,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
        coordinator: RateLimitCoordinator | None = None,
    ) -> None: ...
```

### 6.3 Injection semantics

When `coordinator` is `None` (the default, i.e. the kwarg omitted): behavior is identical to pre-Chunk-7.27A. If none of `min_spacing_seconds`/`clock`/`sleeper` are set either, the facade uses `_DEFAULT_COORDINATOR` and reports `is_shared_default = True`. If any of those are set, the facade constructs a fresh `_ArxivCoordinator` (test-isolation path), unchanged from Chunks 7.20 and 7.22.

When `coordinator` is supplied, the validation path runs in this order:

1. **Combination check.** If any of `min_spacing_seconds`, `clock`, or `sleeper` is also set, raise `ValueError("coordinator= cannot be combined with min_spacing_seconds=, clock=, or sleeper=; build the coordinator with those settings yourself and pass it in as the single `coordinator=` argument.")`. Rationale: avoid two sources of truth. A caller wanting a custom clock can build their own `_ArxivCoordinator(clock=..., sleeper=...)` and inject it.
2. **Protocol conformance check.** If `not isinstance(coordinator, RateLimitCoordinator)`, raise `TypeError("coordinator must satisfy the RateLimitCoordinator Protocol (min_spacing_seconds, last_acquire_time, acquire()); got <type>")`. Protocol is `@runtime_checkable` — isinstance returns `True` iff the object has all three attributes.
3. **Minimum-spacing floor check.** If `coordinator.min_spacing_seconds < MIN_REQUEST_SPACING_SECONDS` (3.0), raise `ValueError("coordinator.min_spacing_seconds must be >= the arXiv ToU minimum of 3.0 seconds; got <value>")`. The 3-second floor must not be weakened by injection; this closes the obvious footgun of "sneak a 0.5-second coordinator past the facade."
4. **Bind.** `self._coordinator = coordinator`; `self._is_default = (coordinator is _DEFAULT_COORDINATOR)`. The `is_shared_default` property transparently reports the latter — e.g. a caller who deliberately injects `_DEFAULT_COORDINATOR` back gets `is_shared_default = True`, which is honest.
5. **Fail-closed.** On any validation failure, construction raises; no `ArxivRateLimiter` object is returned; **no fall-back to `_DEFAULT_COORDINATOR`** anywhere in the error path. The caller never gets a usable facade from a failed injection.

### 6.4 How a future caller would use it

Illustrative only; **no caller is added in Chunk 7.27A**:

```python
# Production path (future collector)
from nlp_semantic.ingestion.rate_limit import (
    ArxivRateLimiter, make_coordinator_from_env,
)
limiter = ArxivRateLimiter(coordinator=make_coordinator_from_env())
with limiter.acquire():
    # single API request to arXiv
    ...
```

Default construction (`ArxivRateLimiter()`) continues to work and silently selects the process-local shared default. Explicit injection makes it visible to code review that the caller consciously picked a backend.

---

## 7. Backward-compatibility analysis

### 7.1 Call-site survey

Pre-change in-tree callers of `ArxivRateLimiter(...)`:
- `tests/ingestion/test_rate_limit.py` — multiple calls (Chunks 7.18 + 7.20).
- `tests/ingestion/test_redis_rate_limit.py` — `TestInProcessCompatibility::test_process_local_limiter_still_works` + `test_injectable_clock_and_sleeper_still_work`.
- `src/*` — **zero** (no collector exists).

### 7.2 Compatibility verification

- All existing call sites use either the no-arg form or the `clock=`/`sleeper=`/`min_spacing_seconds=` kwargs. None of them pass `coordinator=`. The `coordinator: RateLimitCoordinator | None = None` kwarg default preserves prior behavior for every one of these calls.
- The combination check (new) does NOT trigger when `coordinator=None`; existing isolated-test calls (`ArxivRateLimiter(clock=fake, sleeper=fake)`) continue to work.
- `is_shared_default` property semantics unchanged for the two prior paths (default → `True`; test-isolation → `False`).
- No public symbol renamed or removed.
- No existing test modified.
- No existing exception type changed; the two new raise-sites use existing `TypeError` and `ValueError` built-ins consistent with the Chunk 7.18/7.22 convention.

### 7.3 Verified via regression tests

Full ingestion suite baseline: 206 passed, 5 skipped (post-Chunk-7.22). Post-Chunk-7.27A: 224 passed, 5 skipped. Delta: **+18**, exactly the new tests. **Zero regression** on the 206 pre-existing tests. See §9.

---

## 8. Regression tests added

New test class `TestCoordinatorInjection` in `tests/ingestion/test_rate_limit.py`. Also two new helper classes (`_FakeCoordinator`, `_NotACoordinator`).

Grouped by purpose:

### 8.1 Default behavior preserved (2 tests)

- `test_default_construction_still_shared_default` — `ArxivRateLimiter()` with no `coordinator=` → `_coordinator is _DEFAULT_COORDINATOR`, `is_shared_default is True`.
- `test_isolated_test_path_still_works_without_coordinator` — `ArxivRateLimiter(clock=..., sleeper=...)` without `coordinator=` → fresh per-instance coordinator, `is_shared_default is False`.

### 8.2 Injection succeeds (6 tests)

- `test_injected_coordinator_is_retained` — `lim._coordinator is fake`, `is_shared_default is False`.
- `test_injected_coordinator_acquire_is_invoked` — `with lim.acquire():` increments `fake.acquire_count`; `lim.last_acquire_time` reflects the fake's state.
- `test_default_coordinator_is_not_touched_when_injected` — `_DEFAULT_COORDINATOR.last_acquire_time` unchanged before and after an injected acquire.
- `test_injecting_default_coordinator_is_recognized_as_shared` — the edge case where the caller explicitly injects `_DEFAULT_COORDINATOR` back; `is_shared_default is True`.
- `test_min_spacing_reflects_injected_coordinator` — a coordinator with `min_spacing_seconds=5.0` is honestly reported by `lim.min_spacing_seconds`.
- `test_injected_arxiv_coordinator_works` — injecting a fresh `_ArxivCoordinator` (with fake clock/sleeper) works end-to-end.

### 8.3 Validation (5 tests)

- `test_object_without_acquire_rejected` — `_NotACoordinator` (missing `acquire()`) → `TypeError` with `"RateLimitCoordinator"` in message.
- `test_plain_object_rejected` — `object()` → `TypeError`.
- `test_rejection_does_not_fall_back_to_default` — explicit assertion that `TypeError` propagates and NO `ArxivRateLimiter` is returned (fail-closed).
- `test_zero_min_spacing_rejected` — `_FakeCoordinator(min_spacing_seconds=0.5)` → `ValueError`.
- `test_below_minimum_spacing_rejected` — `_FakeCoordinator(min_spacing_seconds=2.9)` → `ValueError`.

### 8.4 Combination with isolated-path kwargs rejected (3 tests)

- `test_coordinator_with_clock_rejected` → `ValueError` with `"cannot be combined"`.
- `test_coordinator_with_sleeper_rejected` → same.
- `test_coordinator_with_min_spacing_rejected` → same.

### 8.5 Error handling (2 tests)

- `test_injected_coordinator_exceptions_propagate` — `_ExplodingCoordinator` whose `acquire()` raises `RuntimeError` propagates verbatim through the facade.
- `test_body_exception_propagates_through_facade` — exception raised INSIDE `with lim.acquire():` body propagates; the injected coordinator still records the acquisition (`acquire_count == 1`).

**No existing assertion weakened. No test removed. No swallow-error pattern used.**

---

## 9. Exact commands executed + actual test results

### 9.1 Narrow — rate-limit module only

```
python -m pytest tests/ingestion/test_rate_limit.py --tb=short -v
```

| Metric | Count |
|---|---|
| Collected | **42** |
| Passed | **42** |
| Failed | 0 |
| Skipped | 0 |
| Collection errors | 0 |
| Completed | **Yes** |

Breakdown: pre-existing 24 (TestRateLimiterConstruction × 5 + TestRateLimiterPacing × 5 + TestRateLimiterConcurrency × 2 + TestRateLimiterOperatorDisciplineDocumented × 2 + TestSharedDefaultCoordinator × 4 + TestRateLimiterExceptionSafety × 5 + TestGlobalRequirementClassification × 1) + **18 new TestCoordinatorInjection**.

### 9.2 Broader — full ingestion

```
python -m pytest tests/ingestion/ --tb=short
```

| Metric | Count |
|---|---|
| Passed | **224** |
| Failed | 0 |
| Skipped | 5 (4 pre-existing inventory skips + 1 Redis integration skip) |
| Collection errors | 0 |

Baseline (post-Chunk-7.24): 206 passed, 5 skipped. Delta: **+18 passed**, zero skip delta.

### 9.3 Schema + ingestion + smoke

```
python -m pytest tests/schema/ tests/ingestion/ tests/test_smoke.py --tb=short
```

| Metric | Count |
|---|---|
| Passed | **458** |
| Failed | 0 |
| Skipped | 5 |
| Collection errors | 0 |

Baseline: 440 passed, 5 skipped. Delta: +18.

### 9.4 Full combined

```
python -m pytest --tb=short
```

| Metric | Count |
|---|---|
| Passed | **610** |
| Failed | 0 |
| Skipped | 5 |
| Collection errors | 0 |

Baseline (post-Chunk-7.24): 592 passed, 5 skipped. Delta: +18.

### 9.5 What tests did NOT execute

- `TestRedisIntegration::test_real_redis_coordinator` — correctly SKIPPED on missing `ARXIV_TEST_REDIS_URL`. Chunk 7.27A did NOT provide a Redis endpoint; the test is in the 5-skip count. No real Redis call made in this chunk.
- No arXiv API request made.
- No metadata downloaded.

The 592 → 610 delta is +18, exactly the number of new Chunk 7.27A tests. No pre-existing test's status changed.

---

## 10. Remaining limitations

Chunk 7.27A does NOT change the posture on any limitation other than K10. Specifically:

| From Chunk 7.26A | Still in effect? | Notes |
|---|---|---|
| K1 — real-Redis integration test NOT executed | **YES, STILL IN EFFECT** | `TestRedisIntegration` still skipped on missing `ARXIV_TEST_REDIS_URL`. |
| K2 — cross-machine operational verification NOT performed | **YES, STILL IN EFFECT** | Requires ≥ 2 machines + staged deployment. |
| K3 — no Redis infrastructure provisioned | **YES, STILL IN EFFECT** | `ARXIV_RATE_COORDINATOR_URL` unset. |
| K4 — no collector exists | **YES, STILL IN EFFECT** | The new `coordinator=` kwarg has no production caller today. |
| K5 — single-Redis-endpoint design, no Redlock | **YES, STILL IN EFFECT** | — |
| K6 — withdrawal regex heuristic | **YES, STILL IN EFFECT** | Not touched by this chunk. |
| K7 — email redaction regex doesn't match obfuscations | **YES, STILL IN EFFECT** | — |
| K8 — external verification pipelines upstream | **YES, STILL IN EFFECT** | — |
| K9 — orphan site-packages `tests` package | **YES, STILL IN EFFECT** (worked around; environment file not deleted) | Chunk 7.27A §5 scope restriction prohibits reopening K9. |
| **K10 — `ArxivRateLimiter` facade lacks `coordinator=` kwarg** | **CLOSED by Chunk 7.27A** | New kwarg + 18 regression tests. |
| K11 — dataset readiness blocked by independent gates | **YES, STILL IN EFFECT** | `lbl_research_pub` is `draft`; no collector; no records. |

### 10.1 New non-guarantees introduced by this chunk

- The injection path is unit-tested with `_FakeCoordinator` + `_ExplodingCoordinator` + `_NotACoordinator` + the real `_ArxivCoordinator`. It is NOT integration-tested against a real production coordinator (no collector exists to serve as the production caller).
- `isinstance(coordinator, RateLimitCoordinator)` is a *structural* Protocol check (the `@runtime_checkable` guarantee): it verifies the three attributes exist, but not that they have the right types. A pathological object providing an `acquire` attribute that is NOT a context manager would pass the Protocol check and fail at `with lim.acquire():` call time — which is honest Pythonic duck-typing behavior and matches how the pre-existing `make_coordinator_from_env()` factory treats the client.

---

## 11. Confirmation — no source promotion, no collection, no Redis provisioning, no training

- No API request initiated ✓
- No metadata collected ✓
- No download performed (no PDF, no TeX, no source archive, no full text) ✓
- No achievement record created ✓
- No annotation created ✓
- No dataset split generated ✓
- No taxonomy promoted ✓
- No source promoted; `src_08ee850ba4b54d1b81cdbd652809b613` remains `review_status: unreviewed` (verified by live `load_and_validate_sources` output and by `sources.yaml` being untouched in Chunk 7.27A — git diff shows SIH + arXiv entry hash identical to post-Chunk-7.20 state) ✓
- Ashok APPROVE / Mohan REVISE outcomes preserved verbatim ✓
- No reviewer identity invented or sign-off recorded ✓
- No stage, no commit, no push, no branch switch ✓
- No teammate directory touched (`src/ml`, `src/recommender`, `src/backend` do not exist) ✓
- No `src/coordinator/` directory created ✓
- No `FacadeCoordinator` class created ✓
- No `caller_context` / `audit_tag` concept introduced ✓
- No site-packages file modified or deleted ✓
- No `pyproject.toml` / `requirements.txt` modified in Chunk 7.27A ✓
- No Redis endpoint contacted (known or unknown) ✓
- No arXiv endpoint contacted ✓
- No infrastructure provisioned ✓
- No training/evaluation code touched ✓
- No K9/K7/K11/K6 remediation smuggled in ✓
- Protected hashes match: `PROJECT_HANDOFF.md` and `hybrid_dataset/raw/.gitkeep` ✓
- Chunk 7.4-D reviewer-independence stop preserved ✓
- Pre-existing `tests/dataset/` 152-pass count preserved (Chunk 7.24 fix untouched) ✓

---

## 12. Final status

**K10 CLOSED. ArxivRateLimiter.__init__ now accepts an optional `coordinator=` keyword argument. 18 new regression tests exercise injection semantics (default preserved, injection succeeds, validation fails explicitly, combination with isolated-path kwargs rejected, error propagation). Full suite 610 passed / 5 skipped / 0 failed / 0 collection errors (was 592/5/0/0; delta exactly +18). Source remains `unreviewed`. No new architecture introduced.**

### Recommended follow-ups (not performed in this chunk)

- A future collector chunk can now use `ArxivRateLimiter(coordinator=make_coordinator_from_env())` as a single-line integration point. Still requires: real Redis deployment (K3), integration test (K1), cross-machine operational verification (K2), and the Chunk 7.17 §5.8 two-reviewer source-promotion sign-off (D-J).
- K6, K7, K11 remain in their existing status.
- The orphan `tests` package in the user's site-packages (K9 environment-level cleanup) remains an optional environment hygiene step for Aryan; the repo is self-contained.
