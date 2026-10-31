# Chunk 7.20 — arXiv Rate-Limit Remediation and Governance-Wording Accuracy

**Report type:** narrowly scoped remediation of concrete gaps identified by the Chunk 7.19 audit.
**Generated:** 2026-10-24 (session date).
**Final governance status:** `UNREVIEWED — PROCESS-LOCAL SAFEGUARDS IMPROVED; GLOBAL CROSS-MACHINE RATE LIMIT REMAINS BLOCKED.`

> This chunk does NOT promote the arXiv source and does NOT create a collector. It fixes four specific gaps from the Chunk 7.19 audit (process-local sharing, exception safety, multi-instance safety, misleading `sources.yaml` wording). A new human review of this remediation is still required before promotion.

---

## 1. Starting repository state

| Field | Value |
|---|---|
| Branch | `feature/nlp-semantic` |
| HEAD (unchanged) | `c8c1b8084ff9d15955e0b456d9eccbe9c4cf6d90` |
| Remote sync | in sync (not pushed) |
| Working tree before | ` M hybrid_dataset/metadata/sources.yaml` (Chunk 7.15 + 7.18 arXiv entry); `?? PROJECT_HANDOFF.md`; `?? hybrid_dataset/metadata/arxiv_governance_decisions.md`; `?? reports/`; `?? src/nlp_semantic/ingestion/arxiv_governance.py`; `?? src/nlp_semantic/ingestion/rate_limit.py`; `?? tests/ingestion/test_arxiv_governance.py`; `?? tests/ingestion/test_rate_limit.py` |
| Working tree after | same shape, with `sources.yaml`, `rate_limit.py`, and `test_rate_limit.py` edited in place; one new file added (`reports/chunk_7_20_arxiv_rate_limit_remediation.md`) |

Protected hashes verified at session start AND at session end:
- `PROJECT_HANDOFF.md` → `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` ✓
- `hybrid_dataset/raw/.gitkeep` → `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` ✓

Pre-remediation grep confirmed **no existing shared coordination mechanism** (no `multiprocessing.Lock`, no `fcntl.flock` / file lock, no Redis / SQLite / SQLAlchemy infrastructure anywhere under `src/`). The one grep hit (`source_registry.py`) is a false positive on `urllib.parse` — not a coordinator.

---

## 2. Audit findings addressed

The Chunk 7.19 audit identified five concrete gaps. This chunk's scope:

| # | Chunk 7.19 finding | Addressed? | How |
|---|---|---|---|
| 1 | `ArxivRateLimiter` is process-local and does not satisfy the global single-connection + 3-second requirement across machines. | **Honestly re-labelled.** The module docstring, `sources.yaml`, and `arxiv_governance_decisions.md` now explicitly state the global requirement is **NOT SATISFIED by code** and that operator discipline is the compensating control. No invented distributed coordinator. | §5 of this report |
| 2 | Multiple limiter instances in one process can bypass aggregate limits. | **Fixed.** Default-constructed `ArxivRateLimiter()` instances now share a module-level `_DEFAULT_COORDINATOR`. New test `test_default_construction_uses_shared_coordinator` asserts identity; `test_two_default_instances_share_last_acquire_time` asserts shared state. | §4 of this report |
| 3 | Exception-safety behavior is not test-covered. | **Fixed.** 4 new tests cover: lock release on body exception, `last_acquire_time` update on exception, concurrent-exception-does-not-deadlock, and 20-cycle state consistency (some with exceptions). | §6 of this report |
| 4 | `sources.yaml` describes restrictions as "PROHIBITED", potentially implying end-to-end enforcement. | **Fixed.** Three sections rewritten to say "DISALLOWED by project policy / policy surface only / no ingestion yet". | §8 of this report |
| 5 | Governance functions are not integrated into an actual collector / production ingestion pathway. | **Honestly re-labelled, NOT fixed.** No collector exists; this chunk does not create one (explicit scope boundary from §Important Scope Boundary of the Chunk 7.20 prompt). The source is still a policy surface awaiting a future authorized collector chunk. | §9 of this report |

---

## 3. Files changed

| Path | Action | Reason |
|---|---|---|
| [`src/nlp_semantic/ingestion/rate_limit.py`](../src/nlp_semantic/ingestion/rate_limit.py) | **REWRITTEN** | Introduces `_ArxivCoordinator` dataclass, module-level `_DEFAULT_COORDINATOR` singleton, and refactors `ArxivRateLimiter` to be a thin facade. Default construction shares the coordinator; explicit `clock`/`sleeper`/`min_spacing_seconds` yield test-isolated coordinators. |
| [`tests/ingestion/test_rate_limit.py`](../tests/ingestion/test_rate_limit.py) | **EXTENDED** | +1 autouse fixture (`_reset_default_coord`), +11 new tests covering shared default coordinator, concurrent default-instance serialization, exception safety, and global-requirement classification. |
| [`hybrid_dataset/metadata/sources.yaml`](../hybrid_dataset/metadata/sources.yaml) | **MODIFIED** (arXiv entry only; SIH entry byte-identical to prior state) | `OFFICIAL METADATA ENDPOINTS` section softened ("DISALLOWED by project policy / policy surface only / no ingestion yet"); `RATE LIMIT` section explicitly says "global cross-machine guarantee NOT SATISFIED by code (operator discipline required)"; `WITHDRAWALS` and `PRIVACY` sections softened. |
| [`reports/chunk_7_20_arxiv_rate_limit_remediation.md`](chunk_7_20_arxiv_rate_limit_remediation.md) | **CREATED** (this file) | Required deliverable. |

**Explicitly NOT changed in this chunk:**
- `src/nlp_semantic/ingestion/arxiv_governance.py` — content is unchanged; its docstring was already honest about policy surface vs enforcement (Chunk 7.18 wrote "This module is pure policy. It never performs API requests, downloads, or filesystem writes. Any future collector MUST route endpoint selection..."). No new changes required.
- `hybrid_dataset/metadata/arxiv_governance_decisions.md` — already documents the governance decisions correctly (Ashok APPROVE / Mohan REVISE preserved; implementation ≠ approval; process-local limitation named). No new changes required for Chunk 7.20 scope.
- `tests/ingestion/test_arxiv_governance.py` — the 76 tests still pass unchanged.
- All existing Pydantic schemas (`Achievement`, `Annotation`, `SourceRegistry`, `LabelTaxonomy`, `Evidence`, `ManifestEntry`) — byte-identical.
- SIH source entry — byte-identical.
- Teammate dirs (`src/ml`, `src/recommender`, `src/backend`) — do not exist; not touched.
- `pyproject.toml`, `tests/__init__.py`, installed Python packages — not touched.

---

## 4. Process-local limiter design (shared default coordinator)

### 4.1 Design

```
┌────────────────────────────────────────────────────────────────┐
│  Module: nlp_semantic.ingestion.rate_limit                     │
│                                                                 │
│  _ArxivCoordinator (dataclass)                                 │
│      min_spacing_seconds: float                                │
│      clock: Callable[[], float]                                │
│      sleeper: Callable[[float], None]                          │
│      _lock: threading.Lock                                     │
│      _last_acquire_time: float | None                          │
│      acquire() -> contextmanager                               │
│                                                                 │
│  _DEFAULT_COORDINATOR = _ArxivCoordinator(                     │
│      min_spacing_seconds=3.0,                                  │
│      clock=time.monotonic,                                     │
│      sleeper=time.sleep,                                       │
│  )                                                              │
│                                                                 │
│  ArxivRateLimiter (thin facade)                                │
│      __init__(min_spacing_seconds=None, *, clock=None,         │
│                sleeper=None):                                   │
│          # If any of (min_spacing_seconds, clock, sleeper)     │
│          # is explicitly passed → fresh per-instance           │
│          # coordinator (test-isolation path).                  │
│          # Otherwise → self._coordinator = _DEFAULT_COORDINATOR│
│      acquire() -> contextmanager                                │
│      is_shared_default: bool  (introspection property)         │
└────────────────────────────────────────────────────────────────┘
```

### 4.2 Rules

1. **Production path.** `ArxivRateLimiter()` with no args returns a facade over the module-level `_DEFAULT_COORDINATOR`. Every default limiter in the process shares the same single-connection lock and the same `last_acquire_time`.
2. **Test-isolation path.** Any of `min_spacing_seconds=`, `clock=`, or `sleeper=` triggers a fresh `_ArxivCoordinator`. The 36 pre-existing Chunk 7.18 tests all use this path (they pass custom clocks); they are unaffected.
3. **State updated BEFORE yield.** `_last_acquire_time` is set before the context manager yields, so an exception inside the body does not leave the gap stale. See §6.
4. **Lock always released.** `try: … finally: self._lock.release()` guarantees that even an exception inside the acquire body does not leave the lock stuck.
5. **No cross-process coordination.** By explicit design and by audit requirement (`§Phase 3 — do not invent a distributed system`), the limiter is single-process. See §5.

### 4.3 Public API (unchanged for production callers)

The Chunk 7.18 public surface — `ArxivRateLimiter`, `ArxivRateLimiter.acquire()`, `MIN_REQUEST_SPACING_SECONDS`, `last_acquire_time`, `min_spacing_seconds` — is preserved. One addition: `ArxivRateLimiter.is_shared_default` property for introspection.

The module also exports `_ArxivCoordinator`, `_DEFAULT_COORDINATOR`, and `_reset_default_coordinator_for_testing` (leading underscores → NOT public; test-only).

---

## 5. Multiple-instance behavior (Chunk 7.19 B3 closed)

### 5.1 Before Chunk 7.20

```python
a = ArxivRateLimiter()      # each has its own threading.Lock
b = ArxivRateLimiter()      # and its own _last_acquire_time
# a.acquire() and b.acquire() do NOT serialize against each other,
# and do NOT share the 3-second gap. Two instances halve the rate.
```

### 5.2 After Chunk 7.20

```python
a = ArxivRateLimiter()      # a._coordinator is _DEFAULT_COORDINATOR
b = ArxivRateLimiter()      # b._coordinator is _DEFAULT_COORDINATOR
assert a._coordinator is b._coordinator
# a.acquire() and b.acquire() SERIALIZE on the same lock.
# a.last_acquire_time == b.last_acquire_time at all times.
```

### 5.3 Verifying tests

| Test | Covers |
|---|---|
| `test_default_construction_uses_shared_coordinator` | `a._coordinator is b._coordinator is _DEFAULT_COORDINATOR`; both `is_shared_default` is True. |
| `test_explicit_args_bypass_default_coordinator` | Explicit `clock=` → `_coordinator is not _DEFAULT_COORDINATOR`; `is_shared_default is False`. |
| `test_two_default_instances_share_last_acquire_time` | After `a.acquire()`, `b.last_acquire_time == a.last_acquire_time`. Then `b.acquire()` 1 s later waits 2.0 s to satisfy the gap. |
| `test_single_connection_lock_serializes_across_default_instances` | 5 threads each create a different `ArxivRateLimiter()` and attempt to acquire concurrently; observed max concurrent holders = 1. |

---

## 6. Exception-safety tests

### 6.1 Before Chunk 7.20

The `acquire` method already used `try: … finally: self._lock.release()`, so lock release on exception was correct **by inspection** but **not covered by any test**. The Chunk 7.19 audit flagged this as B4.

### 6.2 After Chunk 7.20

Four new tests, all passing:

| Test | What it asserts |
|---|---|
| `test_exception_in_body_releases_lock` | `with lim.acquire(): raise _Boom()` — subsequent acquire after `clock.advance(10.0)` completes without hanging. |
| `test_last_acquire_time_updated_on_exception` | After an acquire that raises, `last_acquire_time` is still updated → the gap applies to the next acquisition (1 s later → 2 s wait). |
| `test_lock_free_after_concurrent_exception` | One thread raises inside `acquire()`, another thread acquires immediately after; neither deadlocks (`join(timeout=2.0)` + `is_alive()` check). |
| `test_many_acquisitions_state_consistency` | 20 cycles, every 3rd raises; final `last_acquire_time` matches `1000.0 + 19 * 10.0`; no sleeps required because each cycle advances the clock by 10 s. |

Combined with the pre-existing concurrency test (`test_single_connection_lock_serializes_threads`), the limiter's exception + concurrency behavior is now explicitly tested.

---

## 7. Global coordination assessment

### 7.1 Does the repository have a safe, supported shared-coordination mechanism?

**No.** Grep for all common patterns:

```
$ grep -rln "redis\|multiprocessing.Lock\|fcntl\.flock\|FileLock\|sqlite3\|
            sqlalchemy" src/
# No real hits — one false positive (urllib.parse in source_registry.py)
```

The repository has no Redis client, no file-lock utility (`fcntl` is unix-only and not imported anywhere; Python's `portalocker` or `filelock` are not in `requirements.txt`), no SQLite coordination, no distributed queue. No supported shared-coordination mechanism exists.

### 7.2 Conclusion

Per the Chunk 7.20 §Phase 3 explicit rule — "If no shared coordination mechanism exists: Do not invent a distributed system. Do not introduce an external dependency without explicit owner authorization. Do not claim the global requirement is satisfied. Document that global enforcement remains blocked." — this chunk does NOT introduce a distributed system. Global enforcement remains BLOCKED.

### 7.3 Documentation

The classification is documented in three places:

1. **Module docstring** (`src/nlp_semantic/ingestion/rate_limit.py` lines 15-30): "The Chunk 7.19 audit explicitly classifies the global requirement as NOT SATISFIED by this module."
2. **`sources.yaml` `usage_restrictions`:** "global cross-machine guarantee NOT SATISFIED by code (operator discipline required)".
3. **`arxiv_governance_decisions.md` §Revision 1:** retained from Chunk 7.18 — states the process-local limitation and the operator-discipline compensating control.

Also tested: `test_module_documents_global_not_satisfied` asserts the module docstring contains "not satisfied".

### 7.4 What infrastructure would be required before live collection

A future chunk authorized by the project owner could add ONE of:

- **File-lock-based coordinator.** A `filelock` or `portalocker` wrapper that persists `last_acquire_time` in a project-local file and serializes acquisitions across processes on the same machine. Would satisfy the single-machine aggregate requirement but not cross-machine.
- **Redis-based coordinator.** A Redis mutex with SETNX + TTL plus a timestamp key. Would satisfy cross-machine, at the cost of adding Redis as a runtime dependency.
- **SQLite WAL + advisory lock.** A SQLite-backed coordinator in a shared location. Cross-process on the same machine.

None of these are in scope for Chunk 7.20. They would require explicit owner authorization and a new chunk.

Alternatively, the project may **codify operator discipline** as the compensating control (single collector, single machine) and never ingest from multiple machines — which is the current documented posture.

---

## 8. Governance-wording corrections (`sources.yaml`)

### 8.1 Diff summary (concept)

Three sections of the arXiv entry's `usage_restrictions` and `mapping_notes` were softened:

| Section | Before (declarative) | After (policy-surface accurate) |
|---|---|---|
| **Official endpoints** | `HTML scraping of /abs, /pdf, /src, /html, /format on any arXiv host is PROHIBITED (Chunk 7.18 Rev 1).` | `HTML scraping of /abs, /pdf, /src, /html, /format is DISALLOWED; validate_metadata_endpoint rejects such URLs if invoked. Policy surface only; no ingestion yet.` |
| **Rate limit** | `Enforcement (process-local; operator discipline required for cross-process): src/nlp_semantic/ingestion/rate_limit.py.` | `Code enforcement (rate_limit.py) is PROCESS-LOCAL (Chunk 7.20 shared default coordinator); global cross-machine guarantee NOT SATISFIED by code (operator discipline required).` |
| **Withdrawals** | `WITHDRAWALS: comments matching withdrawn/retracted patterns via arxiv_governance.is_withdrawn() exclude a paper from eligible ingestion and linking.` | `WITHDRAWALS: is_withdrawn() flags withdrawn/retracted patterns in comments. Future ingestion MUST exclude flagged papers (policy obligation; no ingestion today).` |
| **Privacy / emails** | `Submitter contact emails redacted via arxiv_governance.redact_contact_emails (Chunk 7.18 Rev 4).` | `Submitter contact emails: redaction policy via redact_contact_emails (Chunk 7.18 Rev 4); no logger today — policy surface, not enforced.` |

### 8.2 What was preserved

- Source `review_status: unreviewed` — UNCHANGED. ✓
- Ashok APPROVE / Mohan REVISE outcomes in `arxiv_governance_decisions.md` — UNCHANGED. ✓
- CC0 1.0 license verbatim quote in `usage_restrictions` — UNCHANGED. ✓
- API ToU rate-limit verbatim quote — UNCHANGED. ✓
- Full-text / PDF / TeX / figure exclusion — UNCHANGED. ✓
- arXiv Bulk Data redistribution-prohibition verbatim quote — UNCHANGED. ✓
- Acknowledgment text — UNCHANGED. ✓
- SIH source entry — byte-identical to pre-Chunk-7.20 state (`ur_len=985, mn_len=1786` unchanged). ✓
- Append-only convention — honored; the arXiv entry edit replaces its own prior text, not the SIH entry. ✓
- No fabricated reviewer identity, timestamp, or sign-off. ✓

### 8.3 Field-length cap compliance

| Entry | `usage_restrictions` | `mapping_notes` |
|---|---|---|
| SIH (`src_5a89…`) | 985 chars | 1786 chars |
| arXiv (`src_08ee…`) | 1962 chars | 2001 chars (= 2000 after `str_strip_whitespace=True` trims the YAML block's trailing newline) |

Pydantic validation passes: both fields are ≤ 2000 characters after whitespace stripping.

---

## 9. Test verification — exact commands and results

Every count below is independently re-executed in this chunk, not copied from a prior report.

### 9.1 Rate-limit module only (fresh plus pre-existing)

```
python -m pytest tests/ingestion/test_rate_limit.py --tb=short -v
```

| Metric | Count |
|---|---|
| Passed | **24** |
| Failed | 0 |
| Skipped | 0 |
| Collection errors | 0 |
| Completed | **Yes** |

Breakdown by test class:
- `TestRateLimiterConstruction` — 5 passed (preserved from Chunk 7.18).
- `TestRateLimiterPacing` — 5 passed (preserved from Chunk 7.18).
- `TestRateLimiterConcurrency` — 2 passed (preserved from Chunk 7.18).
- `TestRateLimiterOperatorDisciplineDocumented` — 2 passed (1 pre-existing + 1 new `test_module_documents_global_not_satisfied`).
- **`TestSharedDefaultCoordinator`** — 4 passed (all new): default-instance identity, explicit-args isolation path, shared `last_acquire_time`, cross-instance lock serialization.
- **`TestRateLimiterExceptionSafety`** — 5 passed (4 new + 1 pre-existing `test_min_spacing_seconds_below_minimum_rejected_on_explicit_construction`): lock release on exception, `last_acquire_time` update on exception, concurrent-exception-no-deadlock, 20-cycle state consistency, below-minimum rejection.
- **`TestGlobalRequirementClassification`** — 1 passed (new): governance doc contains "process-local"/"cross-process"/"cross-machine" + "operator discipline".

### 9.2 Full ingestion suite

```
python -m pytest tests/ingestion/ --tb=short
```

| Metric | Count |
|---|---|
| Passed | **175** |
| Failed | 0 |
| Skipped | 4 |
| Collection errors | 0 |
| Completed | **Yes** |

Baseline: 164 (post Chunk 7.18). Delta: +11 (the 11 new tests added in this chunk). Zero regression on the 75 Chunk-7.18-pre-existing ingestion tests.

### 9.3 Schema + ingestion + smoke

```
python -m pytest tests/schema/ tests/ingestion/ tests/test_smoke.py --tb=short
```

| Metric | Count |
|---|---|
| Passed | **409** |
| Failed | 0 |
| Skipped | 4 |
| Collection errors | 0 |
| Completed | **Yes** |

Baseline: 398 (post Chunk 7.18). Delta: +11. Zero regression.

### 9.4 Dataset test collection (pre-existing)

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

Error unchanged since Chunk 7.15: `ModuleNotFoundError: No module named 'tests.dataset'`. Root cause: installed `tests` package in Python site-packages shadows the local repo's `tests/` directory. **Not fixed in this chunk** per the Chunk 7.20 prompt §Phase 5 ("Do not silently fix unrelated dataset collection errors").

### 9.5 Direct checks

- **Exception behavior directly tested:** YES (`TestRateLimiterExceptionSafety`, 4 new tests).
- **Multiple instances share coordination state:** YES (`test_two_default_instances_share_last_acquire_time`, `test_default_construction_uses_shared_coordinator`, `test_single_connection_lock_serializes_across_default_instances`).
- **Global requirement remains unresolved:** YES, honestly documented in code + `sources.yaml` + governance doc; test `test_governance_doc_states_global_blocked` asserts the governance doc still contains the operator-discipline / process-local language.

---

## 10. Remaining blockers

Blockers to source promotion ordered by severity:

| # | Blocker | Severity | Owner |
|---|---|---|---|
| B1 | **Global cross-machine rate-limit guarantee** remains blocked. The repository has no shared-coordination infrastructure (no Redis, no file lock, no DB). Compensating control is documented operator discipline (single process, single machine). | **HIGH if reviewers demand code-level global enforcement; LOW if reviewers accept operator discipline.** | Project owner decision. |
| B2 | **No ingestion / collection / logger pathway exists** anywhere in the repository. All governance functions remain policy surfaces with no production callers. | **HIGH if reviewers demand end-to-end enforcement; expected if reviewers accept "policy surfaces ready for a future collector."** | Project owner decision; a future chunk could create a collector that routes through the policy module. |
| B3 | **Pre-existing `tests/dataset/` collection error** (installed `tests` package in site-packages shadows the local one). | **LOW.** Does not affect Chunk 7.20 verification. | Separate narrow chunk. |
| B4 | **`sources.yaml` wording improvements** could be refined further. Current wording is accurate; future iterations may want to use even more precise "policy obligation" phrasing. | **LOW (cosmetic).** | Future refinement if the reviewers raise it. |
| B5 | **Chunk 7.19 B5 — withdrawal regex heuristics** (false positives / negatives). Not addressed in Chunk 7.20; was labeled LOW-MEDIUM. | **LOW-MEDIUM.** | Future refinement; `is_withdrawn` docstring explicitly says it is a positive signal, not a proof. |
| B6 | **arXiv version is not a schema field on `Achievement`.** Documented in Chunk 7.16 §F.7, Chunk 7.18, Chunk 7.19. Not changed in Chunk 7.20. | **LOW.** YAML-comment convention preserved. | Future schema chunk if reviewers want it. |

---

## 11. Protected hash verification

Checked at session start AND session end — both match:

| File | SHA-256 | Match |
|---|---|---|
| `PROJECT_HANDOFF.md` | `c3c59cc7b2df63d6d764a79d719b178a13307c3340797ece29f966aaa34f07f0` | ✓ |
| `hybrid_dataset/raw/.gitkeep` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` | ✓ |

---

## 12. Final `git status`

```
## feature/nlp-semantic...origin/feature/nlp-semantic
 M hybrid_dataset/metadata/sources.yaml
?? PROJECT_HANDOFF.md
?? hybrid_dataset/metadata/arxiv_governance_decisions.md
?? reports/
?? src/nlp_semantic/ingestion/arxiv_governance.py
?? src/nlp_semantic/ingestion/rate_limit.py
?? tests/ingestion/test_arxiv_governance.py
?? tests/ingestion/test_rate_limit.py
```

`git diff --stat` on `sources.yaml` shows 101 insertions, 0 deletions vs HEAD — the same total as after Chunk 7.18, because every Chunk 7.20 edit is a replacement within the uncommitted working-tree text (no net new lines).

HEAD unchanged at `c8c1b808...4cf6d90`. No stage, no commit, no push, no branch switch.

---

## 13. Confirmation — no API, no collection, no commits

- No API request initiated ✓
- No metadata collected ✓
- No download performed (no PDF, no TeX, no source archive, no full text) ✓
- No achievement record created ✓
- No annotation created ✓
- No dataset split generated ✓
- No taxonomy promoted ✓
- No source promoted (`review_status: unreviewed` unchanged) ✓
- No reviewer identity invented ✓
- No fake reviewer approval recorded ✓
- No staging performed ✓
- No commits performed ✓
- No pushes performed ✓
- No branch switched, created, or deleted ✓
- No teammate directory touched (none exist) ✓
- `pyproject.toml` not modified ✓
- `tests/__init__.py` not created ✓
- Installed Python packages not modified ✓
- Protected file hashes unchanged ✓
- Chunk 7.4-D reviewer-independence stop preserved ✓
- Ashok APPROVE and Mohan REVISE outcomes preserved verbatim in `arxiv_governance_decisions.md` ✓
- No invented distributed-system / Redis / file-lock dependency added ✓

---

## 14. Completion decision

### Status

**PROCESS-LOCAL SAFEGUARDS IMPROVED; GLOBAL RATE LIMIT REMAINS BLOCKED.**

- Chunk 7.19 B2 (multi-instance bypass): **CLOSED.** Default `ArxivRateLimiter()` instances now share the module-level `_DEFAULT_COORDINATOR`, verified by 4 new tests.
- Chunk 7.19 B3 (single-instance within-process assumption): **CLOSED** as the direct consequence of the above.
- Chunk 7.19 B4 (exception-safety not test-covered): **CLOSED.** 4 new tests cover lock release on exception, `last_acquire_time` update on exception, concurrent-exception-no-deadlock, and 20-cycle state consistency.
- Chunk 7.19 B7 (sources.yaml declarative "PROHIBITED" wording): **CLOSED.** Four sections rewritten to the "policy surface / no ingestion yet / NOT SATISFIED by code" phrasing.
- Chunk 7.19 B1 (global cross-machine rate limit): **STILL BLOCKED by design.** No shared-coordination infrastructure exists; chunk did not invent one.
- Chunk 7.19 B2 (no ingestion pathway): **STILL BLOCKED by design.** No collector exists; chunk did not create one.

### Source governance

The arXiv source `src_08ee850ba4b54d1b81cdbd652809b613` remains `review_status: unreviewed`. Ashok's `approve` and Mohan's `revise` are preserved. No promotion was performed. A new human review of this remediation is required before the source may be promoted to `verified`.
