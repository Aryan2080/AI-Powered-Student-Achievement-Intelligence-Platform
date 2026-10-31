# Chunk 7.21 — Shared Rate-Limit Coordination Architecture (Design, Read-Only)

**Report type:** read-only architecture design for a future authorized coordination mechanism.
**Generated:** 2026-10-24 (session date).
**Final status:** `DESIGN ONLY. NO IMPLEMENTATION. NO COLLECTION. SOURCE REMAINS UNREVIEWED. GLOBAL RATE-LIMIT BLOCKER NOT RESOLVED BY THIS CHUNK.`

> This chunk does NOT fix the global rate-limit blocker (Chunk 7.19 B1 / Chunk 7.20 B1). It proposes a pluggable coordinator interface, evaluates four backends, and recommends which backend would best satisfy Mohan's cross-machine requirement — but the implementation and the infrastructure decision are explicit **Aryan-authorization gates** and are OUT OF SCOPE for Chunk 7.21.

---

## 1. Starting repository state

| Field | Value |
|---|---|
| Repository | `AI-Powered-Student-Achievement-Intelligence-Platform` |
| Branch | `feature/nlp-semantic` |
| HEAD | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` (unchanged — no commit in this chunk) |
| Remote sync | in sync (not pushed) |
| Working tree before + after | ` M hybrid_dataset/metadata/sources.yaml`; `?? PROJECT_HANDOFF.md`; `?? reports/`; `?? hybrid_dataset/metadata/arxiv_governance_decisions.md`; `?? src/nlp_semantic/ingestion/arxiv_governance.py`; `?? src/nlp_semantic/ingestion/rate_limit.py`; `?? tests/ingestion/test_arxiv_governance.py`; `?? tests/ingestion/test_rate_limit.py` (Chunk 7.21 adds only this report file) |

### 1.1 Protected hashes

| File | Expected | Observed | Match |
|---|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

### 1.2 Current dependency surface (verified by reading `requirements.txt`)

```
pandas
pydantic>=2,<3
pytest
pyyaml
```

No `redis`, `filelock`, `portalocker`, `psycopg`, `sqlalchemy`, `pymongo`, or any other coordination-capable dependency is present. **No shared-coordination infrastructure exists in the repo today.** Any backend adopted by a future chunk requires a dependency-and-infrastructure decision authored by the project owner.

### 1.3 Files inspected (read-only)

- `src/nlp_semantic/ingestion/rate_limit.py` (Chunk 7.20 version with shared default coordinator).
- `src/nlp_semantic/ingestion/arxiv_governance.py` (Chunk 7.18 policy module — pure policy, no network).
- `tests/ingestion/test_rate_limit.py` (24 tests after Chunk 7.20).
- `hybrid_dataset/metadata/sources.yaml` (arXiv entry's post-Chunk-7.20 wording).
- `hybrid_dataset/metadata/arxiv_governance_decisions.md`.
- `reports/chunk_7_19_arxiv_governance_implementation_audit.md`.
- `reports/chunk_7_20_arxiv_rate_limit_remediation.md`.
- `requirements.txt`.
- `src/nlp_semantic/ingestion/__init__.py` (lazy `__getattr__` surface; does NOT re-export the rate limiter — intentional).

No file was modified by Chunk 7.21.

---

## 2. Existing limiter architecture (verified from on-disk code)

### 2.1 Chunk 7.20 shape

```
src/nlp_semantic/ingestion/rate_limit.py

MIN_REQUEST_SPACING_SECONDS = 3.0

@dataclass
class _ArxivCoordinator:                                 # internal
    min_spacing_seconds: float
    clock:   Callable[[], float]
    sleeper: Callable[[float], None]
    _lock:   threading.Lock
    _last_acquire_time: float | None
    def acquire() -> contextmanager                      # the gate

_DEFAULT_COORDINATOR: _ArxivCoordinator = _ArxivCoordinator(
    min_spacing_seconds = 3.0,
    clock               = time.monotonic,
    sleeper             = time.sleep,
)

_reset_default_coordinator_for_testing() -> None          # test-only

class ArxivRateLimiter:                                   # public facade
    def __init__(
        self,
        min_spacing_seconds: float | None = None,
        *, clock: ..., sleeper: ...,
    ):
        # Any explicit arg → fresh _ArxivCoordinator (TEST isolation)
        # Otherwise          → self._coordinator = _DEFAULT_COORDINATOR
        ...

    @contextmanager
    def acquire():
        with self._coordinator.acquire():
            yield
```

### 2.2 Current guarantees — within one Python process

- **Single-connection semantics.** `threading.Lock` serializes acquisitions on the shared `_DEFAULT_COORDINATOR`.
- **3-second gap.** Each acquisition records `_last_acquire_time`; the next acquisition sleeps for the deficit.
- **Exception safety.** `try: … finally: self._lock.release()` + state updated before `yield`.
- **Multi-instance safety.** Every default-constructed `ArxivRateLimiter()` facade shares `_DEFAULT_COORDINATOR` (Chunk 7.20 B2/B3 close).

### 2.3 Current guarantees — across processes / machines

**None.** The lock is `threading.Lock` (in-process). `_last_acquire_time` is a Python attribute on a module-level dataclass instance (in-process memory). Two Python processes, or two machines, cannot see each other's state. This is the Chunk 7.19 B1 / Chunk 7.20 B1 blocker.

### 2.4 Existing injection point for a replacement coordinator

The current `_ArxivCoordinator` is a concrete dataclass. The facade `ArxivRateLimiter._coordinator` is referenced only via `self._coordinator.acquire()`. The minimal interface a replacement must satisfy is:

- `min_spacing_seconds: float` attribute (for introspection / tests).
- `last_acquire_time: float | None` property (for introspection; may legitimately return a stale value for a shared backend).
- An `acquire()` method that returns a context manager serializing the request body and ensuring the inter-request gap.

Any backend that satisfies this shape can be plugged in without touching `ArxivRateLimiter`.

---

## 3. Options comparison

Columns: **CP** = cross-process (same machine); **CM** = cross-machine; **Atomicity** = whether the shared "take lock + check gap + update timestamp" is atomic; **Fail-mode** = what happens when the backing infra is unavailable; **Infra** = what has to exist; **Testing** = how a test suite can exercise the backend; **Ops** = operational complexity.

| # | Option | CP | CM | Atomicity | Fail-mode (if infra absent / crashed) | Infra required | Testing feasibility | Ops |
|---|---|---|---|---|---|---|---|---|
| **A** | **Process-local (current, Chunk 7.20)** | ✗ | ✗ | ✓ (threading.Lock) | n/a — no shared state | None | ✓ fake clock/sleeper → fully deterministic | None |
| **B** | **Shared-filesystem (file lock + timestamp file)** | ✓ (on local FS) | **conditional** (reliable only on a correctly configured network FS with POSIX advisory-lock semantics; NOT reliable on OneDrive sync, Dropbox, SMB client, or NFSv3 without `nolock`) | ✓ with `fcntl.flock` on Linux local FS; **UNRELIABLE** on networked FS; `portalocker` or `filelock` library smooths cross-platform but not cross-NFS | Lock *may* release on process crash (OS-dependent); timestamp file may be stale — gap-logic naturally delays the next request | A shared filesystem path reachable by all collector hosts; a cross-platform locking library (`filelock` or `portalocker`) added to `requirements.txt` | Multi-process on one Linux CI machine is testable with `pytest-xprocess` or subprocess fixtures; cross-machine is not CI-testable | Low on same machine; HIGH if cross-machine (depends on NFS semantics) |
| **C** | **Redis (SETNX + TTL + timestamp key)** | ✓ | ✓ | ✓ with Lua script or `MULTI/EXEC`; Redlock algorithm for fault-tolerant multi-master | FAIL-CLOSED: acquire() must raise/block; MUST NOT fall back to "no limit" | Redis server (self-hosted or managed), `redis` Python client added to `requirements.txt` | `fakeredis` library for unit tests; integration tests require a running Redis (test container or shared dev instance) | Moderate; Redis availability must be monitored | 
| **D** | **Database-backed (SQLite WAL / Postgres advisory lock)** | SQLite: ✓ same-machine, **not** cross-machine. Postgres: ✓ cross-machine via `pg_advisory_xact_lock`. | SQLite: ✗. Postgres: ✓. | SQLite: WAL + exclusive transaction OK; Postgres: advisory locks are atomic by design. | FAIL-CLOSED on DB unavailable. SQLite: database locked / timeout. Postgres: connection error. | SQLite: a shared DB file (same-machine only). Postgres: a Postgres server + `psycopg` client. | SQLite: trivial (in-memory DB for tests). Postgres: integration via test container. | SQLite: minimal. Postgres: similar to Redis. |

### 3.1 Deployability check for this project

- **Operating environment observed:** Windows 11 + OneDrive-synced project folder.
- **OneDrive and file locks:** OneDrive sync is NOT a reliable lock substrate. File-lock semantics on a OneDrive-synced path have no documented guarantee and have known conflict-resolution behaviors that can double-process a lock. **Option B cannot be deployed on OneDrive-synced paths without an explicit "move lock file off OneDrive" rule.**
- **No pre-existing Redis / Postgres / SQLite coordination:** confirmed by `requirements.txt` and by prior-chunk greps. Any backend requires owner authorization to introduce a dependency.
- **CI runner identity unknown:** the project has no CI config visible in the inspected files. Cross-machine semantics cannot be tested without a known CI topology.

### 3.2 Can any option guarantee a shared ≥ 3-second interval across all participating machines?

| Option | Guarantees a shared ≥ 3-second interval across all participating machines? |
|---|---|
| A — process-local | **No.** By design. |
| B — shared filesystem | **Only if** all participants mount the SAME filesystem with POSIX advisory-lock semantics. OneDrive-synced paths DO NOT qualify. A local NFS or SMB share can qualify but adds ops complexity and is not currently present. |
| C — Redis | **Yes**, with proper deployment (Redlock for multi-master; SETNX + TTL with Lua script for single-master). This is the standard shared rate-limit substrate. |
| D — Postgres | **Yes**, via `pg_advisory_lock` or `SELECT ... FOR UPDATE` on a dedicated row. |
| D — SQLite | **No** across machines. Cross-process on a single machine only. |

**Short answer: only options C and D-Postgres can satisfy the cross-machine requirement, and both require infrastructure that does not exist today.**

---

## 4. Recommended architecture

**This chunk recommends a two-layer design and leaves the backend choice as an Aryan-authorization decision.**

### 4.1 Layer 1 — Protocol (zero-dependency; could land in a future narrow implementation chunk)

Introduce a `RateLimitCoordinator` typing Protocol in `rate_limit.py`:

```python
from typing import Protocol, Iterator
from contextlib import AbstractContextManager

class RateLimitCoordinator(Protocol):
    """Any object that gates arXiv requests must satisfy this shape.

    Implementations may be process-local (current _ArxivCoordinator),
    shared-filesystem, Redis-backed, Postgres-backed, or others. The
    facade ArxivRateLimiter calls only .acquire() and reads
    .min_spacing_seconds / .last_acquire_time.
    """
    min_spacing_seconds: float

    @property
    def last_acquire_time(self) -> float | None: ...

    def acquire(self) -> AbstractContextManager[None]: ...
```

The existing `_ArxivCoordinator` already satisfies this shape structurally. **No code change is strictly required for Chunk 7.20 behavior to continue to work.**

### 4.2 Layer 2 — Backend (introduced only after Aryan's authorization)

Three backends sketched; each is a separate future chunk:

1. **`InProcessCoordinator`** — alias for the existing `_ArxivCoordinator`. This is the fallback; nothing changes if operator discipline is codified as the compensating control.
2. **`FileLockCoordinator`** — same-machine cross-process. Would use the `filelock` library on a locally-mounted path (NOT OneDrive). Owner must designate the lock path and confirm it is not OneDrive-synced.
3. **`RedisCoordinator`** — cross-machine. Would use the `redis` client, SETNX+TTL for the lock, and a timestamp key for the gap. Owner must designate the Redis endpoint and credentials.

The recommended **first authorized backend to add** is **`RedisCoordinator`**, because:

- It is the only option that satisfies the cross-machine requirement in Mohan's revision.
- It has a well-understood algorithm (Redlock) with a maintained Python client.
- It can be tested with `fakeredis` in unit tests.
- Alternative (D-Postgres) is comparable but adds a heavier dependency surface (an entire DB).
- Alternative (B — shared FS) is unreliable in the project's actual environment (Windows + OneDrive).

**Caveat:** adding Redis is an infrastructure decision Aryan must authorize. If Aryan prefers to keep the project zero-infrastructure, the recommendation falls back to **codifying operator discipline** as the compensating control:

- One collector process at a time.
- One operator machine at a time.
- A documented policy in `arxiv_governance_decisions.md` that any cross-machine coordination is manual and procedural.

This fallback is what the current Chunk 7.20 posture already assumes.

### 4.3 Rationale for the protocol + pluggable-backend split

- Zero-change code path for today's posture. If Aryan declines Redis, Chunk 7.21's recommendation leaves the repository UNCHANGED (Chunk 7.20 state).
- Clean extension point. A future authorized chunk can add exactly one backend without touching `ArxivRateLimiter` or any caller.
- Honest: the chunk does NOT claim global enforcement; it describes the smallest change that WOULD, once infrastructure is adopted.

---

## 5. Does the recommendation require infrastructure not currently present?

**Yes, for every cross-machine option (C or D-Postgres).** Specifically:

| Option | Missing today | What Aryan must provide |
|---|---|---|
| C — Redis | Redis server + `redis` client dependency | A Redis endpoint URL + credentials + whose server + budget for availability + CI test infrastructure (fakeredis for unit; test container for integration) |
| D — Postgres | Postgres server + `psycopg` dependency | A Postgres endpoint + credentials + whose server + schema migration policy + CI test infrastructure |
| B — local-FS same-machine | Nothing (Windows + the `filelock` library) | Confirmation that collector always runs from a non-OneDrive path, OR acceptance that only one process on one machine runs the collector |
| A — process-local (status quo) | Nothing | Formal codification of operator discipline (single process, single machine); no code change required |

If Aryan declines to adopt any shared infrastructure, the only safe posture is option A plus codified operator discipline — the current Chunk 7.20 state is already that posture.

---

## 6. Failure and concurrency semantics

For any shared backend (B, C, or D), these failure semantics must be specified in advance:

### 6.1 Backend unavailable (connection refused, timeout, host unreachable)

**POLICY: FAIL CLOSED.** `acquire()` must raise a well-typed exception (`RateLimitCoordinatorUnavailableError`) or block until the backend is available. It MUST NOT silently degrade to "no rate limit."

Rationale: Mohan's revision requires a code-level global limit. A fail-open fallback would silently violate the ToU.

### 6.2 Partial failure (lock acquired but timestamp update fails)

Release the lock, raise a `RateLimitCoordinatorPartialFailureError`, record the condition. The caller must treat this as a bounced request. The gap-logic protects correctness here: because the timestamp was never updated, the next acquisition will compute the gap against the previous recorded timestamp — strictly conservative.

### 6.3 Stale lock (previous holder crashed with lock held)

For Redis: the TTL on the SETNX key auto-releases the lock after a bounded time (e.g. `TTL = min_spacing + N seconds`). The next acquire picks it up.

For file locks: OS semantics usually release the lock on process exit. On NFS, stale locks can persist; `filelock` library documents this. A manual recovery procedure must be in the operator playbook.

### 6.4 Clock skew across machines

For a shared timestamp key (Redis / Postgres), use the **backend's clock** as the authority (`SERVER TIME` for Redis, `now()` on the DB server for Postgres), not the client's clock. This avoids drift between client machines affecting the gap computation.

For file-locks, each client reads/writes `last_acquire_time` based on its own clock — susceptible to drift. This is one more reason to prefer Redis/Postgres over file-lock for cross-machine deployments.

### 6.5 Timeout on acquire

A caller may want to bound its wait: `with coordinator.acquire(timeout=30.0): ...`. If the gap plus queue depth would exceed the timeout, raise `RateLimitAcquireTimeoutError`. The current `_ArxivCoordinator` does NOT support a timeout parameter; adding it is a backward-compatible extension to the Protocol signature.

### 6.6 Concurrency within one process on the shared backend

Even with a shared backend, the facade should keep a local `threading.Lock` so concurrent threads within one process do not race on the SETNX call. The local lock is cheap and avoids spurious retries on the shared backend.

---

## 7. Proposed interface and integration points

Minimum changes needed to integrate a chosen backend, assuming Aryan authorizes one:

### 7.1 Protocol (one new type)

Added to `rate_limit.py`:

```python
class RateLimitCoordinator(Protocol):
    min_spacing_seconds: float
    @property
    def last_acquire_time(self) -> float | None: ...
    def acquire(self, *, timeout: float | None = None) -> AbstractContextManager[None]: ...
```

`_ArxivCoordinator` would gain a no-op `timeout` parameter to match (default behavior ignores timeout).

### 7.2 Facade extension (one method signature; no behavior change for existing callers)

```python
class ArxivRateLimiter:
    def __init__(
        self,
        *,
        coordinator: RateLimitCoordinator | None = None,
        # existing args preserved
        min_spacing_seconds: float | None = None,
        clock: Callable[[], float] | None = None,
        sleeper: Callable[[float], None] | None = None,
    ) -> None:
        if coordinator is not None:
            self._coordinator = coordinator
            self._is_default = False
        elif (min_spacing_seconds, clock, sleeper) == (None, None, None):
            self._coordinator = _DEFAULT_COORDINATOR
            self._is_default = True
        else:
            # existing test-isolation path
            ...
```

### 7.3 Factory (configuration-driven; one new function)

```python
def make_default_coordinator_from_config(cfg: dict) -> RateLimitCoordinator:
    """Return the configured backend. Zero-config → in-process.

    Config shape (future, after Aryan authorization):
        backend: "in_process" | "file_lock" | "redis" | "postgres"
        file_lock:
            path: "/var/lock/arxiv_rate_limit.lock"
        redis:
            url: "redis://host:6379/0"
            key_prefix: "arxiv:rate:"
            ttl_seconds: 30
    """
```

The factory is NOT implemented in this chunk; it is a design placeholder.

### 7.4 Backend implementations (ONE module per backend, future authorized chunks)

```
src/nlp_semantic/ingestion/rate_limit_backends/
    __init__.py
    in_process.py        # moves _ArxivCoordinator here, re-exports from rate_limit.py
    file_lock.py         # future chunk; requires filelock dep
    redis.py             # future chunk; requires redis dep
```

### 7.5 Caller integration (zero caller changes if default-constructed)

Any future collector would use:
```python
limiter = ArxivRateLimiter()        # production: default coordinator
with limiter.acquire():
    response = httpx.get(...)       # the single request
```

If Aryan authorizes Redis, the production-default would route through `_DEFAULT_COORDINATOR` which the factory would configure as a `RedisCoordinator` instance at startup. **No caller signature changes.**

### 7.6 Integration points touching other modules

**None required.** The facade signature is backward-compatible; the Protocol is additive. The `arxiv_governance_decisions.md` document would be updated to name the deployed backend when the owner adopts one, and the `sources.yaml` `usage_restrictions` RATE LIMIT section would be updated to say "global cross-machine guarantee SATISFIED via `<backend>` coordinator" instead of "NOT SATISFIED by code." Neither update is in Chunk 7.21's scope.

---

## 8. Test plan

### 8.1 Protocol conformance (new unit tests, achievable without infrastructure)

- `test_arxiv_coordinator_satisfies_protocol`: `isinstance(_DEFAULT_COORDINATOR, RateLimitCoordinator)` (using `typing.runtime_checkable`).
- `test_facade_accepts_custom_coordinator`: pass a mock satisfying the Protocol; assert `ArxivRateLimiter(coordinator=mock)._coordinator is mock`.
- `test_timeout_parameter_default_is_none`: assert the default `acquire(timeout=None)` behaves identically to Chunk 7.20.

### 8.2 FileLockCoordinator (future-chunk tests; sketch)

- `test_file_lock_single_machine_serializes` (uses `subprocess` or `pytest-xprocess` to spawn two Python processes competing for the same lock file).
- Cross-NFS test — **NOT RUNNABLE in local CI without infrastructure.** Must be documented as operational verification.

### 8.3 RedisCoordinator (future-chunk tests; sketch)

- Unit: `fakeredis` as a drop-in substitute. Deterministic.
- Integration: a Redis test container (via `pytest-docker` or `testcontainers`). Not runnable without Docker.
- Load: a benchmark that two separate `python -m` processes on two separate machines coordinate correctly. **Only runnable with real Redis infrastructure.**

### 8.4 Honest multi-machine limitation

**No test suite can prove cross-machine coordination from a single-machine CI run.** The best achievable guarantee from automated tests is:
- Multiple PROCESSES on one machine do coordinate (via file lock or Redis).
- A mock Redis correctly simulates cross-machine semantics.

Actual cross-machine verification requires a staged deployment with two or more machines running the collector against a shared backend. This is an operational test, not a CI test.

### 8.5 Regression coverage

Every one of the 24 Chunk 7.20 `test_rate_limit.py` tests must continue to pass unchanged. The Protocol addition is purely additive.

---

## 9. Explicit unresolved decisions requiring Aryan's authorization

Each row is a decision that Chunk 7.21 does **not** make. Each is required before any implementation chunk may proceed.

| # | Decision | Options | Notes |
|---|---|---|---|
| D1 | **Which backend?** | (a) in-process + codified operator discipline, (b) file-lock (same-machine only), (c) Redis (cross-machine), (d) Postgres (cross-machine) | Option (c) is the only one that fully satisfies Mohan's cross-machine requirement in a single-step adoption. |
| D2 | **If Redis: self-hosted or managed?** | self-hosted on a dev server; managed (AWS ElastiCache, Upstash, …) | Managed is lower ops; self-hosted is cheaper but requires sysadmin. |
| D3 | **If file-lock: which path?** | A locally-mounted (NOT OneDrive) path; a project-local path (NOT the OneDrive-synced repo folder) | OneDrive-synced paths are explicitly unreliable for lock files. |
| D4 | **Failure policy** | fail-closed with timeout (raise `RateLimitCoordinatorUnavailableError`); fail-closed and block forever; fail-open to a stricter in-process limiter | fail-closed is strongly recommended. |
| D5 | **TTL / stale-lock timeout** | `min_spacing_seconds + N` where N = 2, 10, 30, …; configurable per deployment | Default: `min_spacing_seconds + 10.0 s = 13.0 s`. |
| D6 | **Clock authority** | backend server clock (recommended for Redis/Postgres); client clock (file-lock fallback) | Backend clock avoids drift. |
| D7 | **Configuration location** | env var, YAML config, settings module | Suggest an env var `ARXIV_RATE_COORDINATOR_URL` with "" meaning in-process. |
| D8 | **CI policy** | Run `fakeredis` unit tests always; integration tests only when a Redis test container is available | Document in a CI config file (does not currently exist). |
| D9 | **Operational playbook** | Who holds the Redis credentials; who monitors availability; who executes stale-lock recovery | A separate runbook document, not code. |
| D10 | **If Aryan declines all shared infrastructure** | Codify operator discipline formally (one process, one machine); keep Chunk 7.20 state; accept Chunk 7.19 B1 remains open indefinitely; the arXiv source promotion decision must consider whether operator discipline is an acceptable substitute for code-level global enforcement | This is the lowest-infrastructure path. |

---

## 10. Final status

**DESIGN ONLY. NO IMPLEMENTATION. NO COLLECTION. NO SOURCE PROMOTION.**

Specifically:
- No code modified.
- No module added.
- No test added.
- No dependency added.
- No collector created.
- No network request made.
- No metadata collected or downloaded.
- No PDF, TeX, or source archive touched.
- No dataset record, annotation, or split created.
- No taxonomy modified.
- No model, training, or evaluation code changed.
- No source promoted; `src_08ee850ba4b54d1b81cdbd652809b613` remains `review_status: unreviewed`.
- Ashok APPROVE and Mohan REVISE outcomes preserved.
- No fabricated reviewer identity, date, or sign-off.
- No stage, no commit, no push, no branch switch.
- Teammate directories (`src/ml`, `src/recommender`, `src/backend`) do not exist and were not created.
- Pre-existing `tests/dataset/` collection error unchanged.
- Chunk 7.19 B1 / Chunk 7.20 B1 (global cross-machine rate-limit guarantee): **STILL BLOCKED** after Chunk 7.21. This chunk describes the smallest change that WOULD close it, pending Aryan's authorization on D1-D10.

### 10.1 What this chunk is NOT

- NOT a resolution of the global rate-limit blocker.
- NOT an authorization to adopt Redis or any other backend.
- NOT a commitment that an implementation chunk will follow.
- NOT a change to the arXiv source review status.

### 10.2 What this chunk IS

- A documented design decision tree for Aryan.
- A documented interface (`RateLimitCoordinator` Protocol) that any backend must satisfy.
- Failure-semantics specification (fail-closed; clock authority; stale-lock handling).
- Explicit infrastructure-decision table (D1-D10).

### 10.3 Recommended next step

Await Aryan's decision on D1 (which backend) and D10 (whether any shared infrastructure is acceptable). If option (a) is chosen (keep in-process + codify operator discipline), no implementation chunk is required and the Chunk 7.20 state can be presented to the Chunk 7.17-§5.5 reviewers as-is. If option (c) Redis is chosen, a future narrow implementation chunk adds the `RedisCoordinator` backend, the `fakeredis` test harness, and the `requirements.txt` update — in that order — then a follow-up human review decides whether the global requirement is now satisfied.

---

## 11. File manifest for Chunk 7.21

| Path | Action | Why |
|---|---|---|
| [`reports/chunk_7_21_shared_rate_limit_architecture_design.md`](chunk_7_21_shared_rate_limit_architecture_design.md) | **CREATED** (this file) | Required chunk deliverable. |
| Everything else in the working tree | **UNCHANGED** | Design-only chunk. |

---

## 12. Confirmation — no modification, no collection, no promotion

- Repository was **NOT** modified except for the creation of this single report file.
- No stage, no commit, no push, no branch switch.
- No API request initiated.
- No metadata collected or downloaded.
- Source `review_status: unreviewed` unchanged.
- Human review outcomes (Ashok APPROVE / Mohan REVISE) preserved.
- Protected hashes (`PROJECT_HANDOFF.md`, `hybrid_dataset/raw/.gitkeep`) unchanged.
- No teammate directory touched (none exist).
- Pre-existing `tests/dataset/` collection error unchanged.
- Global rate-limit blocker (Chunk 7.19 B1 / Chunk 7.20 B1) is NOT resolved by Chunk 7.21.
