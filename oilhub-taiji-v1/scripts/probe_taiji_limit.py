#!/usr/bin/env python3
"""
Binary search probe to discover taiji API's actual max text length limit.

Usage:
    python3 scripts/probe_taiji_limit.py

This script sends increasingly long texts to taiji API and uses binary search
to find the exact character count at which taiji rejects the request.
"""

import httpx
import json
import os
import sys

TAIJI_BASE_URL = os.getenv("TAIJI_BASE_URL", "https://ai.aurod.cn")
TAIJI_API_KEY = os.getenv(
    "TAIJI_API_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjE4MTEwLCJzaWduIjoiODUyMmY5NjhhY2RhMmViZWY3YzlkMTc5NTdhZDA5ZjYiLCJyb2xlIjoidXNlciIsImV4cCI6MTc3ODU1MDI4MiwibmJmIjoxNzc3MjU0MjgyLCJpYXQiOjE3NzcyNTQyODJ9.IHY5bsaxvFkZrS2g77VuQjEmQ_x3sY044E7ASpVCaDQ"
)
TAIJI_SESSION_ID = int(os.getenv("TAIJI_SESSION_ID", "658084"))
TAIJI_SESSION_COOKIE = os.getenv("TAIJI_SESSION_COOKIE", "e8573afc12a94d36c85627cd71788200")


def test_text_length(length: int) -> tuple[bool, str]:
    """Send a text of given length to taiji API. Returns (success, error_msg)."""
    text = "A" * length

    payload = {
        "text": text,
        "sessionId": TAIJI_SESSION_ID,
        "files": [],
    }

    headers = {
        "accept": "text/event-stream",
        "content-type": "application/json",
        "authorization": TAIJI_API_KEY,
        "x-app-version": "2.16.0",
    }

    cookies = {"server_name_session": TAIJI_SESSION_COOKIE}

    url = f"{TAIJI_BASE_URL}/api/chat/completions"

    try:
        with httpx.Client(timeout=60.0, cookies=cookies) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code != 200:
            return False, f"HTTP {response.status_code}: {response.text[:200]}"

        # Check for business errors in SSE body
        body = response.text
        for line in body.split("\n"):
            line = line.strip()
            if line.startswith("data:"):
                data = line[5:].strip()
                if data == "[DONE]":
                    break
                try:
                    obj = json.loads(data)
                    if obj.get("type") != "string":
                        if obj.get("err") or obj.get("msg") or obj.get("code", 0) != 0:
                            err_msg = obj.get("msg") or obj.get("err") or json.dumps(obj)
                            return False, f"Business error: {err_msg}"
                except json.JSONDecodeError:
                    pass

        return True, ""

    except httpx.TimeoutException:
        return False, "Timeout"
    except Exception as e:
        return False, f"Exception: {e}"


def binary_search_limit(low: int, high: int) -> int:
    """Binary search to find the maximum accepted text length."""
    print(f"Searching between {low} and {high}...")

    while low < high:
        mid = (low + high + 1) // 2
        success, err = test_text_length(mid)

        status = "OK" if success else f"FAIL ({err[:60]})"
        print(f"  Length {mid:>7}: {status}")

        if success:
            low = mid
        else:
            high = mid - 1

    return low


def main():
    print("=" * 60)
    print("Taiji API Max Text Length Probe")
    print("=" * 60)
    print()

    # First, do a coarse scan to find the rough boundary
    print("Phase 1: Coarse scan (step=10000)...")
    step = 10000
    last_ok = 0
    for length in range(step, 200000, step):
        success, err = test_text_length(length)
        status = "OK" if success else f"FAIL ({err[:50]})"
        print(f"  Length {length:>7}: {status}")
        if success:
            last_ok = length
        else:
            break

    if last_ok == 0:
        print("ERROR: Even small texts are failing. Check API credentials.")
        sys.exit(1)

    # Binary search between last_ok and last_ok + step
    low = last_ok
    high = min(last_ok + step, 200000)

    print()
    print(f"Phase 2: Binary search between {low} and {high}...")
    exact_limit = binary_search_limit(low, high)

    print()
    print("=" * 60)
    print(f"RESULT: Taiji API max text length = {exact_limit} characters")
    print("=" * 60)

    # Verify the boundary
    print()
    print("Verification:")
    ok_at_limit, err1 = test_text_length(exact_limit)
    fail_above, err2 = test_text_length(exact_limit + 1)
    print(f"  Length {exact_limit}: {'OK' if ok_at_limit else 'FAIL'}")
    print(f"  Length {exact_limit + 1}: {'OK' if fail_above else 'FAIL'}")


if __name__ == "__main__":
    main()
