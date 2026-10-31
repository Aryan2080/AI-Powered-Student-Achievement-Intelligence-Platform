# Chunk 7.22 — Redis Shared Rate-Limit Implementation

**Report type:** implementation report.
**Generated:** 2026-10-24 (session date).
**Final governance status:** `UNREVIEWED — REDIS COORDINATOR IMPLEMENTED + UNIT-TESTED. INTEGRATION WITH A REAL REDIS SERVER NOT VERIFIED (NO INFRASTRUCTURE AVAILABLE).`

> Chunk 7.22 implements the Chunk 7.21 §Option C design: a Redis-backed `RedisCoordinator` behind the existing `ArxivRateLimiter` abstraction. The code and its atomic Lua scripts are unit-tested against `fakeredis[lua]`. **A real Redis integration test was NOT performed** — no infrastructure is deployed and no `ARXIV_TEST_REDIS_URL` is configured in this environment. Chunk 7.19 B1 (global cross-machine rate-limit guarantee) is **not resolved**; it is now UNBLOCKED pending a deployment + verification step.

---

## 1. Starting repository state

| Field | Value |
|---|---|
| Branch | `feature/nlp-semantic` |
| HEAD before + after | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` (unchanged; no commit) |
| Remote sync | in sync (not pushed) |
| Working tree before | ` M hybrid_dataset/metadata/sources.yaml` (post-Chunk-7.20); `?? PROJECT_HANDOFF.md`; `?? hybrid_dataset/metadata/arxiv_governance_decisions.md`; `?? reports/`; `?? src/nlp_semantic/ingestion/arxiv_governance.py`; `?? src/nlp_semantic/ingestion/rate_limit.py`; `?? tests/ingestion/test_arxiv_governance.py`; `?? tests/ingestion/test_rate_limit.py` |
| Protected hash `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` — verified at start + end |
| Protected hash `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` — verified at start + end |

Preserved existing user changes: ` M hybrid_dataset/metadata/sources.yaml` was already in the working tree (Chunk 7.20 wording corrections, Chunk 7.18 arXiv entry, Chunk 7.15 arXiv registration). It is **not** touched in Chunk 7.22.

---

## 2. Files inspected (read-only, Phase 1)

- `reports/chunk_7_21_shared_rate_limit_architecture_design.md`
- `reports/chunk_7_20_arxiv_rate_limit_remediation.md`
- `src/nlp_semantic/ingestion/rate_limit.py`
- `src/nlp_semantic/ingestion/arxiv_governance.py`
- `tests/ingestion/test_rate_limit.py`
- `hybrid_dataset/metadata/sources.yaml`
- `hybrid_dataset/metadata/arxiv_governance_decisions.md`
- `requirements.txt`
- `src/nlp_semantic/ingestion/__init__.py`
- `pyproject.toml`

---

## 3. Files modified / created

| Path | Action | Rationale |
|---|---|---|
| [`src/nlp_semantic/ingestion/rate_limit.py`](../src/nlp_semantic/ingestion/rate_limit.py) | **EXTENDED** | Added `RateLimitCoordinator` typing Protocol (`@runtime_checkable`); `RateLimitCoordinatorUnavailableError`; `RateLimitAcquireTimeoutError`; two Lua scripts (`_ACQUIRE_LUA`, `_RELEASE_LUA`); `RedisCoordinator` class; `COORDINATOR_URL_ENV_VAR` constant; `make_coordinator_from_env()` factory. Chunk 7.20 behavior and public surface preserved byte-for-byte for existing callers. |
| [`tests/ingestion/test_redis_rate_limit.py`](../tests/ingestion/test_redis_rate_limit.py) | **CREATED** | 31 unit tests covering Protocol conformance, initialization validation, atomic acquire/release, gap enforcement, cross-coordinator mutual exclusion, exception safety, factory configuration parsing, URL-not-leaked assertions, in-process co-existence. Plus 1 integration test correctly skipped when `ARXIV_TEST_REDIS_URL` is unset. |
| [`requirements.txt`](../requirements.txt) | **MODIFIED** | Added `redis>=5,<6` and `fakeredis[lua]>=2,<3` with documentation comments. |
| [`hybrid_dataset/metadata/arxiv_governance_decisions.md`](../hybrid_dataset/metadata/arxiv_governance_decisions.md) | **MODIFIED** | Updated §Revision 1 to document (a) the Redis coordinator is now implemented, (b) `ARXIV_RATE_COORDINATOR_URL` selects the backend, (c) fail-closed semantics, (d) deployment status: **NOT VERIFIED with a real Redis server**. |
| [`reports/chunk_7_22_redis_rate_limit_implementation.md`](chunk_7_22_redis_rate_limit_implementation.md) | **CREATED** (this file) | Required chunk deliverable. |

**Explicitly NOT changed:**
- `src/nlp_semantic/ingestion/arxiv_governance.py` — unchanged.
- `hybrid_dataset/metadata/sources.yaml` — Chunk 7.20 wording preserved byte-identical. The brief source-entry text still points to the governance decisions document, which now carries the Redis update.
- `tests/ingestion/test_rate_limit.py` — Chunk 7.20 version preserved; 24 tests still pass.
- `tests/ingestion/test_arxiv_governance.py` — Chunk 7.18 version preserved; 76 tests still pass.
- `src/nlp_semantic/ingestion/__init__.py` — Chunk 7.22 symbols are importable directly from `nlp_semantic.ingestion.rate_limit`; adding them to the lazy registry is an optional cosmetic step out of scope.
- `pyproject.toml` — unchanged.
- `tests/__init__.py` — not created.
- `src/ml`, `src/recommender`, `src/backend` — do not exist; not touched.
- SIH source entry — byte-identical.
- Taxonomy / annotations / records / splits / models — unchanged.
- `review_status: unreviewed` — unchanged.

---

## 4. RedisCoordinator design

### 4.1 Keys and TTLs

| Key (default prefix `arxiv:rate:`) | Role | Set / cleared when |
|---|---|---|
| `arxiv:rate:lock` | Single-connection mutex. Opaque client token as value. | `SET NX PX <lock_ttl_ms>` on acquire; `DEL` on release (token-scoped). |
| `arxiv:rate:last_ms` | Authoritative last-acquisition timestamp. Milliseconds since Unix epoch, computed from Redis `TIME`. | `SET PX <min_spacing_ms * 10>` on successful acquire. |

Key prefix is configurable via `key_prefix` constructor arg (default `"arxiv:rate:"`).

### 4.2 Atomic acquire — Lua script (verbatim)

```lua
local now = redis.call('TIME')
local now_ms = tonumber(now[1]) * 1000 + math.floor(tonumber(now[2]) / 1000)
local min_spacing_ms = tonumber(ARGV[1])
local lock_ttl_ms = tonumber(ARGV[2])
local token = ARGV[3]

local acquired = redis.call('SET', KEYS[1], token, 'NX', 'PX', lock_ttl_ms)
if not acquired then
    return {-1, 0}   -- lock held by someone else
end

local last = redis.call('GET', KEYS[2])
if last then
    local elapsed_ms = now_ms - tonumber(last)
    if elapsed_ms < min_spacing_ms then
        local deficit_ms = min_spacing_ms - elapsed_ms
        redis.call('DEL', KEYS[1])  -- release lock
        return {0, deficit_ms}      -- caller sleeps, retries
    end
end

redis.call('SET', KEYS[2], tostring(now_ms), 'PX', (min_spacing_ms * 10))
return {1, 0}   -- success; lock held, timestamp updated
```

Return-code semantics:
- `{1, 0}` — success. The Python client's `acquire` yields; the request body runs; the `finally` block calls the release script to free the lock.
- `{0, deficit_ms}` — gap unsatisfied. The lock was NOT retained (atomic `DEL` inside the same script). Caller sleeps `deficit_ms` and re-invokes the acquire script.
- `{-1, 0}` — another client holds the lock. Caller sleeps `locked_backoff_seconds` and retries.

### 4.3 Atomic release — Lua script

```lua
if redis.call('GET', KEYS[1]) == ARGV[1] then
    return redis.call('DEL', KEYS[1])
else
    return 0
end
```

Token-scoped release prevents a client from accidentally deleting another client's lock after a stale-TTL expiry + re-acquisition race.

### 4.4 Clock authority

Redis `TIME` is the authoritative clock for the gap computation. Participating clients do NOT need synchronized local clocks for correctness. The Python-side `clock` / `sleeper` arguments control only the local sleep durations (deficit sleep, locked backoff) and the client-local `last_acquire_time` introspection attribute.

### 4.5 In-process serialization

Each `RedisCoordinator` instance holds a `threading.Lock`. The lock serializes threads from the same coordinator object within one process so they do not thrash Redis with concurrent `SETNX` calls. This is a per-process optimization and does not weaken the cross-process / cross-machine guarantees.

### 4.6 Retry budget

- `max_attempts` (default 40) bounds the retry loop; exceeding raises `RateLimitAcquireTimeoutError`.
- Each attempt costs at most one `evalsha` round-trip; worst-case wait is bounded by `max_attempts * (locked_backoff_seconds OR deficit)` ≈ 40 × 3 s = 2 min at `min_spacing_seconds = 3`.

### 4.7 Public API shape

| Symbol | Kind | Purpose |
|---|---|---|
| `RateLimitCoordinator` | `typing.Protocol`, `@runtime_checkable` | Backend abstraction. Any coordinator must expose `min_spacing_seconds`, `last_acquire_time`, `acquire()`. |
| `RedisCoordinator` | class | Redis-backed implementation. |
| `COORDINATOR_URL_ENV_VAR` | `str = "ARXIV_RATE_COORDINATOR_URL"` | Canonical config env var (Chunk 7.21 §7.3). |
| `make_coordinator_from_env(env=None)` | factory | Dispatches on URL scheme; fail-closed. |
| `RateLimitCoordinatorUnavailableError` | exception | Redis unavailable, timeout, Lua error, missing `redis` lib. |
| `RateLimitAcquireTimeoutError` | exception | Retry budget exhausted. |

### 4.8 Backward compatibility

The Chunk 7.20 `ArxivRateLimiter` and `_ArxivCoordinator` are unchanged. Default construction still returns a facade over `_DEFAULT_COORDINATOR` (in-process). The 24 Chunk 7.20 tests pass unchanged.

---

## 5. Configuration and infrastructure requirements

### 5.1 Environment variable

`ARXIV_RATE_COORDINATOR_URL` (canonical, per Chunk 7.21 §7.3). Values:

| Value | Behavior |
|---|---|
| unset / empty / whitespace-only | `_DEFAULT_COORDINATOR` (in-process; status quo). |
| `in_process:` | Same as empty — explicit opt-in to the status quo. |
| `redis://host:port/db` | `RedisCoordinator` via `redis.Redis.from_url(…)` with `socket_timeout=5.0` and `decode_responses=True`. On construction, a `PING` is sent; failure raises `RateLimitCoordinatorUnavailableError`. |
| `rediss://host:port/db` | Same as `redis://` but TLS. |
| anything else | `ValueError`. The invalid value is deliberately NOT echoed in the error (may contain credentials). |

### 5.2 Infrastructure NOT provisioned by this chunk

Per Chunk 7.22 §3 ("You MUST NOT: Provision Redis infrastructure. Create cloud resources. …"), Chunk 7.22 did not:
- Deploy a Redis server anywhere.
- Create or manage Redis accounts.
- Store or invent credentials.
- Configure network reachability to any Redis instance.
- Set `ARXIV_RATE_COORDINATOR_URL` in any environment.

What Aryan must do before cross-machine coordination is actually operational:
1. Decide on a Redis endpoint (self-hosted or managed; owner authorization gate D1 from Chunk 7.21).
2. Set `ARXIV_RATE_COORDINATOR_URL=redis://…` in the environment of every machine that will run the collector.
3. Verify the Redis endpoint is reachable from every machine.
4. Verify TTL-based stale-lock recovery actually works in the deployed environment.
5. Run a staged multi-machine test and record the result (operational verification; not a CI test).

Until items 1-5 are complete, **cross-machine coordination remains NOT VERIFIED** and the `review_status` of the arXiv source must stay `unreviewed`.

### 5.3 Credential handling

- `make_coordinator_from_env` never prints or echoes the configured URL in any error message or log line. All error messages reference the env var name (`ARXIV_RATE_COORDINATOR_URL`), not the value.
- The `secret_url` test (`test_unknown_scheme_does_not_leak_url_in_error`, `test_unreachable_redis_fail_closed_no_url_leak`) asserts this.
- The `RedisCoordinator` constructor does not store the URL; only the `redis.Redis` client object.

---

## 6. Failure semantics (fail-closed)

| Scenario | Behavior |
|---|---|
| `ARXIV_RATE_COORDINATOR_URL=redis://…` but `redis` Python client not installed | `make_coordinator_from_env` raises `RateLimitCoordinatorUnavailableError`. No fallback to in-process. |
| Redis unreachable (connection refused, DNS failure, TCP timeout) | `PING` inside `make_coordinator_from_env` raises; wrapped in `RateLimitCoordinatorUnavailableError`. The URL is NOT echoed. |
| Redis connection drops mid-acquire | `evalsha` raises; caught in `acquire()` and wrapped in `RateLimitCoordinatorUnavailableError`. The acquire context body does NOT execute. |
| Lua-script runtime error | Treated as a Redis exception; same path as above. |
| Acquire retry budget exhausted (`max_attempts`) | `RateLimitAcquireTimeoutError` raised; no slot acquired; body does NOT execute. |
| Request body raises after a successful acquire | `finally` block runs the release script. If release itself fails, exception is swallowed (TTL will clean up the lock); the original body exception propagates. |
| Stale lock after a client crash | TTL on `arxiv:rate:lock` (default 10 s; configurable via `lock_ttl_seconds`) auto-releases. Next client's `SET NX PX` succeeds. The gap-logic protects correctness: the previous `last_ms` persists for `min_spacing_ms * 10 = 30 s`, so the next acquire sees a conservative gap. |
| Clock skew across machines | Not a concern. Redis `TIME` is the authoritative clock for the gap; client-local `clock`/`sleeper` are used only for local sleep durations. |

**Explicit non-guarantees:**
- Fail-closed does NOT prevent **all** distributed failures. A Redis multi-master partition could, in theory, admit two slots in a short window. The current implementation uses a single Redis endpoint; multi-master requires the Redlock algorithm, which is out of scope.
- A healthy Redis is required. The policy says "if Redis is down, the collector MUST stop" — this is the correct behavior but means Redis availability becomes a prerequisite for the collector.

---

## 7. Test results (independently re-executed in this chunk)

### 7.1 New Redis-coordinator tests

Command:
```
python -m pytest tests/ingestion/test_redis_rate_limit.py --tb=short -v
```

| Metric | Count |
|---|---|
| Passed | **31** |
| Failed | 0 |
| Skipped | **1** (integration test, no `ARXIV_TEST_REDIS_URL`) |
| Collection errors | 0 |
| Completed | **Yes** |

Breakdown by test class:
- `TestProtocolConformance` — 2 passed (`isinstance` against the `@runtime_checkable` Protocol; attribute/shape).
- `TestInitialization` — 7 passed (`min_spacing_seconds` lower bound, `lock_ttl > min_spacing`, `max_attempts > 0`, `locked_backoff > 0`, non-empty prefix, custom prefix, default-OK).
- `TestAcquireRelease` — 3 passed (lock set + released + `last_ms` written; TTL on `last_ms`; token-scoped release).
- `TestGapEnforcement` — 2 passed (primed-old timestamp → zero sleeps; primed-NOW → deficit path + `RateLimitAcquireTimeoutError`).
- `TestConcurrency` — 2 passed (two coordinators sharing one fakeredis cannot both hold the lock; per-coordinator threading.Lock serializes same-coordinator threads).
- `TestExceptionSafety` — 4 passed (body exception releases lock; `register_script` connection failure → `RateLimitCoordinatorUnavailableError`; acquire failure wrapped; no silent fallback on Redis error — body does NOT execute).
- `TestFactory` — 9 passed (empty env, unset var, empty value, whitespace, `in_process:`, unknown scheme ValueError, URL-not-leaked in ValueError, unreachable Redis fail-closed + URL-not-leaked, canonical env var name).
- `TestInProcessCompatibility` — 2 passed (default facade still works; injectable clock/sleeper still works).
- `TestRedisIntegration` — 1 **skipped** with reason: `"ARXIV_TEST_REDIS_URL not set; Redis integration tests require a running Redis test server. Not run in this chunk."`

### 7.2 Full ingestion suite (regression check)

```
python -m pytest tests/ingestion/ --tb=short
```

| Metric | Count |
|---|---|
| Passed | **206** |
| Failed | 0 |
| Skipped | 5 (= 4 pre-existing inventory skips + 1 Redis integration skip) |
| Collection errors | 0 |

Baseline (post-Chunk-7.20): 175 passed, 4 skipped. Delta: **+31 passed, +1 skipped** — exactly matching the new Redis test module. **Zero regression** on the 175 pre-Chunk-7.22 tests.

### 7.3 Schema + ingestion + smoke (broader regression)

```
python -m pytest tests/schema/ tests/ingestion/ tests/test_smoke.py --tb=short
```

| Metric | Count |
|---|---|
| Passed | **440** |
| Failed | 0 |
| Skipped | 5 |
| Collection errors | 0 |

Baseline (post-Chunk-7.20): 409 passed, 4 skipped. Delta: +31 / +1 — same as §7.2.

### 7.4 Dataset test collection (pre-existing)

```
python -m pytest tests/dataset/ --tb=line
```

| Metric | Count |
|---|---|
| Passed | 0 |
| Failed | 0 |
| Skipped | 0 |
| Collection errors | **3** |
| Completed | **No — collection interrupted** |

Error unchanged since Chunk 7.15: `ModuleNotFoundError: No module named 'tests.dataset'`. Root cause: an unrelated `tests` package in the user's Python 3.13 site-packages shadows the local `tests/` directory. **Not fixed in this chunk** per Chunk 7.22 §8 ("Do not claim the existing dataset collection error is resolved unless it is actually resolved").

### 7.5 Real-Redis integration tests — NOT RUN

The single `TestRedisIntegration::test_real_redis_coordinator` test is marked:

```python
requires_real_redis = pytest.mark.skipif(
    not os.environ.get("ARXIV_TEST_REDIS_URL"),
    reason="ARXIV_TEST_REDIS_URL not set; Redis integration tests require ...",
)
```

`ARXIV_TEST_REDIS_URL` is **not set** in this environment, so the test correctly skipped. Cross-machine behavior was NOT verified against a real Redis in this chunk. See §10.

---

## 8. Implementation status by requirement

Required readings per Chunk 7.22 §9:

| Requirement | Implemented | Unit-tested | Integration-tested | Not verified | Requires infra |
|---|---|---|---|---|---|
| `RateLimitCoordinator` Protocol | ✓ | ✓ (`TestProtocolConformance`) | n/a | — | — |
| `RedisCoordinator` class | ✓ | ✓ (31 unit tests) | ✗ | **cross-machine behavior** | ✓ Redis server |
| Atomic acquire Lua script | ✓ | ✓ (`TestAcquireRelease`, `TestGapEnforcement`, `TestConcurrency`) | ✗ against real Redis | TIME-with-real-clock-skew between genuinely different machines | ✓ |
| Atomic release Lua script | ✓ | ✓ (`test_release_is_token_scoped`) | ✗ | — | — |
| Min 3-second interval | ✓ (`min_spacing_seconds` validated; Lua compares `elapsed_ms` to `min_spacing_ms`) | ✓ | ✗ against real Redis | — | — |
| Fail-closed on connection failure | ✓ | ✓ (`TestExceptionSafety`, `TestFactory`) | ✗ (would need actual-Redis outage to test) | real connection-drop-mid-request behavior | — |
| Fail-closed on timeout | ✓ (`socket_timeout=5.0` + wrap in `RateLimitCoordinatorUnavailableError`) | ✓ (via MagicMock side effect) | ✗ | real wall-clock timeout behavior | — |
| No silent fallback to in-process on explicit `redis://` config | ✓ | ✓ (`test_no_silent_fallback_to_in_process_on_redis_error`, `test_unreachable_redis_fail_closed_no_url_leak`) | n/a | — | — |
| Bounded retry (`max_attempts`) | ✓ | ✓ (`TestGapEnforcement`, `TestConcurrency`) | n/a | — | — |
| Key namespace with explicit prefix | ✓ (`key_prefix` kwarg; default `arxiv:rate:`) | ✓ (`test_custom_key_prefix_used`) | n/a | — | — |
| Redis server-time via `TIME` | ✓ (Lua `redis.call('TIME')`) | ✓ (fakeredis supports TIME) | ✗ cross-machine | — | — |
| Avoid unnecessary key growth | ✓ (two keys per prefix; both have TTL) | ✓ (`test_last_ms_has_ttl`; lock has TTL set in Lua) | n/a | — | — |
| Injectable clock/sleeper preserved | ✓ (Chunk 7.20 facade unchanged + `RedisCoordinator` also accepts both) | ✓ (`TestInProcessCompatibility::test_injectable_clock_and_sleeper_still_work`) | n/a | — | — |
| Test-specific state isolation | ✓ (per-test fakeredis fixture; autouse `_reset_default_coord`) | ✓ | n/a | — | — |
| `ARXIV_RATE_COORDINATOR_URL` env-var config | ✓ | ✓ (9 factory tests) | n/a | — | — |
| URL-not-leaked-in-errors | ✓ | ✓ (2 explicit tests with sentinel passwords) | n/a | — | — |
| Dependency added to `requirements.txt` | ✓ (`redis>=5,<6`, `fakeredis[lua]>=2,<3`) | ✓ (import succeeds; tests pass) | n/a | — | — |
| **Cross-machine 3-second-interval guarantee verified under real deployment** | — | — | ✗ | **NOT VERIFIED** | ✓ real Redis + ≥ 2 machines + staged test |

---

## 9. Infrastructure authorization status

| Boundary from Chunk 7.22 §3 | Observed in this chunk |
|---|---|
| MAY implement Redis coordinator | ✓ Implemented. |
| MAY add Redis client dep | ✓ Added `redis>=5,<6`. |
| MAY add Redis test library | ✓ Added `fakeredis[lua]>=2,<3`. |
| MAY use an authorized local test Redis | ✗ Not available in this environment; integration tests skipped. |
| MUST NOT provision Redis infrastructure | ✓ No infrastructure provisioned. |
| MUST NOT create cloud resources | ✓ |
| MUST NOT create/modify Redis accounts | ✓ |
| MUST NOT invent credentials | ✓ Factory never fabricates URLs or passwords. |
| MUST NOT connect to unknown/production Redis | ✓ `ARXIV_RATE_COORDINATOR_URL` unset; no connection attempted. |
| MUST NOT perform network requests to arXiv | ✓ Zero network I/O. |
| MUST NOT collect metadata | ✓ |
| MUST NOT create a collector | ✓ |
| MUST NOT promote the source | ✓ `review_status: unreviewed` unchanged. |
| MUST NOT change Ashok APPROVE / Mohan REVISE | ✓ `arxiv_governance_decisions.md` origin note preserved. |

---

## 10. Limitations and unresolved issues

| # | Item | Severity | Notes |
|---|---|---|---|
| L1 | **No real-Redis integration test performed.** Cross-machine 3-second guarantee is NOT VERIFIED. | **HIGH if reviewers require code-tested cross-machine behavior.** | Requires Aryan to designate a Redis test endpoint (or local Docker Redis) and set `ARXIV_TEST_REDIS_URL` before an integration-test chunk can run. |
| L2 | **No deployment of Redis infrastructure.** `ARXIV_RATE_COORDINATOR_URL` is unset in all known environments. The in-process coordinator remains the operational default. | **HIGH for live-collection readiness; LOW for the current pre-collection posture.** | Deployment decision is out of scope for this chunk. |
| L3 | **Single-Redis-endpoint design.** The implementation uses one Redis instance, not Redlock across multiple masters. A partition in a multi-master Redis cluster could, in principle, admit two slots. | **LOW** at the project's current scale (a single Redis is standard). | Redlock could be a future upgrade; out of scope. |
| L4 | **ArxivRateLimiter facade does not yet expose a `coordinator=` kwarg.** Currently the Redis path is reached only via `make_coordinator_from_env()`; the facade still defaults to `_DEFAULT_COORDINATOR`. A future chunk could add `ArxivRateLimiter(coordinator=make_coordinator_from_env())` glue if callers want it. | **LOW.** No caller exists today anyway (no collector). | — |
| L5 | **Withdrawn-regex heuristic** (Chunk 7.19 B5) — not addressed in Chunk 7.22. | **LOW-MEDIUM.** | Separate future chunk. |
| L6 | **arXiv version not in Achievement schema** — unchanged. | **LOW.** | — |
| L7 | **Pre-existing `tests/dataset/` collection error** — unchanged. | **LOW** (does not affect Chunk 7.22 verification). | — |
| L8 | **No integration with any collector.** No ingestion / collection / logger pathway invokes the coordinator today. The coordinator remains a policy surface. | **MEDIUM — expected until a collector chunk lands.** | — |

---

## 11. Protected hash verification

Checked at session start AND at session end:

| File | Expected | Observed (end) | Match |
|---|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

---

## 12. Confirmation — no source promotion, no data collection

- No API request initiated ✓
- No metadata collected ✓
- No download performed (no PDF, no TeX, no source archive, no full text) ✓
- No achievement record created ✓
- No annotation created ✓
- No dataset split generated ✓
- No taxonomy promoted ✓
- No source promoted; `src_08ee850ba4b54d1b81cdbd652809b613` remains `review_status: unreviewed` ✓
- Ashok APPROVE and Mohan REVISE outcomes preserved verbatim in `arxiv_governance_decisions.md` ✓
- No reviewer identity invented or sign-off recorded ✓
- No stage, no commit, no push, no branch switch ✓
- No teammate directory touched (`src/ml`, `src/recommender`, `src/backend` do not exist) ✓
- `pyproject.toml` untouched ✓
- `tests/__init__.py` not created ✓
- No modification to installed Python packages beyond adding `redis` and `fakeredis[lua]` as declared project dependencies ✓
- Protected hashes unchanged ✓
- Chunk 7.4-D reviewer-independence stop preserved ✓
- Pre-existing `tests/dataset/` collection error not silently fixed ✓
- Cross-machine coordination is NOT claimed to be operational — explicitly NOT VERIFIED (L1) ✓

---

## 13. Final readiness assessment

**COORDINATION-CODE IMPLEMENTED AND UNIT-TESTED. CROSS-MACHINE OPERATIONAL VERIFICATION PENDING.**

- The `RedisCoordinator` is implemented, documented, and exercised by 31 passing unit tests via `fakeredis[lua]`.
- The configuration surface (`ARXIV_RATE_COORDINATOR_URL`) is in place with fail-closed semantics and credential-safe error messages.
- The `requirements.txt` declares the deps; adopting them is a per-environment install.
- No real Redis deployment exists; a cross-machine deployment and a staged two-machine integration test are the remaining operational prerequisites before the Chunk 7.19 B1 global blocker can be declared RESOLVED.

### Recommended next steps (none authorized in this chunk)

1. Aryan designates a Redis endpoint (self-hosted or managed).
2. Set `ARXIV_RATE_COORDINATOR_URL` in the collector-host environments.
3. Create a short integration-test chunk that sets `ARXIV_TEST_REDIS_URL` and runs `TestRedisIntegration`.
4. Perform a two-machine staged test (operational, not CI).
5. Based on the result, a new human review decides whether Chunk 7.19 B1 is closed and whether the arXiv source may be promoted to `review_status: verified`.

Until those steps complete, the source stays `unreviewed`.

**This chunk implements coordination only. It does not authorize source promotion, data collection, or dataset release.**
