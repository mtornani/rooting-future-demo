"""
OPT-001 Verification Script
Verifica che gli indici e WAL mode siano attivi e funzionanti.
"""

import sqlite3
import time
from pathlib import Path

DB_PATH = Path("knowledge_base/rooting_future.db")

def verify_indices():
    """Verifica che gli indici siano presenti"""
    print("[*] Verifying indices...")

    with sqlite3.connect(DB_PATH) as conn:
        # Check documents indices
        docs_indices = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='documents'").fetchall()
        docs_indices = [idx[0] for idx in docs_indices]

        required_docs = ['idx_docs_category_section', 'idx_docs_type', 'idx_docs_club']
        for idx in required_docs:
            if idx in docs_indices:
                print(f"  [OK] {idx}")
            else:
                print(f"  [ERROR] {idx} - MISSING!")
                return False

        # Check plans indices
        plans_indices = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='plans'").fetchall()
        plans_indices = [idx[0] for idx in plans_indices]

        required_plans = ['idx_plans_created', 'idx_plans_club', 'idx_plans_status', 'idx_plans_owner']
        for idx in required_plans:
            if idx in plans_indices:
                print(f"  [OK] {idx}")
            else:
                print(f"  [ERROR] {idx} - MISSING!")
                return False

    return True

def verify_wal_mode():
    """Verifica WAL mode e PRAGMA settings"""
    print("\n[*] Verifying WAL mode...")

    with sqlite3.connect(DB_PATH) as conn:
        journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
        synchronous = conn.execute("PRAGMA synchronous").fetchone()[0]

        print(f"  Journal Mode: {journal_mode}")
        print(f"  Synchronous: {synchronous} (2=NORMAL)")

        if journal_mode.lower() == 'wal':
            print("  [OK] WAL mode enabled")
        else:
            print(f"  [ERROR] WAL mode NOT enabled (current: {journal_mode})")
            return False

        if synchronous == 2:
            print("  [OK] PRAGMA synchronous=NORMAL")
        else:
            print(f"  [WARN]  PRAGMA synchronous={synchronous} (expected 2)")

    return True

def benchmark_query():
    """Benchmark semplice per verificare miglioramenti"""
    print("\n[*] Running simple benchmark...")

    with sqlite3.connect(DB_PATH) as conn:
        # Count plans
        count = conn.execute("SELECT COUNT(*) FROM plans").fetchone()[0]
        print(f"  Total plans in DB: {count}")

        if count == 0:
            print("  [WARN]  No plans in database, skipping benchmark")
            return True

        # Query with index (should be fast)
        start = time.time()
        result = conn.execute("SELECT * FROM plans WHERE status='approved' ORDER BY created_at DESC LIMIT 10").fetchall()
        elapsed = time.time() - start

        print(f"  Query with index took: {elapsed*1000:.2f}ms")
        print(f"  Results: {len(result)} plans")

        if elapsed < 0.1:
            print("  [OK] Query performance is good!")
        else:
            print(f"  [WARN]  Query took longer than expected")

    return True

def verify_schema():
    """Verifica che section_type column esista"""
    print("\n[*] Verifying schema...")

    with sqlite3.connect(DB_PATH) as conn:
        # Check documents table
        docs_schema = conn.execute("PRAGMA table_info(documents)").fetchall()
        docs_columns = [col[1] for col in docs_schema]

        if 'section_type' in docs_columns:
            print("  [OK] documents.section_type column exists")
        else:
            print("  [ERROR] documents.section_type column MISSING!")
            return False

    return True

def main():
    print("=" * 60)
    print("OPT-001 VERIFICATION")
    print("=" * 60)

    if not DB_PATH.exists():
        print(f"[ERROR] Database not found: {DB_PATH}")
        return False

    all_passed = True

    # Run all verifications
    all_passed &= verify_schema()
    all_passed &= verify_indices()
    all_passed &= verify_wal_mode()
    all_passed &= benchmark_query()

    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] OPT-001 VERIFICATION PASSED!")
        print("SQLite indexing and WAL mode successfully implemented.")
    else:
        print("[ERROR] OPT-001 VERIFICATION FAILED!")
        print("Some checks did not pass. See errors above.")
    print("=" * 60)

    return all_passed

if __name__ == "__main__":
    import sys
    success = main()
    sys.exit(0 if success else 1)
