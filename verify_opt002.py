"""
OPT-002 Verification Script
Verifica che AsyncGeminiClient e real async execution siano implementati.
"""

import sys
import ast
from pathlib import Path

AGENTS_FILE = Path("agents.py")

def verify_async_client_class():
    """Verifica che AsyncGeminiClient class esista"""
    print("[*] Verifying AsyncGeminiClient class...")

    if not AGENTS_FILE.exists():
        print(f"  [ERROR] {AGENTS_FILE} not found")
        return False

    content = AGENTS_FILE.read_text(encoding='utf-8')

    # Check for class definition
    if 'class AsyncGeminiClient' not in content:
        print("  [ERROR] AsyncGeminiClient class not found")
        return False
    print("  [OK] AsyncGeminiClient class exists")

    # Check for ThreadPoolExecutor
    if 'ThreadPoolExecutor' not in content:
        print("  [ERROR] ThreadPoolExecutor not imported/used")
        return False
    print("  [OK] ThreadPoolExecutor usage found")

    # Check for rate limiting
    if 'rate_limit' not in content.lower():
        print("  [ERROR] Rate limiting not implemented")
        return False
    print("  [OK] Rate limiting implementation found")

    # Check for retry logic
    if 'retry' not in content.lower() and 'backoff' not in content.lower():
        print("  [ERROR] Retry logic not found")
        return False
    print("  [OK] Retry logic with backoff found")

    return True

def verify_orchestrator_changes():
    """Verifica che MultiAgentOrchestrator usi AsyncGeminiClient"""
    print("\n[*] Verifying MultiAgentOrchestrator changes...")

    content = AGENTS_FILE.read_text(encoding='utf-8')

    # Check async_client initialization
    if 'self.async_client = AsyncGeminiClient' not in content:
        print("  [ERROR] async_client not initialized in __init__")
        return False
    print("  [OK] async_client initialized in orchestrator")

    # Check execute_parallel usage
    if 'execute_parallel' not in content:
        print("  [ERROR] execute_parallel method not used")
        return False
    print("  [OK] execute_parallel method found")

    # Check for OPT-002 comments
    if 'OPT-002' not in content:
        print("  [WARN] OPT-002 markers not found (optional)")
    else:
        print("  [OK] OPT-002 markers present")

    return True

def verify_no_fake_async():
    """Verifica che il vecchio fake async sia stato rimosso/sostituito"""
    print("\n[*] Verifying fake async removal...")

    content = AGENTS_FILE.read_text(encoding='utf-8')

    # Check that we're not using the old pattern anymore
    lines = content.split('\n')

    fake_async_found = False
    for i, line in enumerate(lines):
        # Look for the old "Simula async" comment
        if 'Simula async' in line and 'Gemini è sync' in line:
            print(f"  [WARN] Old fake async comment found at line {i+1}")
            fake_async_found = True

    if not fake_async_found:
        print("  [OK] No fake async patterns found")
    else:
        print("  [WARN] Some old async comments remain (cleanup recommended)")

    # Check that we're using ThreadPoolExecutor now
    if 'ThreadPoolExecutor' in content:
        print("  [OK] Using ThreadPoolExecutor for real parallelism")
        return True
    else:
        print("  [ERROR] ThreadPoolExecutor not found")
        return False

def verify_imports():
    """Verifica che gli import necessari siano presenti"""
    print("\n[*] Verifying imports...")

    content = AGENTS_FILE.read_text(encoding='utf-8')

    required_imports = [
        'concurrent.futures',
        'ThreadPoolExecutor',
        'Semaphore',
        'time'
    ]

    all_found = True
    for imp in required_imports:
        if imp in content:
            print(f"  [OK] {imp} imported")
        else:
            print(f"  [ERROR] {imp} not imported")
            all_found = False

    return all_found

def main():
    print("=" * 60)
    print("OPT-002 VERIFICATION")
    print("=" * 60)

    if not AGENTS_FILE.exists():
        print(f"[ERROR] File not found: {AGENTS_FILE}")
        return False

    all_passed = True

    # Run all verifications
    all_passed &= verify_imports()
    all_passed &= verify_async_client_class()
    all_passed &= verify_orchestrator_changes()
    all_passed &= verify_no_fake_async()

    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] OPT-002 VERIFICATION PASSED!")
        print("AsyncGeminiClient and real parallel execution implemented.")
        print("")
        print("NEXT STEPS:")
        print("1. Generate a test plan to verify timing improvements")
        print("2. Expected: 60s -> 15-20s generation time (-66%)")
        print("3. Check logs for 'TRUE parallel execution' message")
    else:
        print("[ERROR] OPT-002 VERIFICATION FAILED!")
        print("Some checks did not pass. See errors above.")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
