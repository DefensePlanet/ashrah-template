#!/usr/bin/env python3
"""
Test script for TTS hook lock mechanism.
Tests for race conditions, stale lock detection, and concurrent access.
"""

import os
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Path to the TTS hook script
TTS_HOOK = Path.home() / '.claude' / 'simple_tts_hook_fast.py'
LOCK_FILE = Path.home() / '.claude' / 'tts_hook.lock'
LOG_FILE = Path.home() / '.claude' / 'tts_client.log'


def cleanup():
    """Clean up test artifacts."""
    LOCK_FILE.unlink(missing_ok=True)
    if LOG_FILE.exists():
        LOG_FILE.unlink()


def read_log() -> str:
    """Read the log file."""
    if not LOG_FILE.exists():
        return ""
    with open(LOG_FILE, 'r') as f:
        return f.read()


def test_atomic_creation():
    """Test 1: Atomic lock creation prevents race condition."""
    print("TEST 1: Atomic lock creation (race condition prevention)")
    print("-" * 60)

    cleanup()

    # Launch multiple concurrent processes
    processes = []
    num_processes = 10

    # Create test input with sufficient length (script requires >20 chars)
    test_input = '{"transcript_path": "/tmp/test", "message": {"content": "This is a sufficiently long test message for concurrent execution testing that meets the minimum character requirement for the TTS hook script to process properly."}}'

    print(f"Launching {num_processes} concurrent processes...")
    for i in range(num_processes):
        proc = subprocess.Popen(
            [sys.executable, str(TTS_HOOK)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # Send input immediately
        proc.stdin.write(test_input.encode())
        proc.stdin.close()
        processes.append(proc)

    # Wait for all to complete
    for proc in processes:
        proc.wait(timeout=5)

    # Analyze log
    time.sleep(0.5)  # Let log writes complete
    log = read_log()

    lock_acquired = log.count("Lock acquired")
    lock_rejected = log.count("Another instance running") + log.count("Lock held by active process")

    print(f"✅ Lock acquired: {lock_acquired} time(s)")
    print(f"✅ Lock rejected: {lock_rejected} time(s)")
    print(f"✅ Total processes: {num_processes}")

    # Verify only one process got the lock
    # Note: lock_rejected may be higher than num_processes-1 due to retry logic
    if lock_acquired == 1 and lock_rejected >= num_processes - 1:
        print("✅ PASSED: Only one process acquired lock atomically")
        print(f"   (Extra rejections are from retry attempts)")
        return True
    else:
        print("❌ FAILED: Race condition detected!")
        print(f"   Expected 1 acquisition, got {lock_acquired}")
        return False


def test_stale_lock_detection():
    """Test 2: Stale lock detection and cleanup."""
    print("\nTEST 2: Stale lock detection")
    print("-" * 60)

    cleanup()

    # Create a stale lock with a dead PID
    fake_pid = 999999  # Very unlikely to exist
    LOCK_FILE.write_text(f"{fake_pid}\n")
    print(f"Created stale lock with fake PID {fake_pid}")

    # Try to acquire lock
    test_input = '{"transcript_path": "/tmp/test", "message": {"content": "This is a sufficiently long test message for stale lock detection testing."}}'
    proc = subprocess.Popen(
        [sys.executable, str(TTS_HOOK)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    proc.stdin.write(test_input.encode())
    proc.stdin.close()
    proc.wait(timeout=5)

    # Check log
    time.sleep(0.5)
    log = read_log()

    if "Stale lock from dead process" in log and "Lock acquired" in log:
        print("✅ PASSED: Stale lock detected and cleaned up")
        return True
    else:
        print("❌ FAILED: Stale lock not handled correctly")
        print(f"Log output:\n{log}")
        return False


def test_legitimate_lock_protection():
    """Test 3: Legitimate lock holder is protected."""
    print("\nTEST 3: Legitimate lock protection")
    print("-" * 60)

    cleanup()

    # Start a long-running process that holds the lock
    test_input = '{"transcript_path": "/tmp/test", "message": {"content": "This is a sufficiently long test message that will hold the lock for testing."}}'
    proc1 = subprocess.Popen(
        [sys.executable, str(TTS_HOOK)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    proc1.stdin.write(test_input.encode())
    proc1.stdin.close()

    # Give it time to acquire lock
    time.sleep(0.5)

    # Verify lock file has real PID
    if not LOCK_FILE.exists():
        print("❌ FAILED: Lock file not created")
        proc1.terminate()
        return False

    lock_pid = int(LOCK_FILE.read_text().strip())
    print(f"First process PID: {proc1.pid}, Lock PID: {lock_pid}")

    # Try to acquire lock with second process
    proc2 = subprocess.Popen(
        [sys.executable, str(TTS_HOOK)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    proc2.stdin.write(test_input.encode())
    proc2.stdin.close()
    proc2.wait(timeout=5)

    # Wait for first process
    proc1.wait(timeout=5)

    # Check log
    time.sleep(0.5)
    log = read_log()

    # Should see exactly 2 lock acquisition attempts: 1 success, 1 rejection
    lock_acquired = log.count("Lock acquired")
    lock_rejected = log.count("another instance running") or log.count("Lock held by active process")

    if lock_acquired == 1 and lock_rejected >= 1:
        print("✅ PASSED: Legitimate lock holder protected")
        return True
    else:
        print("❌ FAILED: Lock protection not working correctly")
        print(f"Log output:\n{log}")
        return False


def test_empty_lock_cleanup():
    """Test 4: Empty lock file is cleaned up."""
    print("\nTEST 4: Empty lock file cleanup")
    print("-" * 60)

    cleanup()

    # Create empty lock file
    LOCK_FILE.touch()
    print("Created empty lock file")

    # Try to acquire lock
    test_input = '{"transcript_path": "/tmp/test", "message": {"content": "This is a sufficiently long test message for empty lock cleanup testing."}}'
    proc = subprocess.Popen(
        [sys.executable, str(TTS_HOOK)],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    proc.stdin.write(test_input.encode())
    proc.stdin.close()
    proc.wait(timeout=5)

    # Check log
    time.sleep(0.5)
    log = read_log()

    if "Empty lock file, removing" in log and "Lock acquired" in log:
        print("✅ PASSED: Empty lock file cleaned up")
        return True
    else:
        print("❌ FAILED: Empty lock file not handled correctly")
        print(f"Log output:\n{log}")
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("TTS Hook Lock Mechanism Test Suite")
    print("=" * 60)

    if not TTS_HOOK.exists():
        print(f"❌ ERROR: TTS hook not found at {TTS_HOOK}")
        sys.exit(1)

    results: List[Tuple[str, bool]] = []

    # Run tests
    results.append(("Atomic Creation", test_atomic_creation()))
    results.append(("Stale Lock Detection", test_stale_lock_detection()))
    results.append(("Legitimate Lock Protection", test_legitimate_lock_protection()))
    results.append(("Empty Lock Cleanup", test_empty_lock_cleanup()))

    # Cleanup
    cleanup()

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
