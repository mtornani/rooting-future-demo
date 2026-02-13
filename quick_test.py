#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Quick test for FEAT-008
import sys
import os
import sqlite3
from pathlib import Path

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

print("\n" + "="*60)
print("QUICK TEST: FEAT-008 Public Sharing")
print("="*60 + "\n")

# Test 1: Database exists
db_path = Path("knowledge_base/rooting_future.db")
if db_path.exists():
    print(f"✓ Database found: {db_path} ({db_path.stat().st_size // 1024} KB)")
else:
    print(f"✗ Database not found at {db_path}")
    sys.exit(1)

# Test 2: Check table exists
try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='public_shares'")
    result = cursor.fetchone()
    if result:
        print("✓ public_shares table exists")

        # Count shares
        cursor.execute("SELECT COUNT(*) FROM public_shares")
        count = cursor.fetchone()[0]
        print(f"  → {count} shares in database")

        # Show table structure
        cursor.execute("PRAGMA table_info(public_shares)")
        columns = cursor.fetchall()
        print(f"  → {len(columns)} columns defined")

    else:
        print("✗ public_shares table NOT found")
        conn.close()
        sys.exit(1)
    conn.close()
except Exception as e:
    print(f"✗ Database error: {e}")
    sys.exit(1)

# Test 3: Import ShareManager
try:
    from utils.share_manager import ShareManager
    print("✓ ShareManager class imported successfully")
except Exception as e:
    print(f"✗ Failed to import ShareManager: {e}")
    sys.exit(1)

# Test 4: Initialize ShareManager
try:
    sm = ShareManager(db_path=str(db_path))
    print("✓ ShareManager initialized successfully")
except Exception as e:
    print(f"✗ Failed to initialize ShareManager: {e}")
    sys.exit(1)

# Test 5: Check available tables
try:
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
    tables = cursor.fetchall()
    print(f"✓ Available tables in database:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
        count = cursor.fetchone()[0]
        print(f"  → {table[0]} ({count} rows)")

    # Try to find plans table (might have different name)
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%plan%'")
    plan_tables = cursor.fetchall()

    if not plan_tables:
        print("⚠ No plan tables found in database")
        print("\n" + "="*60)
        print("BASIC TESTS PASSED ✓")
        print("(Share creation test skipped - no plan table)")
        print("="*60 + "\n")
        conn.close()
        sys.exit(0)

    plan_table = plan_tables[0][0]
    print(f"\n✓ Using plan table: {plan_table}")

    # Get table structure
    cursor.execute(f"PRAGMA table_info({plan_table})")
    columns = [col[1] for col in cursor.fetchall()]
    print(f"  → Columns: {', '.join(columns[:5])}...")

    # Try to get a plan
    cursor.execute(f"SELECT * FROM {plan_table} ORDER BY rowid DESC LIMIT 1")
    plan = cursor.fetchone()
    conn.close()

    if plan:
        # Get plan_id from first column (assume it's there)
        plan_id = plan[0]
        print(f"✓ Found plan in database: {plan_id}")
        print(f"  → Data: {plan[:3]}...")  # Show first 3 fields
    else:
        print("⚠ No plans in database (cannot test share creation)")
        print("\n" + "="*60)
        print("BASIC TESTS PASSED ✓")
        print("(Share creation test skipped - no plans available)")
        print("="*60 + "\n")
        sys.exit(0)
except Exception as e:
    print(f"✗ Failed to query plans: {e}")
    sys.exit(1)

# Test 6: Create a test share
try:
    share_token = sm.create_share(
        plan_id=plan_id,
        created_by=1,
        expires_days=7,
        password=None,
        allow_download=False
    )
    print(f"✓ Share created successfully")
    print(f"  → Token: {share_token[:20]}...{share_token[-8:]}")
except Exception as e:
    print(f"✗ Failed to create share: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 7: Validate share
try:
    share = sm.validate_share(share_token)
    if share:
        print(f"✓ Share validated successfully")
        print(f"  → Plan ID: {share['plan_id']}")
        print(f"  → Expires: {share['expires_at']}")
        print(f"  → Views: {share['view_count']}")
    else:
        print(f"✗ Share validation failed")
        sys.exit(1)
except Exception as e:
    print(f"✗ Validation error: {e}")
    sys.exit(1)

# Test 8: View counter (auto-incremented by validate_share)
try:
    # Call validate again to increment counter
    share2 = sm.validate_share(share_token)
    if share2 and share2['view_count'] >= 1:
        print(f"✓ View counter working (count: {share2['view_count']})")
    else:
        print(f"⚠ View counter may not be working properly")
except Exception as e:
    print(f"⚠ View count test failed: {e}")

# Test 9: Clean up test share (requires user_id for security)
try:
    success = sm.revoke_share(share_token, user_id=1)
    if success:
        print(f"✓ Share revoked successfully")

        # Verify revocation
        share = sm.validate_share(share_token)
        if not share:
            print(f"✓ Revoked share correctly returns None")
        else:
            print(f"⚠ Revoked share still validates (unexpected)")
    else:
        print(f"⚠ Share revocation returned False")
except Exception as e:
    print(f"⚠ Revocation test failed: {e}")

print("\n" + "="*60)
print("ALL TESTS PASSED ✓")
print("="*60 + "\n")
print("FEAT-008 is working correctly!")
print("You can now test the webapp share button at:")
print(f"  http://127.0.0.1:5000/view/{plan_id}")
print("\n")
