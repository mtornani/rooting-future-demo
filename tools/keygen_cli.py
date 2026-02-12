#!/usr/bin/env python3
"""
Rooting Future - License Key Generator (CLI Version)
Quick command-line tool for generating license keys with optional expiration.

Usage:
    python keygen_cli.py <email> <hwid> [--days N]

Examples:
    python keygen_cli.py cliente@example.com 9B3A-1C2D-4E5F-6789
    python keygen_cli.py cliente@example.com 9B3A-1C2D-4E5F-6789 --days 365
    python keygen_cli.py cliente@example.com 9B3A-1C2D-4E5F-6789 --days 0    # perpetua
"""

import hashlib
import os
import sys
from datetime import datetime, timedelta


def generate_license_key(owner_email: str, machine_identifier: str) -> str:
    """Generate a valid license key for a given user and machine."""
    clean_hwid = machine_identifier.replace("-", "").replace(" ", "").strip().upper()
    secret_salt = os.environ.get("LICENSE_SALT", "coca-cola-secret-recipe-2026")
    raw_string = f"{clean_hwid}:{owner_email}:{secret_salt}"
    return hashlib.sha256(raw_string.encode()).hexdigest().upper()[:24]


def main():
    args = sys.argv[1:]

    if len(args) < 2:
        print("Usage: python keygen_cli.py <email> <hwid> [--days N]")
        print("")
        print("Options:")
        print("  --days N    License duration in days (default: 365, 0 = perpetual)")
        print("")
        print("Examples:")
        print("  python keygen_cli.py cliente@example.com 9B3A-1C2D-4E5F-6789")
        print("  python keygen_cli.py cliente@example.com 9B3A-1C2D-4E5F-6789 --days 90")
        print("  python keygen_cli.py cliente@example.com 9B3A-1C2D-4E5F-6789 --days 0")
        sys.exit(1)

    email = args[0]
    hwid = args[1]

    # Parse --days option
    duration_days = 365
    if "--days" in args:
        days_idx = args.index("--days")
        if days_idx + 1 < len(args):
            try:
                duration_days = int(args[days_idx + 1])
            except ValueError:
                print("ERROR: --days richiede un numero intero")
                sys.exit(1)

    # Validate
    if "@" not in email:
        print("ERROR: Invalid email format")
        sys.exit(1)

    # Generate
    key = generate_license_key(email, hwid)
    formatted = "-".join([key[i:i+6] for i in range(0, len(key), 6)])

    # Calculate expiration
    if duration_days > 0:
        expires_at = datetime.now() + timedelta(days=duration_days)
        expiry_str = expires_at.strftime("%Y-%m-%d")
        duration_label = f"{duration_days} giorni (scade il {expiry_str})"
    else:
        expiry_str = "Mai"
        duration_label = "Perpetua (nessuna scadenza)"

    print(f"\n{'='*55}")
    print(f"  ROOTING FUTURE - LICENSE KEY GENERATOR")
    print(f"{'='*55}")
    print(f"  Email:    {email}")
    print(f"  HWID:     {hwid}")
    print(f"  Durata:   {duration_label}")
    print(f"{'='*55}")
    print(f"  LICENSE KEY: {formatted}")
    print(f"  (raw: {key})")
    print(f"  Duration days: {duration_days}")
    print(f"{'='*55}\n")

    # Log
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open("license_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{timestamp} | {email} | {hwid} | {key} | {duration_days}d | expires:{expiry_str}\n")
    print(f"[Logged to license_log.txt]")


if __name__ == "__main__":
    main()
