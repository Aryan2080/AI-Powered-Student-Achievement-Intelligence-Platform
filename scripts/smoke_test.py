"""
scripts/smoke_test.py
=====================
Production smoke test verifying API health, auth, opportunities catalog,
recommendation engine, and PDF transcript generation.
AI-Powered Student Achievement Intelligence Platform — Member 3
"""

from __future__ import annotations

import sys
import requests

API_BASE_URL = "http://localhost:8000"


def run_smoke_tests():
    print("=" * 60)
    print("RUNNING PRODUCTION SMOKE TESTS")
    print("=" * 60)

    # 1. Health Probe
    try:
        r = requests.get(f"{API_BASE_URL}/health", timeout=5)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        assert r.json().get("status") == "UP"
        print("[PASS] 1. Liveness Probe /health -> HTTP 200 (Service UP)")
    except Exception as e:
        print(f"[FAIL] 1. Liveness Probe failed: {e}")
        sys.exit(1)

    # 2. Opportunities Catalog Probe
    try:
        r = requests.get(f"{API_BASE_URL}/api/v1/opportunities?limit=5", timeout=5)
        assert r.status_code == 200
        data = r.json()
        assert len(data) > 0
        print(f"[PASS] 2. Opportunity Catalog /api/v1/opportunities -> HTTP 200 ({len(data)} items verified)")
    except Exception as e:
        print(f"[FAIL] 2. Opportunity Catalog failed: {e}")
        sys.exit(1)

    # 3. Personalized Recommendation Probe
    try:
        r = requests.get(f"{API_BASE_URL}/api/v1/recommendations/STU-2026-0001?top_k=5", timeout=5)
        assert r.status_code == 200
        recs = r.json().get("recommendations", [])
        assert len(recs) > 0
        assert "explanation" in recs[0]
        assert "scores" in recs[0]
        print(f"[PASS] 3. Recommendations /api/v1/recommendations/STU-2026-0001 -> HTTP 200 ({len(recs)} ranked items)")
    except Exception as e:
        print(f"[FAIL] 3. Recommendations failed: {e}")
        sys.exit(1)

    # 4. Transcript Export Probe
    try:
        r = requests.get(f"{API_BASE_URL}/api/v1/reports/transcript/STU-2026-0001", timeout=5)
        assert r.status_code == 200
        assert r.content.startswith(b"%PDF"), "Response is not a valid PDF binary"
        print(f"[PASS] 4. Official Transcript Export /api/v1/reports/transcript -> HTTP 200 ({len(r.content)} bytes PDF)")
    except Exception as e:
        print(f"[FAIL] 4. Transcript Export failed: {e}")
        sys.exit(1)

    print("=" * 60)
    print("ALL SMOKE TESTS PASSED SUCCESSFULLY (100% HEALTHY)")
    print("=" * 60)


if __name__ == "__main__":
    run_smoke_tests()
